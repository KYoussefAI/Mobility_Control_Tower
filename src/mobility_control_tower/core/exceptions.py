"""Shared project exception helpers."""


class MobilityControlTowerError(RuntimeError):
    """Base project exception for operational failures."""


def cli_failure_message(exc: Exception) -> str:
    return f"Error: {exc}"
