"""Project-wide logging configuration."""

import logging
import os

LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def configure_logging(level: str | None = None) -> None:
    resolved = (level or os.getenv("MCT_LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(level=getattr(logging, resolved, logging.INFO), format=LOG_FORMAT, force=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
