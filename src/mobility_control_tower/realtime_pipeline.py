"""Preserve and normalize one GTFS-Realtime Trip Updates snapshot."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

from .config import SourceConfig
from .io import sha256_bytes, utc_now, write_json, write_parquet_atomic

TRIP_COLUMNS = [
    "snapshot_id",
    "collected_at",
    "service_date",
    "entity_id",
    "trip_id",
    "route_id",
    "direction_id",
    "schedule_relationship",
    "update_timestamp",
]
STOP_COLUMNS = TRIP_COLUMNS + ["stop_id", "stop_sequence", "arrival_delay", "departure_delay", "observed_delay"]
SNAPSHOT_COLUMNS = [
    "snapshot_id",
    "collected_at",
    "collection_date",
    "source_url",
    "sha256",
    "size_bytes",
    "feed_version",
    "header_timestamp",
    "feed_age_seconds",
    "entity_count",
    "trip_update_count",
    "stop_time_update_count",
]


def _enum_name(wrapper: Any, value: int) -> str:
    try:
        return str(wrapper.Name(value))
    except ValueError:
        return f"UNKNOWN_{value}"


def parse_trip_updates(content: bytes, collected_at: datetime) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    if not feed.header.gtfs_realtime_version:
        raise ValueError("GTFS-Realtime feed header has no version")

    checksum = sha256_bytes(content)
    header_timestamp = int(feed.header.timestamp) if feed.header.HasField("timestamp") else None
    identity_time = str(header_timestamp) if header_timestamp is not None else collected_at.strftime("%Y%m%dT%H%M%S")
    snapshot_id = f"{identity_time}-{checksum[:12]}"
    trip_rows: list[dict[str, Any]] = []
    stop_rows: list[dict[str, Any]] = []
    relationship = gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        update = entity.trip_update
        descriptor = update.trip
        base = {
            "snapshot_id": snapshot_id,
            "collected_at": collected_at,
            "service_date": descriptor.start_date or None,
            "entity_id": entity.id,
            "trip_id": descriptor.trip_id or None,
            "route_id": descriptor.route_id or None,
            "direction_id": int(descriptor.direction_id) if descriptor.HasField("direction_id") else None,
            "schedule_relationship": _enum_name(relationship, descriptor.schedule_relationship),
            "update_timestamp": datetime.fromtimestamp(update.timestamp, tz=UTC) if update.timestamp else None,
        }
        trip_rows.append(base)
        for stop_update in update.stop_time_update:
            arrival_delay = (
                int(stop_update.arrival.delay)
                if stop_update.HasField("arrival") and stop_update.arrival.HasField("delay")
                else None
            )
            departure_delay = (
                int(stop_update.departure.delay)
                if stop_update.HasField("departure") and stop_update.departure.HasField("delay")
                else None
            )
            stop_rows.append(
                {
                    **base,
                    "stop_id": stop_update.stop_id or None,
                    "stop_sequence": int(stop_update.stop_sequence) if stop_update.HasField("stop_sequence") else None,
                    "arrival_delay": arrival_delay,
                    "departure_delay": departure_delay,
                    "observed_delay": arrival_delay if arrival_delay is not None else departure_delay,
                }
            )

    trips = pd.DataFrame(trip_rows, columns=TRIP_COLUMNS)
    stops = pd.DataFrame(stop_rows, columns=STOP_COLUMNS)
    metadata = {
        "snapshot_id": snapshot_id,
        "collected_at": collected_at.isoformat(),
        "collection_date": collected_at.date().isoformat(),
        "sha256": checksum,
        "size_bytes": len(content),
        "feed_version": feed.header.gtfs_realtime_version,
        "header_timestamp": (
            datetime.fromtimestamp(header_timestamp, tz=UTC).isoformat() if header_timestamp is not None else None
        ),
        "feed_age_seconds": int(collected_at.timestamp() - header_timestamp) if header_timestamp is not None else None,
        "entity_count": len(feed.entity),
        "trip_update_count": len(trips),
        "stop_time_update_count": len(stops),
    }
    return trips, stops, metadata


def preserve_realtime_bytes(
    content: bytes,
    source: SourceConfig,
    root: Path,
    *,
    source_url: str | None = None,
    collected_at: datetime | None = None,
    http_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    moment = (collected_at or utc_now()).astimezone(UTC)
    trips, stops, metadata = parse_trip_updates(content, moment)
    metadata.update(
        {"source_id": source.id, "source_url": source_url or source.trip_updates_url, "http": http_metadata or {}}
    )
    date = metadata["collection_date"]
    snapshot_id = metadata["snapshot_id"]
    raw_dir = root / "raw" / "realtime" / f"date={date}" / snapshot_id
    silver_files = {
        "trip_updates": root / "silver" / "realtime" / "trip_updates" / f"date={date}" / f"{snapshot_id}.parquet",
        "stop_time_updates": root
        / "silver"
        / "realtime"
        / "stop_time_updates"
        / f"date={date}"
        / f"{snapshot_id}.parquet",
        "feed_snapshots": root / "silver" / "realtime" / "feed_snapshots" / f"date={date}" / f"{snapshot_id}.parquet",
    }
    if (raw_dir / "_SUCCESS").is_file() and all(path.is_file() for path in silver_files.values()):
        saved = json.loads((raw_dir / "metadata.json").read_text(encoding="utf-8"))
        return {**saved, "duplicate": True}

    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "feed.pb"
    if raw_file.exists() and sha256_bytes(raw_file.read_bytes()) != metadata["sha256"]:
        raise ValueError(f"Snapshot collision at {raw_dir}")
    raw_file.write_bytes(content)
    metadata["raw_path"] = str(raw_file.resolve())
    write_json(raw_dir / "metadata.json", metadata)

    snapshot_row = pd.DataFrame(
        [{column: metadata.get(column) for column in SNAPSHOT_COLUMNS}],
        columns=SNAPSHOT_COLUMNS,
    )
    write_parquet_atomic(trips, silver_files["trip_updates"])
    write_parquet_atomic(stops, silver_files["stop_time_updates"])
    write_parquet_atomic(snapshot_row, silver_files["feed_snapshots"])
    (raw_dir / "_SUCCESS").write_text("ok\n", encoding="utf-8")
    return {**metadata, "duplicate": False}


def download_realtime(source: SourceConfig, root: Path, *, timeout_seconds: int = 30) -> dict[str, Any]:
    response = requests.get(source.trip_updates_url, timeout=timeout_seconds)
    response.raise_for_status()
    return preserve_realtime_bytes(
        response.content,
        source,
        root,
        source_url=response.url,
        http_metadata={"status_code": response.status_code, "content_type": response.headers.get("content-type")},
    )


def ensure_empty_realtime_tables(root: Path) -> None:
    """Create schema-only files so a static-only dbt build remains reproducible."""
    base = root / "silver" / "realtime"
    empty_tables = {
        "trip_updates": pd.DataFrame(columns=TRIP_COLUMNS),
        "stop_time_updates": pd.DataFrame(columns=STOP_COLUMNS),
        "feed_snapshots": pd.DataFrame(columns=SNAPSHOT_COLUMNS),
    }
    for name, frame in empty_tables.items():
        path = base / name / "_empty.parquet"
        if not path.exists():
            write_parquet_atomic(frame, path)
