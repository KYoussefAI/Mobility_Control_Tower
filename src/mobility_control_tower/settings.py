"""Typed runtime settings with environment overrides."""

from __future__ import annotations

from pathlib import Path
import os

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:  # pragma: no cover - compatibility fallback for minimal local envs
    from pydantic import BaseModel as BaseSettings

    SettingsConfigDict = dict


class AppSettings(BaseSettings):
    """Runtime settings shared by CLI, API, orchestration, and storage helpers."""

    model_config = SettingsConfigDict(env_prefix="MCT_", env_file=".env", extra="ignore")

    gtfs_source: str = "tisseo"
    config_path: Path = Path("config/sources.yml")
    storage_backend: str = "local"
    storage_root: str = "data"
    s3_bucket: str | None = None
    s3_prefix: str = ""
    aws_region: str = "eu-west-3"
    duckdb_path: Path = Path("data/serving/tisseo/2026-07-17_160355/mobility_control_tower.duckdb")
    history_path: Path = Path("data/realtime_history")
    api_version: str = "v1"
    log_level: str = "INFO"
    benchmark_output_dir: Path = Path("data/benchmarks")

    def __init__(self, **data):
        env_map = {
            "gtfs_source": "MCT_GTFS_SOURCE",
            "config_path": "MCT_CONFIG_PATH",
            "storage_backend": "MCT_STORAGE_BACKEND",
            "storage_root": "MCT_STORAGE_ROOT",
            "s3_bucket": "MCT_S3_BUCKET",
            "s3_prefix": "MCT_S3_PREFIX",
            "aws_region": "MCT_AWS_REGION",
            "duckdb_path": "MCT_DUCKDB_PATH",
            "history_path": "MCT_HISTORY_PATH",
            "api_version": "MCT_API_VERSION",
            "log_level": "MCT_LOG_LEVEL",
            "benchmark_output_dir": "MCT_BENCHMARK_OUTPUT_DIR",
        }
        for field, env_name in env_map.items():
            if field not in data and os.getenv(env_name) not in (None, ""):
                data[field] = os.environ[env_name]
        super().__init__(**data)


def get_settings() -> AppSettings:
    return AppSettings()
