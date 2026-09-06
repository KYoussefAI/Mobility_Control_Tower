"""Shared exception helpers for consistent user-facing failures."""

from __future__ import annotations

from fastapi import HTTPException


class MobilityControlTowerError(RuntimeError):
    """Base project exception for operational failures."""


def cli_failure_message(exc: Exception) -> str:
    return f"Error: {exc}"


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)
