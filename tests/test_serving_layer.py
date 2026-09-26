import json
from pathlib import Path

import duckdb
import pandas as pd

from mobility_control_tower.serving.duckdb_loader import build_serving_database, query_serving_database
from mobility_control_tower.serving.serving_report import generate_serving_report


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def make_gold_run(tmp_path: Path) -> Path:
    gold = tmp_path / "gold" / "tisseo" / "static-1"
    (gold / "dbt_run_manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (gold / "dbt_run_manifest.json").write_text(json.dumps({"status": "success", "tool": "dbt Core"}), encoding="utf-8")
    write_csv(
        gold / "route_daily_trips.csv",
        [
            {
                "service_date": "2026-01-01",
                "route_id": "R1",
                "route_short_name": "A",
                "route_long_name": "Airport",
                "route_type": "3",
                "scheduled_trips_count": 10,
            }
        ],
    )
    write_csv(
        gold / "network_daily_summary.csv",
        [{"service_date": "2026-01-01", "active_routes_count": 1, "scheduled_trips_count": 10, "scheduled_stop_departures_count": 25, "active_stops_count": 2}],
    )
    write_csv(
        gold / "route_period_summary.csv",
        [
            {
                "route_id": "R1",
                "route_short_name": "A",
                "route_long_name": "Airport",
                "route_type": "3",
                "active_service_days": 1,
                "total_scheduled_trips": 10,
                "average_trips_per_active_day": 10,
                "max_daily_trips": 10,
                "first_service_date": "2026-01-01",
                "last_service_date": "2026-01-01",
            }
        ],
    )
    write_csv(
        gold / "route_hourly_headway.csv",
        [
            {
                "service_date": "2026-01-01",
                "route_id": "R1",
                "route_short_name": "A",
                "route_long_name": "Airport",
                "departure_hour": 8,
                "scheduled_departures_count": 4,
                "planned_headway_minutes": 15,
            }
        ],
    )
    write_csv(
        gold / "route_type_daily_summary.csv",
        [
            {
                "service_date": "2026-01-01",
                "route_type": "3",
                "route_type_label": "Bus",
                "active_routes_count": 1,
                "scheduled_trips_count": 10,
                "scheduled_stop_departures_count": 25,
            }
        ],
    )
    return gold


def make_rt_gold_run(tmp_path: Path, include_optional_delay: bool = True) -> Path:
    rt = tmp_path / "realtime_gold" / "tisseo" / "trip_updates" / "rt-1"
    write_csv(
        rt / "rt_feed_health_snapshot.csv",
        [{"feed_type": "trip_updates", "fetched_at": "2026-01-01T00:00:00+00:00", "feed_age_seconds": 30, "freshness_status": "PASS", "entity_count": 5}],
    )
    write_csv(
        rt / "rt_identifier_compatibility_snapshot.csv",
        [
            {
                "identifier_type": "route_id",
                "rt_distinct_count": 1,
                "matched_static_count": 1,
                "unmatched_static_count": 0,
                "match_percentage": 100,
                "status": "PASS",
                "sample_unmatched_values": "",
            }
        ],
    )
    if include_optional_delay:
        write_csv(
            rt / "rt_route_delay_snapshot.csv",
            [
                {
                    "route_id": "R1",
                    "route_short_name": "A",
                    "route_long_name": "Airport",
                    "stop_time_updates_count": 5,
                    "distinct_trip_updates_count": 2,
                    "avg_delay_seconds": 120,
                    "median_delay_seconds": 100,
                    "max_delay_seconds": 300,
                    "delayed_updates_5min_count": 1,
                    "delayed_updates_5min_pct": 20,
                }
            ],
        )
        write_csv(
            rt / "rt_stop_delay_snapshot.csv",
            [{"stop_id": "S1", "stop_name": "Capitole", "stop_time_updates_count": 3, "avg_delay_seconds": 90}],
        )
    return rt


def table_names(db_path: Path) -> set[str]:
    with duckdb.connect(str(db_path), read_only=True) as connection:
        return {row[0] for row in connection.execute("SHOW TABLES").fetchall()}


def test_build_serving_database_static_only_creates_tables_views_manifest_and_report(tmp_path: Path) -> None:
    gold = make_gold_run(tmp_path)
    serving_run = build_serving_database(gold, serving_root=tmp_path / "serving")
    db_path = serving_run / "mobility_control_tower.duckdb"
    manifest = json.loads((serving_run / "serving_manifest.json").read_text(encoding="utf-8"))
    names = table_names(db_path)
    result = query_serving_database(db_path, "top-routes", limit=5)
    report_path = generate_serving_report(serving_run, tmp_path / "reports")

    assert db_path.is_file()
    assert "route_daily_trips" in names
    assert "network_daily_summary" in names
    assert "v_network_overview" in names
    assert "v_top_routes_static" in names
    assert manifest["realtime_gold_run_path"] is None
    assert result.iloc[0]["route_id"] == "R1"
    assert report_path.is_file()


def test_build_serving_database_with_realtime_tables_and_optional_missing_files(tmp_path: Path) -> None:
    gold = make_gold_run(tmp_path)
    rt = make_rt_gold_run(tmp_path, include_optional_delay=False)
    serving_run = build_serving_database(gold, rt, serving_root=tmp_path / "serving")
    db_path = serving_run / "mobility_control_tower.duckdb"
    manifest = json.loads((serving_run / "serving_manifest.json").read_text(encoding="utf-8"))
    names = table_names(db_path)
    health = query_serving_database(db_path, "rt-feed-health", limit=5)
    compatibility = query_serving_database(db_path, "rt-compatibility", limit=5)

    assert "rt_feed_health_snapshot" in names
    assert "rt_identifier_compatibility_snapshot" in names
    assert "v_rt_feed_health" in names
    assert "v_rt_identifier_compatibility" in names
    assert "v_rt_top_delayed_routes_snapshot" not in names
    assert manifest["realtime_run_id"] == "rt-1"
    assert health.iloc[0]["freshness_status"] == "PASS"
    assert compatibility.iloc[0]["status"] == "PASS"


def test_build_serving_database_with_full_realtime_views(tmp_path: Path) -> None:
    gold = make_gold_run(tmp_path)
    rt = make_rt_gold_run(tmp_path)
    serving_run = build_serving_database(gold, rt, serving_root=tmp_path / "serving")
    db_path = serving_run / "mobility_control_tower.duckdb"
    names = table_names(db_path)
    delayed_routes = query_serving_database(db_path, "rt-top-delayed-routes", limit=5)

    assert "v_rt_top_delayed_routes_snapshot" in names
    assert "v_rt_top_delayed_stops_snapshot" in names
    assert delayed_routes.iloc[0]["route_id"] == "R1"
