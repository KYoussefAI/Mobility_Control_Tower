"""Small client for the local Mobility Control Tower API."""

from __future__ import annotations

from typing import Any

import requests


ENDPOINTS = {
    "health": "/health",
    "metadata": "/metadata",
    "network_overview": "/static/network-overview",
    "top_routes": "/static/top-routes",
    "hourly_headway": "/static/hourly-headway",
    "route_types": "/static/route-types",
    "rt_feed_health": "/realtime/feed-health",
    "rt_compatibility": "/realtime/compatibility",
    "rt_top_delayed_routes": "/realtime/top-delayed-routes",
    "rt_top_delayed_stops": "/realtime/top-delayed-stops",
    "history_routes": "/history/routes",
    "history_stops": "/history/stops",
    "history_feed_health": "/history/feed-health",
    "history_delay_trend": "/history/delay-trend",
    "history_summary": "/history/summary",
    "quality_summary": "/quality/summary",
}


def _url(api_url: str, endpoint: str) -> str:
    return api_url.rstrip("/") + endpoint


def get_json(api_url: str, endpoint: str, params: dict[str, Any] | None = None, timeout: int = 5) -> dict[str, Any]:
    """Call one API endpoint and return either JSON data or a friendly error payload."""
    try:
        response = requests.get(_url(api_url, endpoint), params=params, timeout=timeout)
    except requests.RequestException as exc:
        return {
            "ok": False,
            "error": f"API is not reachable at {api_url}. Start it with `python -m mobility_control_tower.cli serve-api ...`. Details: {exc}",
            "data": [],
            "count": 0,
        }
    if response.status_code == 404:
        try:
            detail = response.json().get("detail", "Endpoint unavailable.")
        except ValueError:
            detail = "Endpoint unavailable."
        return {"ok": False, "error": detail, "data": [], "count": 0}
    if response.status_code >= 400:
        return {"ok": False, "error": f"API returned HTTP {response.status_code}.", "data": [], "count": 0}
    try:
        payload = response.json()
    except ValueError:
        return {"ok": False, "error": "API returned a non-JSON response.", "data": [], "count": 0}
    if isinstance(payload, dict):
        payload.setdefault("ok", True)
        return payload
    return {"ok": True, "data": payload, "count": len(payload) if isinstance(payload, list) else 1}


def fetch_dashboard_data(api_url: str) -> dict[str, dict[str, Any]]:
    """Fetch the small set of payloads used by the dashboard."""
    return {
        "health": get_json(api_url, ENDPOINTS["health"]),
        "metadata": get_json(api_url, ENDPOINTS["metadata"]),
        "network_overview": get_json(api_url, ENDPOINTS["network_overview"], {"limit": 20}),
        "top_routes": get_json(api_url, ENDPOINTS["top_routes"], {"limit": 10}),
        "hourly_headway": get_json(api_url, ENDPOINTS["hourly_headway"], {"limit": 50}),
        "route_types": get_json(api_url, ENDPOINTS["route_types"], {"limit": 50}),
        "rt_feed_health": get_json(api_url, ENDPOINTS["rt_feed_health"]),
        "rt_compatibility": get_json(api_url, ENDPOINTS["rt_compatibility"]),
        "rt_top_delayed_routes": get_json(api_url, ENDPOINTS["rt_top_delayed_routes"], {"limit": 10}),
        "rt_top_delayed_stops": get_json(api_url, ENDPOINTS["rt_top_delayed_stops"], {"limit": 10}),
        "history_routes": get_json(api_url, ENDPOINTS["history_routes"], {"limit": 20}),
        "history_stops": get_json(api_url, ENDPOINTS["history_stops"], {"limit": 20}),
        "history_feed_health": get_json(api_url, ENDPOINTS["history_feed_health"], {"limit": 100}),
        "history_delay_trend": get_json(api_url, ENDPOINTS["history_delay_trend"], {"limit": 100}),
        "history_summary": get_json(api_url, ENDPOINTS["history_summary"], {"limit": 100}),
        "quality_summary": get_json(api_url, ENDPOINTS["quality_summary"]),
    }
