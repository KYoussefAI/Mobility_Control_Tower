"""Historical GTFS-Realtime polling and Parquet archive helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any

import pandas as pd
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.observability import FEED_FRESHNESS, HISTORICAL_POLLS, ROWS_PROCESSED
from mobility_control_tower.realtime.gtfs_rt_parser import _alerts, _summary, _trip_updates, _vehicle_positions
from mobility_control_tower.realtime.gtfs_rt_raw import FEED_TYPES, configured_realtime_url

Fetcher = Callable[[str, int], tuple[bytes, int | None, str | None]]
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot_id(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H-%M-%S.%fZ")


def _feed_header_timestamp(content: bytes) -> int | None:
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(content)
    except Exception:
        return None
    if feed.header.HasField("timestamp"):
        return int(feed.header.timestamp)
    return None


def deterministic_snapshot_id(source_id: str, feed_type: str, content: bytes, collection_dt: datetime) -> tuple[str, str, int | None]:
    checksum = hashlib.sha256(content).hexdigest()
    header_timestamp = _feed_header_timestamp(content)
    timestamp_part = str(header_timestamp) if header_timestamp is not None else _snapshot_id(collection_dt)
    return f"{source_id}_{feed_type}_{timestamp_part}_{checksum[:16]}", checksum, header_timestamp


def _partition_parts(moment: datetime) -> tuple[str, str]:
    return moment.strftime("%Y-%m-%d"), moment.strftime("%H")


def _default_fetcher(url: str, timeout_seconds: int) -> tuple[bytes, int | None, str | None]:
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch GTFS-Realtime snapshot from {url}: {exc}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"GTFS-Realtime request failed with HTTP {response.status_code} for {url}")
    return response.content, response.status_code, response.headers.get("content-type")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _read_existing_metadata(parsed_dir: Path) -> dict[str, Any] | None:
    metadata_path = parsed_dir / "metadata.json"
    if not metadata_path.is_file():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _required_files(feed_type: str) -> tuple[str, ...]:
    if feed_type == "trip_updates":
        return ("trip_updates.parquet", "stop_time_updates.parquet", "feed_summary.parquet", "metadata.json", "_SUCCESS")
    if feed_type == "vehicle_positions":
        return ("vehicle_positions.parquet", "feed_summary.parquet", "metadata.json", "_SUCCESS")
    if feed_type == "service_alerts":
        return ("alerts.parquet", "alert_informed_entities.parquet", "feed_summary.parquet", "metadata.json", "_SUCCESS")
    return ("metadata.json", "_SUCCESS")


def _commit_marker_valid(parsed_dir: Path, feed_type: str | None = None) -> bool:
    if feed_type is None:
        metadata = _read_existing_metadata(parsed_dir) or {}
        feed_type = str(metadata.get("feed_type", "trip_updates"))
    required = _required_files(feed_type)
    return all((parsed_dir / name).is_file() for name in required)


def discover_committed_snapshots(history_run: Path) -> list[dict[str, Any]]:
    """Return committed historical snapshots in deterministic order."""
    if not history_run.is_dir():
        return []
    snapshots: list[dict[str, Any]] = []
    for metadata_path in sorted(history_run.glob("date=*/hour=*/snapshot_timestamp=*/metadata.json")):
        parsed_dir = metadata_path.parent
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not _commit_marker_valid(parsed_dir, str(metadata.get("feed_type", "trip_updates"))):
            continue
        metadata["parsed_path"] = str(parsed_dir)
        snapshots.append(metadata)
    return sorted(snapshots, key=lambda row: (row.get("collection_time", ""), row.get("snapshot_id", row.get("snapshot_timestamp", ""))))


def _add_history_metadata(
    frame: pd.DataFrame,
    *,
    snapshot_timestamp: str,
    collection_time: str,
    feed_age_seconds: int | None,
    poll_number: int,
    collection_date: str,
    collection_hour: str,
    source_id: str,
    feed_type: str,
    checksum: str,
    header_timestamp: int | None,
) -> pd.DataFrame:
    result = frame.copy()
    result["source"] = source_id
    result["feed_type"] = feed_type
    result["snapshot_id"] = snapshot_timestamp
    result["snapshot_timestamp"] = snapshot_timestamp
    result["collection_time"] = collection_time
    result["feed_header_timestamp"] = header_timestamp
    result["payload_checksum"] = checksum
    result["feed_age_seconds"] = feed_age_seconds
    result["poll_number"] = poll_number
    result["collection_date"] = collection_date
    result["collection_hour"] = collection_hour
    return result


def _to_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Historical Parquet file already exists and will not be overwritten: {path}")
    frame.replace("", pd.NA).to_parquet(path, index=False, engine="pyarrow")


def _parse_feed(content: bytes, feed_type: str, fetched_at: str) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(content)
    except Exception as exc:
        raise ValueError(f"Unable to parse GTFS-Realtime protobuf snapshot: {exc}") from exc
    if feed_type == "trip_updates":
        trips, stops, parsed, skipped = _trip_updates(feed)
        return {"trip_updates": trips, "stop_time_updates": stops}, _summary(feed, feed_type, fetched_at, parsed, skipped)
    if feed_type == "vehicle_positions":
        vehicles, parsed, skipped = _vehicle_positions(feed)
        return {"vehicle_positions": vehicles}, _summary(feed, feed_type, fetched_at, parsed, skipped)
    if feed_type == "service_alerts":
        alerts, informed, parsed, skipped = _alerts(feed)
        return {"alerts": alerts, "alert_informed_entities": informed}, _summary(feed, feed_type, fetched_at, parsed, skipped)
    raise ValueError(f"Historical collection does not support feed type '{feed_type}'")


def collect_gtfs_rt_snapshot(
    source_id: str,
    source: dict[str, Any],
    feed_type: str,
    *,
    url: str | None = None,
    raw_history_root: Path = Path("data/raw_realtime/historical"),
    parsed_history_root: Path = Path("data/realtime_history"),
    timeout_seconds: int = 30,
    poll_number: int = 1,
    fetcher: Fetcher | None = None,
) -> dict[str, Any]:
    """Fetch one GTFS-Realtime snapshot and append it to immutable history partitions."""
    if feed_type not in FEED_TYPES:
        raise ValueError(f"Unsupported GTFS-Realtime feed type '{feed_type}'. Expected one of: {', '.join(sorted(FEED_TYPES))}")
    resolved_url = url or configured_realtime_url(source, feed_type)
    if not resolved_url:
        raise ValueError(
            f"No enabled GTFS-Realtime URL for feed type '{feed_type}'. " "Provide one with --url or enable it under realtime in config/sources.yml."
        )

    collection_dt = _utc_now()
    collection_time = collection_dt.isoformat()
    collection_date, collection_hour = _partition_parts(collection_dt)
    content, http_status, content_type = (fetcher or _default_fetcher)(resolved_url, timeout_seconds)
    if not content:
        raise ValueError("GTFS-Realtime snapshot is empty")
    snapshot_timestamp, checksum, header_timestamp = deterministic_snapshot_id(source_id, feed_type, content, collection_dt)
    parsed_dir = (
        parsed_history_root / source_id / feed_type / f"date={collection_date}" / f"hour={collection_hour}" / f"snapshot_timestamp={snapshot_timestamp}"
    )
    existing = _read_existing_metadata(parsed_dir)
    if existing is not None:
        if existing.get("sha256") == checksum and _commit_marker_valid(parsed_dir, feed_type):
            duplicate = dict(existing)
            duplicate["duplicate"] = True
            return duplicate
        raise FileExistsError(f"Conflicting historical snapshot already exists for snapshot id: {snapshot_timestamp}")

    tables, summary = _parse_feed(content, feed_type, collection_time)
    feed_age = summary.iloc[0].get("feed_age_seconds") if not summary.empty else None
    if pd.isna(feed_age):
        feed_age = None
    feed_age = int(feed_age) if feed_age is not None else None
    history_tables = {
        name: _add_history_metadata(
            frame,
            snapshot_timestamp=snapshot_timestamp,
            collection_time=collection_time,
            feed_age_seconds=feed_age,
            poll_number=poll_number,
            collection_date=collection_date,
            collection_hour=collection_hour,
            source_id=source_id,
            feed_type=feed_type,
            checksum=checksum,
            header_timestamp=header_timestamp,
        )
        for name, frame in tables.items()
    }
    summary = _add_history_metadata(
        summary,
        snapshot_timestamp=snapshot_timestamp,
        collection_time=collection_time,
        feed_age_seconds=feed_age,
        poll_number=poll_number,
        collection_date=collection_date,
        collection_hour=collection_hour,
        source_id=source_id,
        feed_type=feed_type,
        checksum=checksum,
        header_timestamp=header_timestamp,
    )

    metadata = {
        "source_id": source_id,
        "source_name": source.get("name"),
        "feed_type": feed_type,
        "url": resolved_url,
        "snapshot_timestamp": snapshot_timestamp,
        "collection_time": collection_time,
        "collection_date": collection_date,
        "collection_hour": collection_hour,
        "poll_number": poll_number,
        "snapshot_id": snapshot_timestamp,
        "feed_header_timestamp": header_timestamp,
        "feed_age_seconds": feed_age,
        "sha256": checksum,
        "file_size_bytes": len(content),
        "http_status": http_status,
        "content_type": content_type,
        "raw_path": str(raw_history_root / source_id / feed_type / f"date={collection_date}" / f"hour={collection_hour}" / snapshot_timestamp / "feed.pb"),
        "parsed_path": str(parsed_dir),
        "row_counts": {name: int(len(frame)) for name, frame in history_tables.items()},
        "trip_update_rows": int(len(history_tables.get("trip_updates", pd.DataFrame()))),
        "stop_time_update_rows": int(len(history_tables.get("stop_time_updates", pd.DataFrame()))),
        "vehicle_position_rows": int(len(history_tables.get("vehicle_positions", pd.DataFrame()))),
        "alert_rows": int(len(history_tables.get("alerts", pd.DataFrame()))),
    }

    raw_dir = Path(str(metadata["raw_path"])).parent
    raw_tmp_dir = raw_dir.parent / f".{raw_dir.name}.tmp"
    parsed_tmp_dir = parsed_dir.parent / f".{parsed_dir.name}.tmp"
    if parsed_dir.exists() or parsed_tmp_dir.exists() or raw_dir.exists() or raw_tmp_dir.exists():
        raise FileExistsError(f"Historical parsed snapshot already exists and will not be overwritten: {parsed_dir}")
    try:
        raw_tmp_dir.mkdir(parents=True, exist_ok=False)
        (raw_tmp_dir / "feed.pb").write_bytes(content)
        _write_json(raw_tmp_dir / "metadata.json", metadata)
        for name, frame in history_tables.items():
            _to_parquet(frame, parsed_tmp_dir / f"{name}.parquet")
        _to_parquet(summary, parsed_tmp_dir / "feed_summary.parquet")
        _write_json(parsed_tmp_dir / "metadata.json", metadata)
        (parsed_tmp_dir / "_SUCCESS").write_text("ok\n", encoding="utf-8")
        (raw_tmp_dir / "_SUCCESS").write_text("ok\n", encoding="utf-8")
        raw_tmp_dir.rename(raw_dir)
        parsed_tmp_dir.rename(parsed_dir)
    except Exception:
        shutil.rmtree(parsed_tmp_dir, ignore_errors=True)
        shutil.rmtree(raw_tmp_dir, ignore_errors=True)
        raise

    _append_jsonl(parsed_history_root / source_id / feed_type / "collection_log.jsonl", metadata)
    HISTORICAL_POLLS.labels(source=source_id, feed_type=feed_type).inc()
    rows_processed = sum(len(frame) for frame in history_tables.values())
    ROWS_PROCESSED.labels(pipeline="historical_realtime", task="collect_gtfs_rt").inc(int(rows_processed))
    if feed_age is not None:
        FEED_FRESHNESS.labels(source=source_id, feed_type=feed_type).set(feed_age)
    return metadata


def run_historical_collection(
    source_id: str,
    source: dict[str, Any],
    feed_type: str,
    *,
    interval_seconds: int = 30,
    url: str | None = None,
    raw_history_root: Path = Path("data/raw_realtime/historical"),
    parsed_history_root: Path = Path("data/realtime_history"),
    timeout_seconds: int = 30,
    max_polls: int | None = None,
    fetcher: Fetcher | None = None,
) -> list[dict[str, Any]]:
    """Run scheduled GTFS-Realtime polling until interrupted or max_polls is reached."""
    safe_interval = max(1, int(interval_seconds))
    results: list[dict[str, Any]] = []
    scheduler = BackgroundScheduler()
    stop_requested = Event()

    def job() -> None:
        poll_number = len(results) + 1
        metadata = collect_gtfs_rt_snapshot(
            source_id,
            source,
            feed_type,
            url=url,
            raw_history_root=raw_history_root,
            parsed_history_root=parsed_history_root,
            timeout_seconds=timeout_seconds,
            poll_number=poll_number,
            fetcher=fetcher,
        )
        results.append(metadata)
        logger.info(
            f"Collected poll {poll_number}: {metadata.get('row_counts', {})} rows, raw={metadata['raw_path']}, parsed={metadata['parsed_path']}",
        )
        if max_polls is not None and len(results) >= max_polls:
            stop_requested.set()

    scheduler.add_job(job, "interval", seconds=safe_interval, max_instances=1, coalesce=True, next_run_time=_utc_now())
    scheduler.start()
    try:
        while scheduler.running and not stop_requested.is_set():
            time.sleep(0.2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Historical GTFS-Realtime collection stopped.")
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    return results
