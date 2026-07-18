"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path
import time

from fastapi import FastAPI
from starlette.responses import Response

from mobility_control_tower.api.db import validate_database_path
from mobility_control_tower.api.routes import router
from mobility_control_tower.observability import API_REQUESTS


def create_app(db_path: str | Path) -> FastAPI:
    resolved = validate_database_path(db_path)
    app = FastAPI(
        title="Mobility Control Tower API",
        description="Local read-only API serving DuckDB data products.",
        version="0.1.0",
    )

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        API_REQUESTS.labels(method=request.method, path=request.url.path, status=str(response.status_code)).inc()
        response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"
        return response

    app.state.db_path = resolved
    app.include_router(router)
    app.include_router(router, prefix="/v1")
    return app
