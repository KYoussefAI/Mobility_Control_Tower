from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from google.transit import gtfs_realtime_pb2

from mct_solo.config import load_source
from mct_solo.realtime_pipeline import preserve_realtime_bytes


def trip_updates_payload() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_767_268_770
    entity = feed.entity.add()
    entity.id = "update-1"
    update = entity.trip_update
    update.trip.trip_id = "T1"
    update.trip.route_id = "R1"
    update.trip.start_date = "20260101"
    update.timestamp = 1_767_268_775

    first = update.stop_time_update.add()
    first.stop_sequence = 1
    first.stop_id = "S1"
    first.arrival.delay = 120
    first.departure.delay = 999

    second = update.stop_time_update.add()
    second.stop_sequence = 2
    second.stop_id = "S2"
    second.departure.delay = 420
    return feed.SerializeToString()


def test_realtime_parse_preserve_and_retry_are_idempotent(tmp_path) -> None:
    collected_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    first = preserve_realtime_bytes(trip_updates_payload(), load_source(), tmp_path, collected_at=collected_at)
    second = preserve_realtime_bytes(trip_updates_payload(), load_source(), tmp_path, collected_at=collected_at)
    parquet = next((tmp_path / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(parquet).sort_values("stop_sequence")

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert len(list((tmp_path / "raw" / "realtime").glob("date=*/*/feed.pb"))) == 1
    assert rows["observed_delay"].tolist() == [120, 420]
    assert first["feed_age_seconds"] == 30
