"""FastAPI application factory for the available analytical routes."""

from pathlib import Path

from fastapi import FastAPI

from mobility_control_tower.api.db import validate_database_path
from mobility_control_tower.api.routes import router


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Mobility Control Tower API", version="0.1.0")
    app.state.db_path = validate_database_path(db_path) if db_path is not None else None
    app.include_router(router, prefix="/v1")
    return app
