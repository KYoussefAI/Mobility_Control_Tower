import json
import time
from pathlib import Path

import pandas as pd
import pytest
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.realtime.gtfs_rt_compatibility import check_realtime_compatibility
from mobility_control_tower.realtime.gtfs_rt_kpis import build_rt_gold
from mobility_control_tower.realtime.gtfs_rt_parser import parse_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_raw import preserve_realtime_snapshot

SOURCE = {"name": "Test", "source_page_url": "https://example.test"}


def _feed(timestamp: int | None = None) -> gtfs_realtime_pb2.FeedMessage:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    if timestamp is not None:
        feed.header.timestamp = timestamp
    return feed


def _add_trip(feed: gtfs_realtime_pb2.FeedMessage, *, entity_id: str, trip_id: str = "T1", route_id: str = "R1") -> None:
    entity = feed.entity.add()
    entity.id = entity_id
    entity.trip_update.trip.trip_id = trip_id
    entity.trip_update.trip.route_id = route_id
    update = entity.trip_update.stop_time_update.add()
    update.stop_id = "S1"
    update.arrival.delay = 30


def _raw(tmp_path: Path, payload: bytes) -> Path:
    return preserve_realtime_snapshot(
        payload,
        "test",
        SOURCE,
        "trip_updates",
        "https://example.test/trip-updates.pb",
        tmp_path / "raw",
    )


def _summary(parsed: Path) -> dict[str, str]:
    return pd.read_csv(parsed / "rt_feed_summary.csv", dtype=str, keep_default_na=False).iloc[0].to_dict()


def _silver(tmp_path: Path) -> Path:
    silver = tmp_path / "silver" / "test" / "run"
    silver.mkdir(parents=True)
    (silver / "routes.csv").write_text("route_id\nR1\nR2\n", encoding="utf-8")
    (silver / "trips.csv").write_text("trip_id,route_id\nT1,R1\n", encoding="utf-8")
    (silver / "stops.csv").write_text("stop_id\nS1\n", encoding="utf-8")
    return silver


def test_truncated_protobuf_is_rejected_without_partial_output(tmp_path: Path) -> None:
    raw = _raw(tmp_path, b"\x0a\xff")
    with pytest.raises(ValueError, match="Unable to parse"):
        parse_realtime_snapshot(raw, tmp_path / "parsed")
    assert not (tmp_path / "parsed").exists()


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [(None, "MISSING"), (int(time.time()) - 3_600, "STALE"), (int(time.time()) + 3_600, "FUTURE")],
)
def test_untrusted_feed_timestamps_disable_operational_metrics(tmp_path: Path, timestamp: int | None, expected: str) -> None:
    feed = _feed(timestamp)
    _add_trip(feed, entity_id="one")
    parsed = parse_realtime_snapshot(_raw(tmp_path, feed.SerializeToString()), tmp_path / "parsed")
    summary = _summary(parsed)
    assert summary["feed_timestamp_status"] == expected
    assert summary["operationally_usable"] == "False"

    gold = build_rt_gold(_silver(tmp_path), parsed, tmp_path / "gold")
    assert pd.read_csv(gold / "rt_route_delay_snapshot.csv").empty


def test_valid_empty_feed_degrades_to_diagnostic_summary(tmp_path: Path) -> None:
    feed = _feed(int(time.time()))
    parsed = parse_realtime_snapshot(_raw(tmp_path, feed.SerializeToString()), tmp_path / "parsed")
    summary = _summary(parsed)
    assert summary["entity_count"] == "0"
    assert summary["operationally_usable"] == "False"
    assert "EMPTY_FEED" in summary["diagnostic_codes"]


def test_duplicate_entities_missing_trip_ids_and_unusable_partial_updates_are_skipped(tmp_path: Path) -> None:
    feed = _feed(int(time.time()))
    _add_trip(feed, entity_id="duplicate")
    _add_trip(feed, entity_id="duplicate")
    _add_trip(feed, entity_id="missing-trip", trip_id="")
    partial = feed.entity.add()
    partial.id = "partial"
    partial.trip_update.trip.trip_id = "T2"
    partial.trip_update.stop_time_update.add().stop_id = "S1"

    parsed = parse_realtime_snapshot(_raw(tmp_path, feed.SerializeToString()), tmp_path / "parsed")
    summary = _summary(parsed)
    assert summary["parsed_entity_count"] == "1"
    assert summary["skipped_entity_count"] == "3"
    assert summary["duplicate_entity_count"] == "1"
    assert summary["unusable_stop_time_update_count"] == "1"
    assert len(pd.read_csv(parsed / "rt_trip_updates.csv")) == 1


def test_explicit_cancellation_without_stop_updates_is_usable(tmp_path: Path) -> None:
    feed = _feed(int(time.time()))
    entity = feed.entity.add()
    entity.id = "cancelled"
    entity.trip_update.trip.trip_id = "T1"
    entity.trip_update.trip.route_id = "R1"
    entity.trip_update.trip.schedule_relationship = gtfs_realtime_pb2.TripDescriptor.CANCELED
    parsed = parse_realtime_snapshot(_raw(tmp_path, feed.SerializeToString()), tmp_path / "parsed")
    trip = pd.read_csv(parsed / "rt_trip_updates.csv", dtype=str, keep_default_na=False).iloc[0]
    assert trip["schedule_relationship"] == "CANCELED"
    assert _summary(parsed)["operationally_usable"] == "True"


def test_unknown_trip_and_conflicting_trip_route_relationship_are_diagnostics(tmp_path: Path) -> None:
    feed = _feed(int(time.time()))
    _add_trip(feed, entity_id="unknown", trip_id="UNKNOWN", route_id="R1")
    _add_trip(feed, entity_id="wrong-route", trip_id="T1", route_id="R2")
    parsed = parse_realtime_snapshot(_raw(tmp_path, feed.SerializeToString()), tmp_path / "parsed")
    report_path, _ = check_realtime_compatibility(_silver(tmp_path), parsed, tmp_path / "reports")
    checks = {row["check_name"]: row for row in json.loads(report_path.read_text(encoding="utf-8"))["checks"]}
    assert checks["trip_id_matches_static_trips"]["status"] == "WARN"
    assert checks["trip_route_relationship_matches_static"]["status"] == "WARN"
    assert checks["trip_route_relationship_matches_static"]["unmatched_count"] == 2
