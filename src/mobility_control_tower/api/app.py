"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from mobility_control_tower.api.db import validate_database_path
from mobility_control_tower.api.routes import router


def create_app(db_path: str | Path) -> FastAPI:
    resolved = validate_database_path(db_path)
    app = FastAPI(
        title="Mobility Control Tower API",
        description="Local read-only API serving DuckDB data products.",
        version="0.1.0",
    )
    app.state.db_path = resolved
    app.include_router(router)
    return app

