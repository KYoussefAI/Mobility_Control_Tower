"""FastAPI routes for serving DuckDB data products."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request
from starlette.responses import Response

from mobility_control_tower.api.db import database_connected, list_tables_and_views, query_view, view_exists
from mobility_control_tower.core.exceptions import not_found
from mobility_control_tower.observability import metrics_response


router = APIRouter()


def _db_path(request: Request) -> Path:
    return request.app.state.db_path


def _limit(value: int, maximum: int) -> int:
    return max(1, min(value, maximum))


def _response(data: list[dict[str, Any]], source: str, notes: list[str] | None = None) -> dict[str, Any]:
    return {"data": data, "count": len(data), "source": source, "notes": notes or []}


def _query_or_404(db_path: Path, view_name: str, limit: int, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    if not view_exists(db_path, view_name):
        if view_name.startswith("v_") and "_history" in view_name:
            raise not_found("Historical realtime data is not available in this serving database.")
        if view_name.startswith("v_rt_"):
            raise not_found("Realtime snapshot data is not available in this serving database.")
        raise not_found(f"Required view '{view_name}' is not available in this serving database.")
    return _response(query_view(db_path, view_name, limit, filters), view_name)


@router.get("/health", tags=["system"], summary="Service health")
def health(request: Request) -> dict[str, Any]:
    db_path = _db_path(request)
    return {
        "status": "ok",
        "service": "Mobility Control Tower API",
        "database_connected": database_connected(db_path),
    }


@router.get("/metadata", tags=["system"], summary="Available tables and views")
def metadata(request: Request) -> dict[str, Any]:
    db_path = _db_path(request)
    tables, views = list_tables_and_views(db_path)
    return {
        "database_path": str(db_path),
        "available_tables": tables,
        "available_views": views,
        "static_data_available": "v_network_overview" in views and "v_top_routes_static" in views,
        "realtime_snapshot_available": any(view.startswith("v_rt_") for view in views),
        "historical_realtime_available": any(view.endswith("_history") or view == "v_collection_summary" for view in views),
    }


@router.get("/static/network-overview", tags=["static"], summary="Static network overview")
def static_network_overview(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_network_overview", _limit(limit, 100))


@router.get("/static/top-routes", tags=["static"], summary="Top scheduled routes")
def static_top_routes(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_top_routes_static", _limit(limit, 100))


@router.get("/static/hourly-headway", tags=["static"], summary="Route hourly planned headway")
def static_hourly_headway(
    request: Request,
    route_id: str | None = None,
    service_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_route_hourly_headway", _limit(limit, 500), {"route_id": route_id, "service_date": service_date})


@router.get("/static/route-types", tags=["static"], summary="Daily summary by GTFS route type")
def static_route_types(
    request: Request,
    service_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_route_type_daily_summary", _limit(limit, 500), {"service_date": service_date})


@router.get("/realtime/feed-health", tags=["realtime"], summary="Realtime snapshot feed health")
def realtime_feed_health(request: Request) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_feed_health", 10)


@router.get("/realtime/compatibility", tags=["realtime"], summary="Static and realtime identifier compatibility")
def realtime_compatibility(request: Request) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_identifier_compatibility", 10)


@router.get("/realtime/top-delayed-routes", tags=["realtime"], summary="Top delayed routes in realtime snapshot")
def realtime_top_delayed_routes(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_top_delayed_routes_snapshot", _limit(limit, 100))


@router.get("/realtime/top-delayed-stops", tags=["realtime"], summary="Top delayed stops in realtime snapshot")
def realtime_top_delayed_stops(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_rt_top_delayed_stops_snapshot", _limit(limit, 100))


@router.get("/history/routes", tags=["history"], summary="Historical route delay analytics")
def history_routes(request: Request, limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_route_delay_history", _limit(limit, 200))


@router.get("/history/stops", tags=["history"], summary="Historical stop delay analytics")
def history_stops(request: Request, limit: int = Query(default=20, ge=1, le=200)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_stop_delay_history", _limit(limit, 200))


@router.get("/history/feed-health", tags=["history"], summary="Historical feed freshness")
def history_feed_health(request: Request, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_feed_health_history", _limit(limit, 1000))


@router.get("/history/delay-trend", tags=["history"], summary="Historical delay trend")
def history_delay_trend(request: Request, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_collection_summary", _limit(limit, 1000))


@router.get("/history/summary", tags=["history"], summary="Historical collection summary")
def history_summary(request: Request, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_collection_summary", _limit(limit, 1000))


@router.get("/quality/summary", tags=["quality"], summary="Latest data quality summary")
def quality_summary() -> dict[str, Any]:
    path = Path("data/quality/latest_validation_summary.json")
    if not path.is_file():
        raise not_found("Data quality validation summary is not available.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"data": [payload], "count": 1, "source": str(path), "notes": []}


@router.get("/pipeline/metrics", tags=["observability"], summary="Prometheus metrics")
def pipeline_metrics() -> Response:
    content, media_type = metrics_response()
    return Response(content=content, media_type=media_type)
