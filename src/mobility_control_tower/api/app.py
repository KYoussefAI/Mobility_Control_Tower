"""FastAPI application factory."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from mobility_control_tower.api.db import validate_database_path
from mobility_control_tower.api.rate_limit import FixedWindowRateLimiter
from mobility_control_tower.api.routes import router
from mobility_control_tower.observability import API_REQUESTS


def _read_compatibility_router() -> APIRouter:
    """Expose legacy reads without duplicating canonical mutation routes."""
    compatibility = APIRouter()
    for route in router.routes:
        if isinstance(route, APIRoute) and route.methods == {"GET"}:
            compatibility.add_api_route(
                route.path,
                route.endpoint,
                methods=["GET"],
                include_in_schema=False,
                deprecated=True,
            )
    return compatibility


def create_app(
    db_path: str | Path | None = None,
    *,
    source: str = "tisseo",
    serving_root: str | Path = "data/serving",
    rate_limiter: FixedWindowRateLimiter | None = None,
) -> FastAPI:
    resolved = validate_database_path(db_path) if db_path is not None else None
    app = FastAPI(
        title="Mobility Control Tower API",
        description="Local API for bounded analytical reads and scoped incident operations.",
        version="1.0.0",
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
    app.state.operator_rate_limiter = rate_limiter or FixedWindowRateLimiter.from_environment()
    app.include_router(router, prefix="/v1")
    app.include_router(_read_compatibility_router())
    return app
