"""Typed runtime settings with environment overrides."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    duckdb_path: Path | None = None
    serving_root: Path = Path("data/serving")
    history_path: Path = Path("data/realtime_history")
    watermark_root: Path = Path("data/watermarks")
    api_version: str = "v1"
    log_level: str = "INFO"
    profile: str = "local"
    collection_interval_seconds: int = 60
    refresh_interval_seconds: int = 600
    incremental_lookback_count: int = 1
    feed_age_warning_seconds: int = 600
    feed_age_critical_seconds: int = 1800
    serving_max_age_seconds: int = 86400
    allow_raw_history_delete: bool = False
    airflow_db_user: str | None = None
    airflow_db_password: str | None = None
    airflow_db_name: str | None = None
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
            "serving_root": "MCT_SERVING_ROOT",
            "history_path": "MCT_HISTORY_PATH",
            "watermark_root": "MCT_WATERMARK_ROOT",
            "api_version": "MCT_API_VERSION",
            "log_level": "MCT_LOG_LEVEL",
            "profile": "MCT_PROFILE",
            "collection_interval_seconds": "MCT_COLLECTION_INTERVAL_SECONDS",
            "refresh_interval_seconds": "MCT_REFRESH_INTERVAL_SECONDS",
            "incremental_lookback_count": "MCT_INCREMENTAL_LOOKBACK_COUNT",
            "feed_age_warning_seconds": "MCT_FEED_AGE_WARNING_SECONDS",
            "feed_age_critical_seconds": "MCT_FEED_AGE_CRITICAL_SECONDS",
            "serving_max_age_seconds": "MCT_SERVING_MAX_AGE_SECONDS",
            "allow_raw_history_delete": "MCT_ALLOW_RAW_HISTORY_DELETE",
            "airflow_db_user": "AIRFLOW_DB_USER",
            "airflow_db_password": "AIRFLOW_DB_PASSWORD",
            "airflow_db_name": "AIRFLOW_DB_NAME",
            "benchmark_output_dir": "MCT_BENCHMARK_OUTPUT_DIR",
        }
        for field, env_name in env_map.items():
            if field not in data and os.getenv(env_name) not in (None, ""):
                data[field] = os.environ[env_name]
        super().__init__(**data)

    @model_validator(mode="after")
    def validate_operational_settings(self) -> AppSettings:
        if self.refresh_interval_seconds < self.collection_interval_seconds:
            raise ValueError("MCT_REFRESH_INTERVAL_SECONDS must be greater than or equal to MCT_COLLECTION_INTERVAL_SECONDS")
        if self.incremental_lookback_count < 0:
            raise ValueError("MCT_INCREMENTAL_LOOKBACK_COUNT must be non-negative")
        if self.feed_age_warning_seconds >= self.feed_age_critical_seconds:
            raise ValueError("MCT_FEED_AGE_WARNING_SECONDS must be lower than MCT_FEED_AGE_CRITICAL_SECONDS")
        if any(part.startswith(".") and "tmp" in part for part in self.serving_root.parts):
            raise ValueError("MCT_SERVING_ROOT must not point inside a temporary publication directory")
        if self.profile not in {"local", "demo"} and self.airflow_db_password in {"admin", "mct_airflow_demo", "local-demo-secret-key"}:
            raise ValueError("Production-style profiles must not use local-demo Airflow/PostgreSQL credentials")
        if self.allow_raw_history_delete:
            raise ValueError("Phase 2 does not allow automatic deletion of immutable raw realtime history")
        return self


def get_settings() -> AppSettings:
    return AppSettings()
