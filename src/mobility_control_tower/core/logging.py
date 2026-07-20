"""Project-wide logging configuration."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
CONTEXT_FIELDS = (
    "event",
    "source",
    "feed_type",
    "dag_id",
    "task_id",
    "airflow_run_id",
    "pipeline_run_id",
    "static_run_id",
    "dbt_run_id",
    "serving_run_id",
    "snapshot_id",
    "duration_seconds",
    "rows_processed",
    "status",
    "correlation_id",
)


class JsonFormatter(logging.Formatter):
    """Format operational logs as compact JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None) -> None:
    """Configure standard application logging once."""
    resolved = (level or os.getenv("MCT_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    if (os.getenv("MCT_LOG_FORMAT") or "").lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.basicConfig(level=getattr(logging, resolved, logging.INFO), handlers=[handler], force=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, message: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured operational event without requiring callers to build LogRecord extras."""
    extra = {"event": event, **{key: value for key, value in fields.items() if key in CONTEXT_FIELDS and value is not None}}
    logger.log(level, message, extra=extra)
