import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.api.app import create_app
from mobility_control_tower.api.routes import history_delay_trend, history_feed_health, history_routes, history_stops, history_summary
from mobility_control_tower.dashboard.api_client import ENDPOINTS
from mobility_control_tower.metrics.historical_kpis import build_historical_kpis, compute_historical_kpis
from mobility_control_tower.realtime import historical_storage
from mobility_control_tower.realtime.historical_storage import collect_gtfs_rt_snapshot, run_historical_collection
from mobility_control_tower.serving.duckdb_loader import build_serving_database, query_serving_database


SOURCE = {"name": "Tisseo"}


class FakeRequest:
    def __init__(self, app):
        self.app = app


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def make_gold_run(tmp_path: Path) -> Path:
    gold = tmp_path / "gold" / "tisseo" / "static-1"
    write_csv(
        gold / "route_daily_trips.csv",
        [{"service_date": "2026-01-01", "route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3", "scheduled_trips_count": 10}],
    )
    write_csv(
        gold / "network_daily_summary.csv",
        [{"service_date": "2026-01-01", "active_routes_count": 1, "scheduled_trips_count": 10, "scheduled_stop_departures_count": 25, "active_stops_count": 2}],
    )
    write_csv(
        gold / "route_period_summary.csv",
        [{"route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3", "active_service_days": 1, "total_scheduled_trips": 10, "average_trips_per_active_day": 10, "max_daily_trips": 10}],
    )
    return gold


def trip_updates_feed(delay: int, header_timestamp: int = 1_700_000_000) -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = header_timestamp
    entity = feed.entity.add()
    entity.id = f"tu-{delay}"
    update = entity.trip_update
    update.trip.trip_id = f"T{delay}"
    update.trip.route_id = "R1"
    update.timestamp = header_timestamp + 5
    stop_update = update.stop_time_update.add()
    stop_update.stop_sequence = 1
    stop_update.stop_id = "S1"
    stop_update.arrival.delay = delay
    return feed.SerializeToString()


def test_collect_snapshots_preserves_raw_and_appends_partitioned_parquet(tmp_path: Path, monkeypatch) -> None:
    moments = iter(
        [
            datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 8, 0, 1, tzinfo=timezone.utc),
        ]
    )
    payloads = iter([trip_updates_feed(60), trip_updates_feed(120)])
    monkeypatch.setattr(historical_storage, "_utc_now", lambda: next(moments))

    def fetcher(url: str, timeout_seconds: int):
        return next(payloads), 200, "application/x-protobuf"

    first = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "trip_updates",
        url="https://example.test/feed.pb",
        raw_history_root=tmp_path / "raw",
        parsed_history_root=tmp_path / "history",
        fetcher=fetcher,
        poll_number=1,
    )
    second = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "trip_updates",
        url="https://example.test/feed.pb",
        raw_history_root=tmp_path / "raw",
        parsed_history_root=tmp_path / "history",
        fetcher=fetcher,
        poll_number=2,
    )
    history_run = tmp_path / "history" / "tisseo" / "trip_updates"
    parquet_files = sorted(history_run.glob("date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet"))
    rows = pd.concat([pd.read_parquet(path) for path in parquet_files], ignore_index=True)
    log_rows = (history_run / "collection_log.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert first["raw_path"] != second["raw_path"]
    assert len(parquet_files) == 2
    assert sorted(rows["poll_number"].tolist()) == [1, 2]
    assert set(rows["collection_date"]) == {"2026-01-01"}
    assert set(rows["collection_hour"]) == {"08"}
    assert len(log_rows) == 2
    assert all(json.loads(row)["snapshot_timestamp"] for row in log_rows)


def test_scheduler_collects_multiple_snapshots(tmp_path: Path) -> None:
    payloads = iter([trip_updates_feed(30), trip_updates_feed(90)])

    def fetcher(url: str, timeout_seconds: int):
        return next(payloads), 200, "application/x-protobuf"

    results = run_historical_collection(
        "tisseo",
        SOURCE,
        "trip_updates",
        interval_seconds=1,
        url="https://example.test/feed.pb",
        raw_history_root=tmp_path / "raw",
        parsed_history_root=tmp_path / "history",
        max_polls=2,
        fetcher=fetcher,
    )

    assert [result["poll_number"] for result in results] == [1, 2]
    assert len(list((tmp_path / "history" / "tisseo" / "trip_updates").glob("date=*/hour=*/snapshot_timestamp=*/trip_updates.parquet"))) == 2


def test_historical_kpis_and_duckdb_partition_views(tmp_path: Path, monkeypatch) -> None:
    moments = iter(
        [
            datetime(2026, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 2, 10, 0, 1, tzinfo=timezone.utc),
        ]
    )
    payloads = iter([trip_updates_feed(60), trip_updates_feed(180)])
    monkeypatch.setattr(historical_storage, "_utc_now", lambda: next(moments))

    def fetcher(url: str, timeout_seconds: int):
        return next(payloads), 200, "application/x-protobuf"

    for poll in (1, 2):
        collect_gtfs_rt_snapshot(
            "tisseo",
            SOURCE,
            "trip_updates",
            url="https://example.test/feed.pb",
            raw_history_root=tmp_path / "raw",
            parsed_history_root=tmp_path / "history",
            fetcher=fetcher,
            poll_number=poll,
        )

    history_run = tmp_path / "history" / "tisseo" / "trip_updates"
    history_gold = build_historical_kpis(history_run, tmp_path / "history_gold")
    serving_run = build_serving_database(make_gold_run(tmp_path), serving_root=tmp_path / "serving", history_run=history_run, history_gold_run=history_gold)
    db_path = serving_run / "mobility_control_tower.duckdb"
    routes = query_serving_database(db_path, "history-routes", limit=10)
    trend = query_serving_database(db_path, "history-delay-trend", limit=10)

    with duckdb.connect(str(db_path), read_only=True) as connection:
        names = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}

    assert (history_gold / "route_delay_history.parquet").is_file()
    assert "v_delay_history" in names
    assert "v_route_delay_history" in names
    assert routes.iloc[0]["average_delay_seconds"] == 120
    assert trend.iloc[0]["updates_collected"] == 2


