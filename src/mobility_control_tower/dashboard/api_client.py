"""Client for API features available to this dashboard."""

from typing import Any

import requests

ENDPOINTS = {
    "health": "/v1/health",
    "metadata": "/v1/metadata",
    "network_overview": "/v1/static/network-overview",
    "top_routes": "/v1/static/top-routes",
    "hourly_headway": "/v1/static/hourly-headway",
    "route_types": "/v1/static/route-types",
    "rt_feed_health": "/v1/realtime/feed-health",
    "rt_compatibility": "/v1/realtime/compatibility",
    "rt_routes": "/v1/realtime/top-delayed-routes",
    "rt_stops": "/v1/realtime/top-delayed-stops",
}


def get_json(api_url: str, endpoint: str, params: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    try:
        response = requests.get(api_url.rstrip("/") + endpoint, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"data": payload}
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "error": str(exc), "data": [], "count": 0}


def fetch_dashboard_data(api_url: str, token: str | None = None) -> dict[str, dict[str, Any]]:
    return {name: get_json(api_url, endpoint, token=token) for name, endpoint in ENDPOINTS.items()}
