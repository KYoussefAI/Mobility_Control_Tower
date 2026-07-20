"""Durable analytical watermarks with a small filesystem lock."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def watermark_path(root: Path, source: str, feed_type: str, workflow: str) -> Path:
    return root / source / feed_type / f"{workflow}.json"


def read_watermark(root: Path, source: str, feed_type: str, workflow: str) -> dict[str, Any]:
    path = watermark_path(root, source, feed_type, workflow)
    if not path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "source": source,
            "feed_type": feed_type,
            "workflow": workflow,
            "latest_successfully_processed_snapshot": None,
            "latest_collection_time": None,
            "latest_feed_timestamp": None,
            "latest_serving_run": None,
            "updated_timestamp": None,
            "status": "never_run",
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported watermark schema in {path}")
    return payload


def write_watermark(root: Path, payload: dict[str, Any]) -> Path:
    required = ("source", "feed_type", "workflow")
    missing = [name for name in required if not payload.get(name)]
    if missing:
        raise ValueError(f"Watermark payload is missing required fields: {', '.join(missing)}")
    path = watermark_path(root, payload["source"], payload["feed_type"], payload["workflow"])
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(payload)
    record["schema_version"] = SCHEMA_VERSION
    record["updated_timestamp"] = _utc_now()
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


@contextmanager
def watermark_lock(root: Path, source: str, feed_type: str, workflow: str) -> Iterator[Path]:
    path = watermark_path(root, source, feed_type, workflow)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Watermark is locked by another refresh: {lock_path}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(_utc_now() + "\n")
        yield lock_path
    finally:
        lock_path.unlink(missing_ok=True)


def select_snapshots_after_watermark(snapshots: list[dict[str, Any]], watermark: dict[str, Any], lookback_count: int = 0) -> list[dict[str, Any]]:
    latest = watermark.get("latest_successfully_processed_snapshot")
    if latest is None:
        return snapshots
    positions = [index for index, snapshot in enumerate(snapshots) if snapshot.get("snapshot_id") == latest or snapshot.get("snapshot_timestamp") == latest]
    if not positions:
        return snapshots[-lookback_count:] if lookback_count > 0 else snapshots
    start = max(0, positions[-1] + 1 - max(0, lookback_count))
    return snapshots[start:]


def advance_watermark_after_publish(
    root: Path,
    *,
    source: str,
    feed_type: str,
    workflow: str,
    snapshot: dict[str, Any] | None,
    serving_run_id: str | None,
    status: str = "success",
) -> Path:
    payload = read_watermark(root, source, feed_type, workflow)
    payload.update(
        {
            "latest_successfully_processed_snapshot": snapshot.get("snapshot_id") if snapshot else payload.get("latest_successfully_processed_snapshot"),
            "latest_collection_time": snapshot.get("collection_time") if snapshot else payload.get("latest_collection_time"),
            "latest_feed_timestamp": snapshot.get("feed_header_timestamp") if snapshot else payload.get("latest_feed_timestamp"),
            "latest_serving_run": serving_run_id or payload.get("latest_serving_run"),
            "status": status,
        }
    )
    return write_watermark(root, payload)
