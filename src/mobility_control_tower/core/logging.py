"""Project-wide logging configuration."""

from __future__ import annotations

import logging
import os
import sys


LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def configure_logging(level: str | None = None) -> None:
    """Configure standard application logging once."""
    resolved = (level or os.getenv("MCT_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(level=getattr(logging, resolved, logging.INFO), format=LOG_FORMAT, stream=sys.stdout, force=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

