"""FastAPI routes for serving DuckDB data products."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from mobility_control_tower.api.db import database_connected, list_tables_and_views, query_view, view_exists


router = APIRouter()


def _db_path(request: Request) -> Path:
    return request.app.state.db_path


def _limit(value: int, maximum: int) -> int:
    return max(1, min(value, maximum))


def _response(data: list[dict[str, Any]], source: str, notes: list[str] | None = None) -> dict[str, Any]:
    return {"data": data, "count": len(data), "source": source, "notes": notes or []}


def _query_or_404(db_path: Path, view_name: str, limit: int, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    if not view_exists(db_path, view_name):
        if view_name.startswith("v_rt_"):
            raise HTTPException(status_code=404, detail="Realtime snapshot data is not available in this serving database.")
        raise HTTPException(status_code=404, detail=f"Required view '{view_name}' is not available in this serving database.")
    return _response(query_view(db_path, view_name, limit, filters), view_name)


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    db_path = _db_path(request)
    return {
        "status": "ok",
        "service": "Mobility Control Tower API",
        "database_connected": database_connected(db_path),
    }


@router.get("/metadata")
def metadata(request: Request) -> dict[str, Any]:
    db_path = _db_path(request)
    tables, views = list_tables_and_views(db_path)
    return {
        "database_path": str(db_path),
        "available_tables": tables,
        "available_views": views,
        "static_data_available": "v_network_overview" in views and "v_top_routes_static" in views,
        "realtime_snapshot_available": any(view.startswith("v_rt_") for view in views),
    }


@router.get("/static/network-overview")
def static_network_overview(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_network_overview", _limit(limit, 100))


@router.get("/static/top-routes")
def static_top_routes(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_top_routes_static", _limit(limit, 100))


@router.get("/static/hourly-headway")
def static_hourly_headway(
    request: Request,
    route_id: str | None = None,
    service_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_route_hourly_headway", _limit(limit, 500), {"route_id": route_id, "service_date": service_date})


@router.get("/static/route-types")
def static_route_types(
    request: Request,
    service_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_route_type_daily_summary", _limit(limit, 500), {"service_date": service_date})


@router.get("/realtime/feed-health")
def realtime_feed_health(request: Request) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_feed_health", 10)


@router.get("/realtime/compatibility")
def realtime_compatibility(request: Request) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_identifier_compatibility", 10)


@router.get("/realtime/top-delayed-routes")
def realtime_top_delayed_routes(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_top_delayed_routes_snapshot", _limit(limit, 100))


@router.get("/realtime/top-delayed-stops")
def realtime_top_delayed_stops(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_top_delayed_stops_snapshot", _limit(limit, 100))

