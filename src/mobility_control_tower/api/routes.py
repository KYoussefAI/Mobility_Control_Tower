"""FastAPI routes for serving DuckDB data products."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException, Query, Request
from starlette.responses import JSONResponse, Response

from mobility_control_tower.api.db import database_connected, list_tables_and_views, query_view, view_exists
from mobility_control_tower.config import load_sources
from mobility_control_tower.core.exceptions import not_found
from mobility_control_tower.incidents import IncidentEvaluationEngine, IncidentStore, evaluation_result_to_dict, incident_backend
from mobility_control_tower.observability import metrics_response
from mobility_control_tower.security import AuthenticationError, verify_access_token
from mobility_control_tower.serving.duckdb_loader import resolve_current_database, validate_serving_database

router = APIRouter()
JSON_BODY = Body(default_factory=dict)


def _db_path(request: Request) -> Path:
    explicit = getattr(request.app.state, "db_path", None)
    if explicit is not None:
        return explicit
    return resolve_current_database(request.app.state.source, request.app.state.serving_root)


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


def _safe_metadata(request: Request) -> dict[str, Any]:
    try:
        pointer = getattr(request.app.state, "source", "tisseo")
        return {"source": pointer}
    except Exception:
        return {}


def _operator(authorization: str | None, scopes: set[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        return verify_access_token(authorization.split(" ", 1)[1], scopes).subject
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="authentication required") from None


def _require_scope(authorization: str | None, scopes: set[str]) -> str:
    return _operator(authorization, scopes)


def _readiness_payload(request: Request) -> tuple[dict[str, Any], int]:
    try:
        db_path = _db_path(request)
        validation = validate_serving_database(db_path)
        required_views = {"v_network_overview"}
        if os.getenv("MCT_STRICT_READINESS") == "true":
            required_views.add("v_reliability_incident_snapshot")
        _, views = list_tables_and_views(db_path)
        missing_views = sorted(required_views - set(views))
        if missing_views:
            return (
                {
                    "status": "not_ready",
                    "service": "Mobility Control Tower API",
                    "reason": "required serving views are unavailable",
                    "missing_views": missing_views,
                    "source": getattr(request.app.state, "source", None),
                },
                503,
            )
        incident_store = IncidentStore()
        incident_schema_version = incident_store.repository.schema_version()
    except Exception as exc:
        reason = exc.__class__.__name__
        if isinstance(exc, (RuntimeError, ValueError)):
            reason = str(exc).splitlines()[0][:160]
        return (
            {
                "status": "not_ready",
                "service": "Mobility Control Tower API",
                "reason": reason,
                "source": getattr(request.app.state, "source", None),
            },
            503,
        )
    return {
        "status": "ready",
        "service": "Mobility Control Tower API",
        "database_connected": database_connected(db_path),
        "artifact": "current",
        "validation": validation,
        "incident_repository": {
            "backend": incident_backend(),
            "schema_version": incident_schema_version,
            "reachable": True,
        },
    }, 200


@router.get("/health/live", tags=["system"], summary="Service liveness")
def health_live() -> dict[str, Any]:
    return {"status": "live", "service": "Mobility Control Tower API"}


@router.get("/health/ready", tags=["system"], summary="Service readiness")
def health_ready(request: Request) -> Response:
    payload, status_code = _readiness_payload(request)
    return JSONResponse(payload, status_code=status_code)


@router.get("/health", tags=["system"], summary="Service health")
def health(request: Request) -> Any:
    payload, status_code = _readiness_payload(request)
    if status_code == 200:
        payload["status"] = "ok"
        return payload
    return JSONResponse(payload, status_code=status_code)


@router.get("/metadata", tags=["system"], summary="Available tables and views")
def metadata(request: Request) -> dict[str, Any]:
    db_path = _db_path(request)
    tables, views = list_tables_and_views(db_path)
    return {
        "available_tables": tables,
        "available_views": views,
        "static_data_available": "v_network_overview" in views and "v_top_routes_static" in views,
        "realtime_snapshot_available": any(view.startswith("v_rt_") for view in views),
        "historical_realtime_available": any(view.endswith("_history") or view == "v_collection_summary" for view in views),
    }


@router.get("/sources", tags=["system"], summary="Configured source capabilities")
def sources() -> dict[str, Any]:
    rows = []
    for source_id, source in load_sources(Path("config/sources.yml")).items():
        rows.append(
            {
                "source": source_id,
                "name": source["name"],
                "city": source["city"],
                "country": source["country"],
                "timezone": source["timezone"],
                "language": source["language"],
                "static_gtfs_enabled": source["static_gtfs"]["enabled"],
                "realtime": {feed_type: {"enabled": feed["enabled"], "available": bool(feed.get("url"))} for feed_type, feed in source["realtime"].items()},
                "expected_freshness": source["expected_freshness"],
            }
        )
    return {"data": rows, "count": len(rows), "source": "config/sources.yml", "notes": []}


@router.get("/network/status", tags=["operations"], summary="Current network status")
def network_status(request: Request, source: str = "tisseo") -> dict[str, Any]:
    db_path = _db_path(request)
    if not view_exists(db_path, "v_network_reliability_summary"):
        return {"data": [], "count": 0, "source": source, "metadata": _safe_metadata(request), "notes": ["dbt reliability mart unavailable"]}
    data = query_view(db_path, "v_network_reliability_summary", 20, {"source": source})
    return {"data": data, "count": len(data), "source": source, "metadata": _safe_metadata(request)}


@router.get("/network/reliability", tags=["operations"], summary="Network reliability indicators")
def network_reliability(request: Request, source: str = "tisseo", limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    return network_status(request, source=source) if limit else network_status(request, source=source)


@router.get("/routes", tags=["operations"], summary="Routes")
def routes(request: Request, source: str = "tisseo", limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    return _query_or_404(_db_path(request), "v_top_routes_static", _limit(limit, 500))


@router.get("/routes/{route_id}/reliability", tags=["operations"], summary="Route reliability")
def route_reliability(request: Request, route_id: str, source: str = "tisseo", limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    db_path = _db_path(request)
    return _query_or_404(db_path, "v_route_reliability", _limit(limit, 200), {"source": source, "route_id": route_id})


@router.get("/routes/{route_id}/headways", tags=["operations"], summary="Route observed headways")
def route_headways(request: Request, route_id: str, source: str = "tisseo", limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    db_path = _db_path(request)
    return _query_or_404(db_path, "v_headway_reliability", _limit(limit, 200), {"source": source, "route_id": route_id})


@router.get("/vehicles", tags=["operations"], summary="Latest vehicles")
def vehicles(request: Request, source: str = "tisseo", route_id: str | None = None, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    db_path = _db_path(request)
    if not view_exists(db_path, "v_latest_vehicle_positions"):
        return {"data": [], "count": 0, "source": source, "notes": ["vehicle_positions unavailable for current artifact"]}
    return _response(
        query_view(db_path, "v_latest_vehicle_positions", _limit(limit, 500), {"source": source, "route_id": route_id}), "v_latest_vehicle_positions"
    )


@router.get("/alerts/active", tags=["operations"], summary="Active service alerts")
def active_alerts(request: Request, source: str = "tisseo", limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    db_path = _db_path(request)
    if not view_exists(db_path, "v_active_service_alerts"):
        return {"data": [], "count": 0, "source": source, "notes": ["service_alerts unavailable for current artifact"]}
    return _response(query_view(db_path, "v_active_service_alerts", _limit(limit, 500), {"source": source}), "v_active_service_alerts")


@router.get("/incidents", tags=["operations"], summary="Operational incidents")
def incidents(source: str | None = None, status: str | None = None, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    rows = IncidentStore().list_incidents(status=status, source=source, limit=limit)
    return {"data": rows, "count": len(rows), "source": source or "all", "notes": []}


@router.get("/v1/incidents", tags=["operations"], summary="List operational incidents")
def v1_incidents(
    authorization: str | None = Header(default=None),
    source: str | None = None,
    status: str | None = None,
    rule: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    _require_scope(authorization, {"operations:read"})
    rows = IncidentStore().list_incidents(status=status, source=source, rule_id=rule, severity=severity, limit=limit, offset=offset)
    return {"data": rows, "count": len(rows), "source": source or "all", "notes": []}


@router.get("/v1/incidents/evaluations", tags=["operations"], summary="List incident evaluation runs")
def v1_incident_evaluations(
    authorization: str | None = Header(default=None),
    source: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    _require_scope(authorization, {"operations:read"})
    rows = IncidentStore().list_evaluation_runs(source=source, limit=limit)
    return {"data": rows, "count": len(rows), "source": source or "all", "notes": []}


@router.post("/v1/incidents/evaluate", tags=["operations"], summary="Trigger incident evaluation")
def v1_evaluate_incidents(
    authorization: str | None = Header(default=None),
    source: str | None = None,
    dry_run: bool = False,
    correlation_id: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_scope(authorization, {"admin"})
    result = IncidentEvaluationEngine().evaluate(source=source, correlation_id=correlation_id, dry_run=dry_run)
    return {"data": [evaluation_result_to_dict(result)], "count": 1, "source": source or "all", "notes": ["dry-run"] if dry_run else []}


@router.get("/v1/incidents/{incident_id}", tags=["operations"], summary="Get one operational incident")
def v1_incident(incident_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_scope(authorization, {"operations:read"})
    row = IncidentStore().get_by_id(incident_id)
    if row is None:
        raise not_found("Incident is not available.")
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.get("/v1/incidents/{incident_id}/events", tags=["operations"], summary="Get incident event history")
def v1_incident_events(
    incident_id: str,
    authorization: str | None = Header(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    _require_scope(authorization, {"operations:read"})
    rows = IncidentStore().list_events(incident_id, limit=limit)
    return {"data": rows, "count": len(rows), "source": "incident_events", "notes": []}


@router.post("/incidents/{incident_id}/acknowledge", tags=["operations"], summary="Acknowledge incident")
def acknowledge_incident(incident_id: str, authorization: str | None = Header(default=None), note: str | None = None) -> dict[str, Any]:
    operator = _operator(authorization, {"incidents:write"})
    row = IncidentStore().transition(incident_id, status="ACKNOWLEDGED", operator=operator, note=note)
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.post("/incidents/{incident_id}/resolve", tags=["operations"], summary="Resolve incident")
def resolve_incident(incident_id: str, authorization: str | None = Header(default=None), note: str | None = None) -> dict[str, Any]:
    operator = _operator(authorization, {"incidents:write"})
    row = IncidentStore().transition(incident_id, status="RESOLVED", operator=operator, note=note)
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.post("/v1/incidents/{incident_id}/acknowledge", tags=["operations"], summary="Acknowledge incident")
def v1_acknowledge_incident(
    incident_id: str,
    authorization: str | None = Header(default=None),
    payload: dict[str, Any] = JSON_BODY,
) -> dict[str, Any]:
    operator = _operator(authorization, {"incidents:write"})
    row = IncidentStore().transition(incident_id, status="ACKNOWLEDGED", operator=operator, note=payload.get("reason"))
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.post("/v1/incidents/{incident_id}/resolve", tags=["operations"], summary="Resolve incident")
def v1_resolve_incident(
    incident_id: str,
    authorization: str | None = Header(default=None),
    payload: dict[str, Any] = JSON_BODY,
) -> dict[str, Any]:
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="resolution reason is required")
    operator = _operator(authorization, {"incidents:write"})
    row = IncidentStore().transition(incident_id, status="RESOLVED", operator=operator, note=reason)
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.post("/v1/incidents/{incident_id}/suppress", tags=["operations"], summary="Suppress incident")
def v1_suppress_incident(
    incident_id: str,
    authorization: str | None = Header(default=None),
    payload: dict[str, Any] = JSON_BODY,
) -> dict[str, Any]:
    reason = str(payload.get("reason") or "").strip()
    expires_at = str(payload.get("expires_at") or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="suppression reason is required")
    if not expires_at:
        raise HTTPException(status_code=422, detail="suppression expiry is required")
    operator = _operator(authorization, {"incidents:write"})
    try:
        row = IncidentStore().transition(incident_id, status="SUPPRESSED", operator=operator, note=reason, suppress_until=expires_at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.post("/v1/incidents/{incident_id}/unsuppress", tags=["operations"], summary="Unsuppress incident")
def v1_unsuppress_incident(
    incident_id: str,
    authorization: str | None = Header(default=None),
    payload: dict[str, Any] = JSON_BODY,
) -> dict[str, Any]:
    operator = _operator(authorization, {"incidents:write"})
    row = IncidentStore().transition(incident_id, status="OPEN", operator=operator, note=payload.get("reason"))
    return {"data": [row], "count": 1, "source": "incidents", "notes": []}


@router.get("/data-quality/status", tags=["quality"], summary="Data quality status")
def data_quality_status() -> dict[str, Any]:
    return quality_summary()


@router.get("/lineage/status", tags=["lineage"], summary="Lineage availability")
def lineage_status() -> dict[str, Any]:
    enabled = (
        bool(json.loads(Path("data/lineage/status.json").read_text(encoding="utf-8")).get("enabled")) if Path("data/lineage/status.json").is_file() else False
    )
    return {"data": [{"enabled": enabled, "backend": "local_file" if enabled else None}], "count": 1, "source": "lineage", "notes": []}


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
