"""Load source definitions from YAML configuration."""

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path("config/sources.yml")


def load_source(source_id: str, config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Source configuration not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    sources = document.get("sources", {})
    if source_id not in sources:
        available = ", ".join(sorted(sources)) or "none"
        raise ValueError(f"Unknown source '{source_id}'. Available sources: {available}")
    return dict(sources[source_id])
