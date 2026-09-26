"""Source and runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    timezone: str
    licence: str
    source_page: str
    gtfs_url: str
    trip_updates_url: str
    expected_realtime_freshness_seconds: int
    stale_realtime_after_seconds: int


def load_source(path: Path | None = None) -> SourceConfig:
    config_path = path or PROJECT_ROOT / "config" / "source.yml"
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))["source"]
    return SourceConfig(**raw)


def data_root() -> Path:
    return Path(os.environ.get("MCT_DATA_ROOT", PROJECT_ROOT / "data")).resolve()


def db_path(root: Path | None = None) -> Path:
    default = (root or data_root()) / "mart" / "mobility_control_tower.duckdb"
    return Path(os.environ.get("MCT_DBT_DATABASE_PATH", default)).resolve()


def latest_run(parent: Path) -> Path:
    runs = sorted(path for path in parent.glob("*") if path.is_dir() and (path / "manifest.json").is_file())
    if not runs:
        raise FileNotFoundError(f"No completed run found under {parent}")
    return runs[-1]
