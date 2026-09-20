"""Typed local runtime settings with environment overrides."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCT_", env_file=".env", extra="ignore")

    gtfs_source: str = "tisseo"
    config_path: Path = Path("config/sources.yml")
    storage_root: Path = Path("data")
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
    operator_rate_limit: int = 10
    operator_rate_window_seconds: int = 60


def get_settings() -> AppSettings:
    return AppSettings()
