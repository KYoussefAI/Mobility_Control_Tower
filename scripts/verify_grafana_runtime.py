"""Verify Grafana provisioning through a running Grafana instance."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

EXPECTED_DASHBOARD_UID = "mct-operations"
EXPECTED_PANELS = {
    "Serving Ready",
    "Active Critical Incidents",
    "Active Incidents by Rule",
    "Incident Evaluation Candidates",
    "Incident Evaluation Transitions",
    "Last Incident Evaluation Success",
}


def _request(method: str, url: str, *, auth: tuple[str, str], **kwargs: Any) -> Any:
    response = requests.request(method, url, auth=auth, timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grafana-url", default=f"http://127.0.0.1:{os.getenv('GRAFANA_PORT', '3000')}")
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/grafana-report.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    auth = (os.getenv("GRAFANA_ADMIN_USER", "admin"), os.getenv("GRAFANA_ADMIN_PASSWORD", "admin"))

    health = _request("GET", f"{args.grafana_url}/api/health", auth=auth)
    datasources = _request("GET", f"{args.grafana_url}/api/datasources", auth=auth)
    prometheus = next((source for source in datasources if source.get("name") == "Prometheus"), None)
    datasource_ok = False
    datasource_health: dict[str, Any] | None = None
    query_result: dict[str, Any] | None = None
    if prometheus:
        datasource_health = _request("GET", f"{args.grafana_url}/api/datasources/uid/{prometheus['uid']}/health", auth=auth)
        datasource_ok = str(datasource_health.get("status", "")).lower() in {"ok", "success"}
        query_result = _request(
            "POST",
            f"{args.grafana_url}/api/ds/query",
            auth=auth,
            json={
                "queries": [
                    {
                        "refId": "A",
                        "datasource": {"type": "prometheus", "uid": prometheus["uid"]},
                        "expr": "up",
                        "instant": True,
                        "range": False,
                    }
                ],
                "from": "now-5m",
                "to": "now",
            },
        )
    dashboard = _request("GET", f"{args.grafana_url}/api/dashboards/uid/{EXPECTED_DASHBOARD_UID}", auth=auth)
    panels = {panel.get("title") for panel in dashboard.get("dashboard", {}).get("panels", [])}
    missing_panels = sorted(EXPECTED_PANELS - panels)
    status = (
        "ok"
        if health.get("database") == "ok"
        and prometheus
        and prometheus.get("url") == "http://prometheus:9090"
        and datasource_ok
        and not missing_panels
        and query_result
        and "results" in query_result
        else "failed"
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "prometheus_datasource": prometheus,
        "datasource_health": datasource_health,
        "dashboard_uid": EXPECTED_DASHBOARD_UID,
        "dashboard_title": dashboard.get("dashboard", {}).get("title"),
        "panel_titles": sorted(title for title in panels if title),
        "missing_panels": missing_panels,
        "sample_query_status": "ok" if query_result and "results" in query_result else "failed",
        "status": status,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": status}, sort_keys=True))
    if status != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
