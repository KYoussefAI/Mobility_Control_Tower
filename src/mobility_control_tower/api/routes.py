"""FastAPI routes for the available analytical features."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from mobility_control_tower.api.db import database_connected, list_tables_and_views, query_view, view_exists

router = APIRouter()


def _db_path(request: Request) -> Path:
    path = getattr(request.app.state, "db_path", None)
    if path is None:
        raise HTTPException(status_code=503, detail="No serving database is configured")
    return path


def _query(request: Request, view: str, limit: int = 100, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    path = _db_path(request)
    if not view_exists(path, view):
        raise HTTPException(status_code=404, detail=f"Required view '{view}' is unavailable")
    rows = query_view(path, view, max(1, min(limit, 500)), filters)
    return {"data": rows, "count": len(rows), "source": view, "notes": []}


@router.get("/health", tags=["system"])
def health(request: Request) -> dict[str, Any]:
    path = _db_path(request)
    return {"status": "ok" if database_connected(path) else "not_ready", "service": "Mobility Control Tower API"}


@router.get("/metadata", tags=["system"])
def metadata(request: Request) -> dict[str, Any]:
    tables, views = list_tables_and_views(_db_path(request))
    return {"available_tables": tables, "available_views": views, "static_data_available": "v_network_overview" in views}


@router.get("/static/network-overview", tags=["static"])
def static_network_overview(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    return _query(request, "v_network_overview", limit)


@router.get("/static/top-routes", tags=["static"])
def static_top_routes(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query(request, "v_top_routes_static", limit)


@router.get("/static/hourly-headway", tags=["static"])
def static_hourly_headway(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    return _query(request, "v_route_hourly_headway", limit)


@router.get("/static/route-types", tags=["static"])
def static_route_types(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    return _query(request, "v_route_type_daily_summary", limit)
