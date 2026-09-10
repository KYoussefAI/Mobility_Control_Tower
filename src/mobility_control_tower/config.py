"""Load the single Tisséo source and its realtime capabilities."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config/sources.yml")
FEED_TYPES = ("trip_updates", "vehicle_positions", "service_alerts")


def _load_tisseo(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Source configuration not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    sources = document.get("sources", {}) or {}
    if set(sources) != {"tisseo"}:
        raise ValueError("This project version supports only the 'tisseo' source")
    source = dict(sources["tisseo"])
    static = source.get("static_gtfs") or {}
    source["download_url"] = static.get("url")
    for feed_type in FEED_TYPES:
        feed = (source.get("realtime") or {}).get(feed_type) or {}
        if feed.get("enabled") and not feed.get("url"):
            raise ValueError(f"Enabled Tisséo realtime feed is missing URL: {feed_type}")
    return source


def load_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, dict[str, Any]]:
    return {"tisseo": _load_tisseo(config_path)}


def load_source(source_id: str, config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if source_id != "tisseo":
        raise ValueError("This project version supports only the 'tisseo' source")
    return _load_tisseo(config_path)
