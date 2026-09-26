"""Create deterministic Parquet inputs for CI; this is not real-source evidence."""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from google.transit import gtfs_realtime_pb2

from mct_solo.config import load_source
from mct_solo.realtime_pipeline import ensure_empty_realtime_tables, preserve_realtime_bytes
from mct_solo.static_pipeline import preserve_static_bytes, transform_static

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def gtfs_fixture() -> bytes:
    buffer = io.BytesIO()
    fixture_dir = PROJECT_ROOT / "tests" / "fixtures" / "static"
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(fixture_dir.glob("*.txt")):
            archive.write(path, path.name)
    return buffer.getvalue()


def realtime_fixture() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_767_268_770
    entity = feed.entity.add()
    entity.id = "ci-update-1"
    update = entity.trip_update
    update.trip.trip_id = "T1"
    update.trip.route_id = "R1"
    update.trip.start_date = "20260101"
    update.timestamp = 1_767_268_775
    first = update.stop_time_update.add()
    first.stop_sequence = 1
    first.stop_id = "S1"
    first.arrival.delay = 120
    second = update.stop_time_update.add()
    second.stop_sequence = 2
    second.stop_id = "S2"
    second.departure.delay = 420
    return feed.SerializeToString()


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else PROJECT_ROOT / "data" / "ci").resolve()
    source = load_source()
    raw = preserve_static_bytes(
        gtfs_fixture(),
        source,
        root,
        source_url="fixture://tisseo-static",
        ingested_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    silver = transform_static(raw, root)
    ensure_empty_realtime_tables(root)
    preserve_realtime_bytes(
        realtime_fixture(),
        source,
        root,
        source_url="fixture://tisseo-trip-updates",
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    print(silver)


if __name__ == "__main__":
    main()
