import hashlib
import json
from pathlib import Path

import pytest

from mobility_control_tower.realtime.gtfs_rt_raw import fetch_realtime_snapshot, preserve_realtime_snapshot

SOURCE = {
    "name": "Test Transit",
    "source_page_url": "https://example.test/source",
    "static_gtfs": {"url": "https://example.test/static.zip"},
    "realtime": {"trip_updates": {"enabled": True, "url": "https://example.test/trips.pb"}},
}


def test_preserve_realtime_snapshot_writes_immutable_payload_and_provenance(tmp_path: Path) -> None:
    payload = b"protobuf-evidence"
    run = preserve_realtime_snapshot(payload, "test", SOURCE, "trip_updates", "https://example.test/trips.pb", tmp_path)
    metadata = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
    assert (run / "feed.pb").read_bytes() == payload
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    assert metadata["file_size_bytes"] == len(payload)
    assert metadata["fetched_at"].endswith("+00:00")


def test_empty_payload_and_unknown_feed_type_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        preserve_realtime_snapshot(b"", "test", SOURCE, "trip_updates", "https://example.test/trips.pb", tmp_path)
    with pytest.raises(ValueError, match="Unsupported"):
        preserve_realtime_snapshot(b"bytes", "test", SOURCE, "unknown", "https://example.test/feed.pb", tmp_path)


def test_fetch_rejects_redirects_without_persisting(tmp_path: Path, monkeypatch) -> None:
    response = type("Response", (), {"status_code": 302, "content": b"redirect", "headers": {"location": "https://other.test"}})()
    monkeypatch.setattr("mobility_control_tower.realtime.gtfs_rt_raw.requests.get", lambda *args, **kwargs: response)
    with pytest.raises(RuntimeError, match="redirects are disabled"):
        fetch_realtime_snapshot("test", SOURCE, "trip_updates", raw_root=tmp_path)
    assert not any(tmp_path.rglob("feed.pb"))
