"""Load and validate source capability definitions from YAML configuration."""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

DEFAULT_CONFIG_PATH = Path("config/sources.yml")
FEED_TYPES = ("trip_updates", "vehicle_positions", "service_alerts")
DEFAULT_FRESHNESS_SECONDS = {
    "trip_updates": 90,
    "vehicle_positions": 90,
    "service_alerts": 600,
}


def _legacy_realtime(source: dict[str, Any]) -> dict[str, Any]:
    feeds = source.get("gtfs_realtime") or {}
    return {feed_type: {"enabled": bool(feeds.get(f"{feed_type}_url")), "url": feeds.get(f"{feed_type}_url")} for feed_type in FEED_TYPES}


def _validate_url(value: str | None, *, required: bool, label: str) -> str | None:
    if not value:
        if required:
            raise ValueError(f"Enabled capability is missing URL: {label}")
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"Invalid URL for {label}: {value}")
    return value


def normalize_source(source_id: str, source: dict[str, Any]) -> dict[str, Any]:
    realtime = source.get("realtime") or _legacy_realtime(source)
    static = source.get("static_gtfs") or {"enabled": True, "url": source.get("download_url")}
    freshness = source.get("expected_freshness") or {}
    normalized = dict(source)
    normalized["source_id"] = source_id
    normalized["city"] = normalized.get("city") or source_id
    normalized["country"] = normalized.get("country") or ""
    normalized["timezone"] = normalized.get("timezone") or "UTC"
    normalized["language"] = normalized.get("language") or "en"
    normalized["static_gtfs"] = {
        "enabled": bool(static.get("enabled", True)),
        "url": _validate_url(static.get("url"), required=bool(static.get("enabled", True)), label=f"{source_id}.static_gtfs"),
    }
    normalized["download_url"] = normalized["static_gtfs"]["url"]
    normalized["realtime"] = {}
    normalized["gtfs_realtime"] = {}
    for feed_type in FEED_TYPES:
        config = realtime.get(feed_type) or {}
        enabled = bool(config.get("enabled", bool(config.get("url"))))
        url = _validate_url(config.get("url"), required=enabled, label=f"{source_id}.realtime.{feed_type}")
        normalized["realtime"][feed_type] = {"enabled": enabled, "url": url}
        normalized["gtfs_realtime"][f"{feed_type}_url"] = url if enabled else None
    normalized["expected_freshness"] = {
        f"{feed_type}_seconds": int(freshness.get(f"{feed_type}_seconds", DEFAULT_FRESHNESS_SECONDS[feed_type])) for feed_type in FEED_TYPES
    }
    return normalized


def load_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, dict[str, Any]]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Source configuration not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    return {source_id: normalize_source(source_id, source) for source_id, source in (document.get("sources", {}) or {}).items()}


def load_source(source_id: str, config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    sources = load_sources(config_path)
    if source_id not in sources:
        available = ", ".join(sorted(sources)) or "none"
        raise ValueError(f"Unknown source '{source_id}'. Available sources: {available}")
    return dict(sources[source_id])
