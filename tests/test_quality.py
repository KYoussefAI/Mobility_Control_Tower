from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from test_realtime_pipeline import trip_updates_payload

from mobility_control_tower.config import load_source
from mobility_control_tower.quality import validate_realtime, validate_static
from mobility_control_tower.realtime_pipeline import preserve_realtime_bytes
from mobility_control_tower.static_pipeline import preserve_static_bytes, transform_static


def test_static_quality_passes_fixture(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    silver = transform_static(raw, tmp_path)
    report = validate_static(silver)
    assert report["status"] == "PASS"


def test_static_quality_detects_unknown_route(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    silver = transform_static(raw, tmp_path)
    trips_path = silver / "trips.parquet"
    trips = pd.read_parquet(trips_path)
    trips.loc[0, "route_id"] = "NOT_A_ROUTE"
    trips.to_parquet(trips_path, index=False)

    report = validate_static(silver)
    failed = {check["name"] for check in report["checks"] if check["status"] == "FAIL"}
    assert "trips_reference_routes" in failed


def test_static_quality_rejects_blank_stop_identifier(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    silver = transform_static(raw, tmp_path)
    stops_path = silver / "stops.parquet"
    stops = pd.read_parquet(stops_path)
    stops.loc[0, "stop_id"] = "  "
    stops.to_parquet(stops_path, index=False)

    report = validate_static(silver)
    failed = {check["name"] for check in report["checks"] if check["status"] == "FAIL"}
    assert "stop_id_not_null" in failed


def test_realtime_quality_passes_fixture(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    assert validate_realtime(tmp_path)["status"] == "PASS"


def test_realtime_outlier_is_warned_and_not_a_pipeline_failure(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    path = next((tmp_path / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(path)
    rows.loc[0, "observed_delay"] = -86400
    rows.to_parquet(path, index=False)

    report = validate_realtime(tmp_path)
    assert report["status"] == "WARN"
    assert next(check for check in report["checks"] if check["name"] == "delay_sanity")["problem_count"] == 1


def test_realtime_delay_sanity_boundary_is_inclusive(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    path = next((tmp_path / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(path)
    boundary_rows = pd.concat([rows.iloc[[0]]] * 5, ignore_index=True)
    boundary_rows["entity_id"] = ["missing", "negative-out", "negative-edge", "positive-edge", "positive-out"]
    boundary_rows["stop_sequence"] = range(101, 106)
    boundary_rows["observed_delay"] = pd.array([None, -7201, -7200, 7200, 7201], dtype="Int64")
    boundary_rows.to_parquet(path, index=False)

    report = validate_realtime(tmp_path)
    delay_check = next(check for check in report["checks"] if check["name"] == "delay_sanity")
    assert report["status"] == "WARN"
    assert delay_check["problem_count"] == 2


def test_realtime_duplicate_source_keys_are_warnings(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    realtime = tmp_path / "silver" / "realtime"
    for table in ("trip_updates", "stop_time_updates"):
        path = next((realtime / table).glob("date=*/*.parquet"))
        rows = pd.read_parquet(path)
        pd.concat([rows, rows.iloc[[0]]], ignore_index=True).to_parquet(path, index=False)

    report = validate_realtime(tmp_path)
    checks = {check["name"]: check for check in report["checks"]}
    assert report["status"] == "WARN"
    assert checks["trip_update_key_unique"]["status"] == "WARN"
    assert checks["stop_update_key_unique"]["status"] == "WARN"


def test_realtime_missing_trip_identifier_remains_fatal(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    path = next((tmp_path / "silver" / "realtime" / "trip_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(path)
    rows.loc[0, "trip_id"] = None
    rows.to_parquet(path, index=False)

    report = validate_realtime(tmp_path)
    check = next(check for check in report["checks"] if check["name"] == "trip_id_not_null")
    assert report["status"] == "FAIL"
    assert check["status"] == "FAIL"
