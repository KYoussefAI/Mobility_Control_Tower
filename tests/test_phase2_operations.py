from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.api.app import create_app
from mobility_control_tower.observability_exporter import collect_operational_metrics
from mobility_control_tower.operations.watermarks import advance_watermark_after_publish, read_watermark, select_snapshots_after_watermark, watermark_lock
from mobility_control_tower.realtime import historical_storage
from mobility_control_tower.realtime.historical_storage import collect_gtfs_rt_snapshot, deterministic_snapshot_id, discover_committed_snapshots
from mobility_control_tower.serving.duckdb_loader import build_serving_database, current_pointer_path, resolve_current_database

SOURCE = {"name": "Tisseo"}


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


def test_deterministic_snapshot_identity_is_content_based() -> None:
    moment = historical_storage._utc_now()
    first = deterministic_snapshot_id("tisseo", "trip_updates", trip_updates_feed(60), moment)
    second = deterministic_snapshot_id("tisseo", "trip_updates", trip_updates_feed(60), moment)
    third = deterministic_snapshot_id("tisseo", "trip_updates", trip_updates_feed(120), moment)

    assert first == second
    assert first[0] != third[0]


def test_duplicate_snapshot_is_noop_and_conflicting_existing_snapshot_fails(tmp_path: Path, monkeypatch) -> None:
    moment = historical_storage._utc_now()
    monkeypatch.setattr(historical_storage, "_utc_now", lambda: moment)

    def fetcher(url: str, timeout_seconds: int):
        return trip_updates_feed(60), 200, "application/x-protobuf"

    first = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "trip_updates",
        url="https://example.test",
        raw_history_root=tmp_path / "raw",
        parsed_history_root=tmp_path / "history",
        fetcher=fetcher,
    )
    second = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "trip_updates",
        url="https://example.test",
        raw_history_root=tmp_path / "raw",
        parsed_history_root=tmp_path / "history",
        fetcher=fetcher,
    )

    assert second["duplicate"] is True
    history_run = tmp_path / "history" / "tisseo" / "trip_updates"
    assert len(discover_committed_snapshots(history_run)) == 1

    parsed = Path(first["parsed_path"])
    metadata = json.loads((parsed / "metadata.json").read_text(encoding="utf-8"))
    metadata["sha256"] = "different"
    (parsed / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(FileExistsError):
        collect_gtfs_rt_snapshot(
            "tisseo",
            SOURCE,
            "trip_updates",
            url="https://example.test",
            raw_history_root=tmp_path / "raw",
            parsed_history_root=tmp_path / "history",
            fetcher=fetcher,
        )


def test_incomplete_snapshot_is_ignored(tmp_path: Path) -> None:
    snapshot = tmp_path / "history" / "tisseo" / "trip_updates" / "date=2026-01-01" / "hour=08" / "snapshot_timestamp=s1"
    snapshot.mkdir(parents=True)
    (snapshot / "metadata.json").write_text('{"snapshot_id": "s1"}\n', encoding="utf-8")

    assert discover_committed_snapshots(tmp_path / "history" / "tisseo" / "trip_updates") == []


def test_watermark_advance_after_success_and_lock_conflict(tmp_path: Path) -> None:
    root = tmp_path / "watermarks"
    snapshot = {"snapshot_id": "s2", "collection_time": "2026-01-01T08:00:00+00:00", "feed_header_timestamp": 1760000000}
    with watermark_lock(root, "tisseo", "trip_updates", "incremental_refresh"):
        with pytest.raises(RuntimeError):
            with watermark_lock(root, "tisseo", "trip_updates", "incremental_refresh"):
                pass
        path = advance_watermark_after_publish(
            root,
            source="tisseo",
            feed_type="trip_updates",
            workflow="incremental_refresh",
            snapshot=snapshot,
            serving_run_id="serving_1",
        )

    watermark = read_watermark(root, "tisseo", "trip_updates", "incremental_refresh")
    selected = select_snapshots_after_watermark([{"snapshot_id": "s1"}, {"snapshot_id": "s2"}, {"snapshot_id": "s3"}], watermark, lookback_count=1)
    assert path.is_file()
    assert watermark["latest_successfully_processed_snapshot"] == "s2"
    assert [row["snapshot_id"] for row in selected] == ["s2", "s3"]


def test_serving_pointer_atomic_publication_and_failure_preserves_current(tmp_path: Path) -> None:
    gold = make_gold_run(tmp_path)
    serving_root = tmp_path / "serving"
    first = build_serving_database(gold, serving_root=serving_root, serving_run_id="serving_ok")
    pointer_before = current_pointer_path("tisseo", serving_root).read_text(encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        build_serving_database(tmp_path / "missing_gold", serving_root=serving_root, serving_run_id="serving_bad")

    assert current_pointer_path("tisseo", serving_root).read_text(encoding="utf-8") == pointer_before
    assert resolve_current_database("tisseo", serving_root) == first / "mobility_control_tower.duckdb"


def test_api_readiness_before_and_after_serving_publication(tmp_path: Path) -> None:
    app = create_app(None, source="tisseo", serving_root=tmp_path / "serving")
    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503

    build_serving_database(make_gold_run(tmp_path), serving_root=tmp_path / "serving")
    ready = client.get("/health/ready")

    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_metrics_exporter_uses_bounded_labels(tmp_path: Path) -> None:
    serving_root = tmp_path / "serving"
    build_serving_database(make_gold_run(tmp_path), serving_root=serving_root)
    content = collect_operational_metrics(
        source="tisseo", serving_root=serving_root, history_root=tmp_path / "history", watermark_root=tmp_path / "watermarks", quality_root=tmp_path / "quality"
    )
    text = content.decode()

    assert "mct_serving_artifact_ready" in text
    assert "serving_run_id" not in text
    assert "snapshot_id" not in text


def test_interrupted_temp_serving_directory_is_not_current(tmp_path: Path) -> None:
    gold = make_gold_run(tmp_path)
    serving_root = tmp_path / "serving"
    build_serving_database(gold, serving_root=serving_root, serving_run_id="serving_ok")
    temp = serving_root / "tisseo" / "runs" / ".interrupted.tmp"
    temp.mkdir(parents=True)
    with duckdb.connect(str(temp / "mobility_control_tower.duckdb")) as connection:
        connection.execute("create table partial(id integer)")

    current = json.loads(current_pointer_path("tisseo", serving_root).read_text(encoding="utf-8"))
    assert current["serving_run_id"] == "serving_ok"
