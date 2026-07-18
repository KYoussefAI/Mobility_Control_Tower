"""Historical GTFS-Realtime polling and Parquet archive helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any, Callable

import pandas as pd
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.realtime.gtfs_rt_parser import _feed_age_seconds, _summary, _trip_updates
from mobility_control_tower.realtime.gtfs_rt_raw import FEED_TYPES, configured_realtime_url
from mobility_control_tower.observability import FEED_FRESHNESS, HISTORICAL_POLLS, ROWS_PROCESSED


Fetcher = Callable[[str, int], tuple[bytes, int | None, str | None]]
logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot_id(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H-%M-%S.%fZ")


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


def _add_history_metadata(
    frame: pd.DataFrame,
    *,
    snapshot_timestamp: str,
    collection_time: str,
    feed_age_seconds: int | None,
    poll_number: int,
    collection_date: str,
    collection_hour: str,
) -> pd.DataFrame:
    result = frame.copy()
    result["snapshot_timestamp"] = snapshot_timestamp
    result["collection_time"] = collection_time
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


def _parse_trip_updates(content: bytes, fetched_at: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(content)
    except Exception as exc:
        raise ValueError(f"Unable to parse GTFS-Realtime protobuf snapshot: {exc}") from exc
    trips, stops, parsed, skipped = _trip_updates(feed)
    summary = _summary(feed, "trip_updates", fetched_at, parsed, skipped)
    return trips, stops, summary


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
    if feed_type != "trip_updates":
        raise ValueError("Historical collection currently supports trip_updates feeds")
    resolved_url = url or configured_realtime_url(source, feed_type)
    if not resolved_url:
        raise ValueError(
            f"No configured GTFS-Realtime URL for feed type '{feed_type}'. "
            "Provide one with --url or add it under gtfs_realtime in config/sources.yml."
        )

    collection_dt = _utc_now()
    collection_time = collection_dt.isoformat()
    collection_date, collection_hour = _partition_parts(collection_dt)
    snapshot_timestamp = _snapshot_id(collection_dt)
    content, http_status, content_type = (fetcher or _default_fetcher)(resolved_url, timeout_seconds)
    if not content:
        raise ValueError("GTFS-Realtime snapshot is empty")

    raw_dir = raw_history_root / source_id / feed_type / f"date={collection_date}" / f"hour={collection_hour}" / snapshot_timestamp
    raw_dir.mkdir(parents=True, exist_ok=False)
    raw_path = raw_dir / "feed.pb"
    raw_path.write_bytes(content)

    trips, stops, summary = _parse_trip_updates(content, collection_time)
    feed_age = summary.iloc[0].get("feed_age_seconds") if not summary.empty else None
    if pd.isna(feed_age):
        feed_age = None
    feed_age = int(feed_age) if feed_age is not None else None
    trips = _add_history_metadata(
        trips,
        snapshot_timestamp=snapshot_timestamp,
        collection_time=collection_time,
        feed_age_seconds=feed_age,
        poll_number=poll_number,
        collection_date=collection_date,
        collection_hour=collection_hour,
    )
    stops = _add_history_metadata(
        stops,
        snapshot_timestamp=snapshot_timestamp,
        collection_time=collection_time,
        feed_age_seconds=feed_age,
        poll_number=poll_number,
        collection_date=collection_date,
        collection_hour=collection_hour,
    )
    summary = _add_history_metadata(
        summary,
        snapshot_timestamp=snapshot_timestamp,
        collection_time=collection_time,
        feed_age_seconds=feed_age,
        poll_number=poll_number,
        collection_date=collection_date,
        collection_hour=collection_hour,
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
        "feed_age_seconds": feed_age,
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size_bytes": len(content),
        "http_status": http_status,
        "content_type": content_type,
        "raw_path": str(raw_path),
        "parsed_path": str(parsed_history_root / source_id / feed_type / f"date={collection_date}" / f"hour={collection_hour}" / f"snapshot_timestamp={snapshot_timestamp}"),
        "trip_update_rows": int(len(trips)),
        "stop_time_update_rows": int(len(stops)),
    }
    _write_json(raw_dir / "metadata.json", metadata)

    parsed_dir = Path(metadata["parsed_path"])
    parsed_tmp_dir = parsed_dir.parent / f".{parsed_dir.name}.tmp"
    if parsed_dir.exists() or parsed_tmp_dir.exists():
        raise FileExistsError(f"Historical parsed snapshot already exists and will not be overwritten: {parsed_dir}")
    try:
        _to_parquet(trips, parsed_tmp_dir / "trip_updates.parquet")
        _to_parquet(stops, parsed_tmp_dir / "stop_time_updates.parquet")
        _to_parquet(summary, parsed_tmp_dir / "feed_summary.parquet")
        _write_json(parsed_tmp_dir / "metadata.json", metadata)
        parsed_tmp_dir.rename(parsed_dir)
    except Exception:
        shutil.rmtree(parsed_tmp_dir, ignore_errors=True)
        raise

    _write_json(parsed_dir / "metadata.json", metadata)
    _append_jsonl(parsed_history_root / source_id / feed_type / "collection_log.jsonl", metadata)
    HISTORICAL_POLLS.labels(source=source_id, feed_type=feed_type).inc()
    ROWS_PROCESSED.labels(pipeline="historical_realtime", task="collect_gtfs_rt").inc(int(len(stops)))
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
            f"Collected poll {poll_number}: {metadata['stop_time_update_rows']} stop updates, "
            f"raw={metadata['raw_path']}, parsed={metadata['parsed_path']}",
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
