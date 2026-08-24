"""Load the initial static GTFS source configuration."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config/sources.yml")


def load_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, dict[str, Any]]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Source configuration not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    return dict(document.get("sources", {}) or {})


def load_source(source_id: str, config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    sources = load_sources(config_path)
    if source_id not in sources:
        available = ", ".join(sorted(sources)) or "none"
        raise ValueError(f"Unknown source '{source_id}'. Available sources: {available}")
    return dict(sources[source_id])
