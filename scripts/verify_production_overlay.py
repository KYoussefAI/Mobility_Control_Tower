"""Validate rendered production Compose configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

INTERNAL_SERVICES = {"postgres", "airflow-webserver", "airflow-scheduler", "prometheus", "metrics-exporter"}
PUBLIC_SERVICES = {"reverse-proxy"}
RESTART_REQUIRED = {"api", "dashboard", "postgres", "airflow-webserver", "airflow-scheduler", "prometheus", "grafana", "reverse-proxy"}


def _ports(service: dict[str, Any]) -> list[Any]:
    return service.get("ports") or []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/production-overlay-report.json"))
    args = parser.parse_args()
    config = json.loads(args.compose_json.read_text(encoding="utf-8"))
    services: dict[str, dict[str, Any]] = config.get("services", {})
    failures: list[str] = []
    for name in sorted(INTERNAL_SERVICES):
        if _ports(services.get(name, {})):
            failures.append(f"{name} exposes host ports")
    if not _ports(services.get("reverse-proxy", {})):
        failures.append("reverse-proxy does not expose public ports")
    api_env = services.get("api", {}).get("environment", {})
    if api_env.get("MCT_ENV") != "production":
        failures.append("api does not set MCT_ENV=production")
    if api_env.get("MCT_INCIDENT_BACKEND") == "sqlite":
        failures.append("production api uses sqlite incident backend")
    auth_secret = api_env.get("MCT_AUTH_SECRET")
    if "MCT_AUTH_SECRET" not in api_env and not any(str(value).startswith("${MCT_AUTH_SECRET:?") for value in api_env.values()):
        failures.append("production api does not require MCT_AUTH_SECRET")
    if auth_secret in {"local-demo-change-me", "local-demo-secret-change-me", "local-demo-secret-key"}:
        failures.append("production api uses a demo auth secret")
    if "demo-bootstrap" in services and "production" in services["demo-bootstrap"].get("profiles", []):
        failures.append("demo-bootstrap is active in production profile")
    for name in sorted(RESTART_REQUIRED):
        if services.get(name, {}).get("restart") not in {"unless-stopped", "always", "on-failure"}:
            failures.append(f"{name} lacks a production restart policy")
    volumes = set(config.get("volumes", {}))
    for volume in ("postgres-data", "mct-data", "prometheus-data", "grafana-data"):
        if volume not in volumes:
            failures.append(f"missing persistent volume {volume}")
    report = {"status": "ok" if not failures else "failed", "failures": failures, "checked_services": sorted(services)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
