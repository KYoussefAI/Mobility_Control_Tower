"""FastAPI application factory."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI

from mobility_control_tower.api.db import validate_database_path
from mobility_control_tower.api.routes import router
from mobility_control_tower.observability import API_REQUESTS


def create_app(db_path: str | Path | None = None, *, source: str = "tisseo", serving_root: str | Path = "data/serving") -> FastAPI:
    resolved = validate_database_path(db_path) if db_path is not None else None
    app = FastAPI(
        title="Mobility Control Tower API",
        description="Local read-only API serving DuckDB data products.",
        version="0.1.0",
    )

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)
        status_class = f"{response.status_code // 100}xx"
        API_REQUESTS.labels(method=request.method, path=endpoint, status=status_class).inc()
        response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"
        return response

    app.state.db_path = resolved
    app.state.source = source
    app.state.serving_root = Path(serving_root)
    app.include_router(router)
    app.include_router(router, prefix="/v1")
    return app
