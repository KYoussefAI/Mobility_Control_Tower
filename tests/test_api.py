from pathlib import Path

import duckdb
import pytest
from fastapi import HTTPException

from mobility_control_tower.api.app import create_app
from mobility_control_tower.api.report import generate_api_report
from mobility_control_tower.api.routes import (
    health,
    metadata,
    realtime_compatibility,
    realtime_feed_health,
    realtime_top_delayed_routes,
    realtime_top_delayed_stops,
    static_hourly_headway,
    static_top_routes,
)


def make_db(path: Path, include_realtime: bool = True) -> Path:
    with duckdb.connect(str(path)) as connection:
        connection.execute(
            """
            CREATE TABLE network_daily_summary AS
            SELECT '2026-01-01' AS service_date, 2 AS active_routes_count, 20 AS scheduled_trips_count,
                   100 AS scheduled_stop_departures_count, 10 AS active_stops_count
            """
        )
        connection.execute("CREATE VIEW v_network_overview AS SELECT * FROM network_daily_summary")
        connection.execute(
            """
            CREATE TABLE route_period_summary AS
            SELECT 'R1' AS route_id, 'A' AS route_short_name, 'Airport' AS route_long_name, '3' AS route_type,
                   2 AS active_service_days, 20 AS total_scheduled_trips, 10.0 AS average_trips_per_active_day,
                   12 AS max_daily_trips
            UNION ALL
            SELECT 'R2', 'B', 'Basso', '3', 1, 5, 5.0, 5
            """
        )
        connection.execute("CREATE VIEW v_top_routes_static AS SELECT * FROM route_period_summary ORDER BY total_scheduled_trips DESC")
        connection.execute(
            """
            CREATE TABLE route_hourly_headway AS
            SELECT '2026-01-01' AS service_date, 'R1' AS route_id, 'A' AS route_short_name,
                   'Airport' AS route_long_name, 8 AS departure_hour, 4 AS scheduled_departures_count,
                   15.0 AS planned_headway_minutes
            UNION ALL
            SELECT '2026-01-02', 'R2', 'B', 'Basso', 9, 2, 30.0
            """
        )
        connection.execute("CREATE VIEW v_route_hourly_headway AS SELECT * FROM route_hourly_headway")
        connection.execute(
            """
            CREATE TABLE route_type_daily_summary AS
            SELECT '2026-01-01' AS service_date, '3' AS route_type, 'Bus' AS route_type_label,
                   2 AS active_routes_count, 20 AS scheduled_trips_count, 100 AS scheduled_stop_departures_count
            """
        )
        connection.execute("CREATE VIEW v_route_type_daily_summary AS SELECT * FROM route_type_daily_summary")
        if include_realtime:
            connection.execute(
                """
                CREATE TABLE rt_feed_health_snapshot AS
                SELECT 'trip_updates' AS feed_type, 6 AS feed_age_seconds, 'PASS' AS freshness_status,
                       1191 AS entity_count
                """
            )
            connection.execute("CREATE VIEW v_rt_feed_health AS SELECT * FROM rt_feed_health_snapshot")
            connection.execute(
                """
                CREATE TABLE rt_identifier_compatibility_snapshot AS
                SELECT 'route_id' AS identifier_type, 100.0 AS match_percentage, 'PASS' AS status
                UNION ALL
                SELECT 'trip_id', 88.08, 'WARN'
                """
            )
            connection.execute("CREATE VIEW v_rt_identifier_compatibility AS SELECT * FROM rt_identifier_compatibility_snapshot")
            connection.execute(
                """
                CREATE TABLE rt_route_delay_snapshot AS
                SELECT 'R1' AS route_id, 'A' AS route_short_name, 'Airport' AS route_long_name,
                       10 AS stop_time_updates_count, 2 AS distinct_trip_updates_count,
                       120.0 AS avg_delay_seconds, 100.0 AS median_delay_seconds, 300 AS max_delay_seconds,
                       1 AS delayed_updates_5min_count, 10.0 AS delayed_updates_5min_pct
                """
            )
            connection.execute("CREATE VIEW v_rt_top_delayed_routes_snapshot AS SELECT * FROM rt_route_delay_snapshot")
            connection.execute(
                """
                CREATE TABLE rt_stop_delay_snapshot AS
                SELECT 'S1' AS stop_id, 'Capitole' AS stop_name, 5 AS stop_time_updates_count,
                       90.0 AS avg_delay_seconds
                """
            )
            connection.execute("CREATE VIEW v_rt_top_delayed_stops_snapshot AS SELECT * FROM rt_stop_delay_snapshot")
    return path


class FakeRequest:
    def __init__(self, app):
        self.app = app


def test_app_factory_rejects_invalid_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_app(tmp_path / "missing.duckdb")


def test_health_metadata_static_endpoints_and_filters(tmp_path: Path) -> None:
    db = make_db(tmp_path / "api.duckdb")
    app = create_app(db)
    request = FakeRequest(app)

    health_response = health(request)
    metadata_response = metadata(request)
    top_routes = static_top_routes(request, limit=1)
    headway = static_hourly_headway(request, route_id="R1", service_date="2026-01-01", limit=10)

    assert health_response["status"] == "ok"
    assert health_response["database_connected"] is True
    assert "network_daily_summary" in metadata_response["available_tables"]
    assert "v_top_routes_static" in metadata_response["available_views"]
    assert metadata_response["static_data_available"] is True
    assert metadata_response["realtime_snapshot_available"] is True
    assert not any(getattr(route, "path", None) == "/sql" for route in app.routes)
    assert top_routes["count"] == 1
    assert top_routes["data"][0]["route_id"] == "R1"
    assert headway["count"] == 1
    assert headway["data"][0]["route_id"] == "R1"


def test_realtime_endpoints_work_when_views_exist_and_report_is_generated(tmp_path: Path) -> None:
    db = make_db(tmp_path / "api.duckdb")
    request = FakeRequest(create_app(db))
    report_path = generate_api_report(db, tmp_path / "reports")

    health_response = realtime_feed_health(request)
    compatibility = realtime_compatibility(request)
    delayed_routes = realtime_top_delayed_routes(request, limit=1)
    delayed_stops = realtime_top_delayed_stops(request, limit=1)

    assert health_response["data"][0]["freshness_status"] == "PASS"
    assert compatibility["count"] == 2
    assert delayed_routes["data"][0]["route_id"] == "R1"
    assert delayed_stops["data"][0]["stop_id"] == "S1"
    assert report_path.is_file()
    assert "local read-only API" in report_path.read_text(encoding="utf-8")


def test_realtime_endpoints_return_404_without_realtime_views(tmp_path: Path) -> None:
    db = make_db(tmp_path / "api_static_only.duckdb", include_realtime=False)
    request = FakeRequest(create_app(db))

    metadata_response = metadata(request)

    assert metadata_response["realtime_snapshot_available"] is False
    with pytest.raises(HTTPException) as excinfo:
        realtime_feed_health(request)
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Realtime snapshot data is not available in this serving database."