def test_compute_historical_kpis_outputs_expected_tables() -> None:
    stops = pd.DataFrame(
        [
            {"route_id": "R1", "stop_id": "S1", "trip_id": "T1", "arrival_delay": 60, "departure_delay": "", "snapshot_timestamp": "s1", "collection_date": "2026-01-01", "collection_hour": "08"},
            {"route_id": "R1", "stop_id": "S1", "trip_id": "T2", "arrival_delay": 180, "departure_delay": "", "snapshot_timestamp": "s2", "collection_date": "2026-01-01", "collection_hour": "08"},
        ]
    )
    summary = pd.DataFrame(
        [
            {"snapshot_timestamp": "s1", "collection_date": "2026-01-01", "collection_hour": "08", "feed_age_seconds": 5, "parsed_entity_count": 1, "skipped_entity_count": 0},
            {"snapshot_timestamp": "s2", "collection_date": "2026-01-01", "collection_hour": "08", "feed_age_seconds": 15, "parsed_entity_count": 1, "skipped_entity_count": 0},
        ]
    )

    tables = compute_historical_kpis(stops, summary)

    assert set(tables) == {"route_delay_history", "stop_delay_history", "delay_evolution_by_hour", "feed_freshness_trend", "trip_match_trend", "daily_summary"}
    assert tables["route_delay_history"].iloc[0]["average_delay_seconds"] == 120
    assert tables["feed_freshness_trend"].iloc[0]["average_feed_age_seconds"] == 10


def test_history_api_endpoints_and_dashboard_client_names(tmp_path: Path, monkeypatch) -> None:
    moments = iter([datetime(2026, 1, 3, 11, 0, 0, tzinfo=timezone.utc)])
    monkeypatch.setattr(historical_storage, "_utc_now", lambda: next(moments))

    collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "trip_updates",
        url="https://example.test/feed.pb",
        raw_history_root=tmp_path / "raw",
        parsed_history_root=tmp_path / "history",
        fetcher=lambda url, timeout_seconds: (trip_updates_feed(45), 200, "application/x-protobuf"),
    )
    history_run = tmp_path / "history" / "tisseo" / "trip_updates"
    history_gold = build_historical_kpis(history_run, tmp_path / "history_gold")
    serving_run = build_serving_database(make_gold_run(tmp_path), serving_root=tmp_path / "serving", history_run=history_run, history_gold_run=history_gold)
    request = FakeRequest(create_app(serving_run / "mobility_control_tower.duckdb"))

    assert history_routes(request, limit=10)["data"][0]["route_id"] == "R1"
    assert history_stops(request, limit=10)["data"][0]["stop_id"] == "S1"
    assert history_feed_health(request, limit=10)["count"] == 1
    assert history_delay_trend(request, limit=10)["data"][0]["updates_collected"] == 1
    assert history_summary(request, limit=10)["data"][0]["snapshots_collected"] == 1
    assert ENDPOINTS["history_routes"] == "/history/routes"
    assert ENDPOINTS["history_feed_health"] == "/history/feed-health"
