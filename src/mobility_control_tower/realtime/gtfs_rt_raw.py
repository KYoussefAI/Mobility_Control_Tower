"""Fetch and preserve one GTFS-Realtime protobuf snapshot."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

FEED_TYPES = {"trip_updates", "vehicle_positions", "service_alerts"}


def timestamp_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def configured_realtime_url(source: dict[str, Any], feed_type: str) -> str | None:
    realtime = source.get("realtime") or {}
    if feed_type in realtime:
        config = realtime[feed_type] or {}
        if not config.get("enabled", False):
            return None
        return config.get("url")
    feeds = source.get("gtfs_realtime") or {}
    return feeds.get(f"{feed_type}_url")


def _allowed_hosts(source: dict[str, Any]) -> set[str]:
    hosts: set[str] = set()
    static_url = (source.get("static_gtfs") or {}).get("url") or source.get("download_url")
    for value in [static_url, *((feed or {}).get("url") for feed in (source.get("realtime") or {}).values())]:
        if value:
            parsed = urlparse(value)
            if parsed.hostname:
                hosts.add(parsed.hostname)
    return hosts


def _validate_feed_response(response: requests.Response, *, max_bytes: int) -> None:
    size = len(response.content)
    if size > max_bytes:
        raise RuntimeError(f"GTFS-Realtime response exceeded configured size limit: {size} > {max_bytes} bytes")
    content_type = response.headers.get("content-type", "").lower()
    if content_type and not any(token in content_type for token in ("protobuf", "octet-stream", "x-protobuf")):
        raise RuntimeError(f"Unexpected GTFS-Realtime content-type: {content_type}")


def preserve_realtime_snapshot(
    content: bytes,
    source_id: str,
    source: dict[str, Any],
    feed_type: str,
    url: str,
    raw_root: Path = Path("data/raw_realtime"),
    http_status: int | None = None,
    content_type: str | None = None,
) -> Path:
    if feed_type not in FEED_TYPES:
        raise ValueError(f"Unsupported GTFS-Realtime feed type '{feed_type}'. Expected one of: {', '.join(sorted(FEED_TYPES))}")
    if not content:
        raise ValueError("GTFS-Realtime snapshot is empty")
    run_dir = raw_root / source_id / feed_type / timestamp_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    feed_path = run_dir / "feed.pb"
    feed_path.write_bytes(content)
    metadata = {
        "source_id": source_id,
        "source_name": source.get("name"),
        "source_page_url": source.get("source_page_url"),
        "feed_type": feed_type,
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size_bytes": len(content),
        "http_status": http_status,
        "content_type": content_type,
        "snapshot_note": "Saved feed.pb is an immutable local GTFS-Realtime snapshot for replay, demos, parser tests, and compatibility checks.",
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return run_dir


def fetch_realtime_snapshot(
    source_id: str,
    source: dict[str, Any],
    feed_type: str,
    url: str | None = None,
    raw_root: Path = Path("data/raw_realtime"),
    timeout_seconds: int = 30,
    max_response_bytes: int = 15_000_000,
) -> Path:
    resolved_url = url or configured_realtime_url(source, feed_type)
    if not resolved_url:
        raise ValueError(
            f"No configured GTFS-Realtime URL for feed type '{feed_type}'. " "Provide one with --url or add it under gtfs_realtime in config/sources.yml."
        )
    allowed = _allowed_hosts(source)
    host = urlparse(resolved_url).hostname
    if allowed and host not in allowed:
        raise RuntimeError(f"GTFS-Realtime host is not allowed for this source: {host}")
    try:
        response = requests.get(resolved_url, timeout=timeout_seconds, allow_redirects=False)
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch GTFS-Realtime snapshot from {resolved_url}: {exc}") from exc
    if 300 <= response.status_code < 400:
        raise RuntimeError(f"GTFS-Realtime redirects are disabled for safety: HTTP {response.status_code}")
    if response.status_code >= 400:
        raise RuntimeError(f"GTFS-Realtime request failed with HTTP {response.status_code} for {resolved_url}")
    _validate_feed_response(response, max_bytes=max_response_bytes)
    return preserve_realtime_snapshot(
        response.content,
        source_id,
        source,
        feed_type,
        resolved_url,
        raw_root,
        http_status=response.status_code,
        content_type=response.headers.get("content-type"),
    )
