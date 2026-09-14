from pathlib import Path

import pandas as pd
from google.transit import gtfs_realtime_pb2

import mobility_control_tower.realtime.historical_storage as history


def _payload() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1789290000
    entity = feed.entity.add()
    entity.id = "trip-1"
    entity.trip_update.trip.trip_id = "T1"
    update = entity.trip_update.stop_time_update.add()
    update.stop_id = "S1"
    update.arrival.delay = 45
    return feed.SerializeToString()


def test_history_commit_is_immutable_and_duplicate_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    moment = history.datetime(2026, 9, 13, 10, 0, tzinfo=history.timezone.utc)
    monkeypatch.setattr(history, "_utc_now", lambda: moment)

    def fetcher(url: str, timeout: int) -> tuple[bytes, int, str]:
        return _payload(), 200, "application/x-protobuf"

    source = {"name": "Test", "realtime": {"trip_updates": {"enabled": True, "url": "https://example.test/feed.pb"}}}
    first = history.collect_gtfs_rt_snapshot(
        "test", source, "trip_updates", raw_history_root=tmp_path / "raw", parsed_history_root=tmp_path / "history", fetcher=fetcher
    )
    second = history.collect_gtfs_rt_snapshot(
        "test", source, "trip_updates", raw_history_root=tmp_path / "raw", parsed_history_root=tmp_path / "history", fetcher=fetcher
    )
    assert first["sha256"] == second["sha256"]
    assert second["duplicate"] is True
    committed = history.discover_committed_snapshots(tmp_path / "history" / "test" / "trip_updates")
    assert len(committed) == 1
    parsed = Path(committed[0]["parsed_path"])
    assert (parsed / "_SUCCESS").is_file()
    assert len(pd.read_parquet(parsed / "trip_updates.parquet")) == 1


def test_incomplete_history_partition_is_not_discoverable(tmp_path: Path) -> None:
    partial = tmp_path / "history" / "date=2026-09-13" / "hour=10" / "snapshot_timestamp=partial"
    partial.mkdir(parents=True)
    (partial / "metadata.json").write_text('{"feed_type":"trip_updates"}', encoding="utf-8")
    assert history.discover_committed_snapshots(tmp_path / "history") == []
