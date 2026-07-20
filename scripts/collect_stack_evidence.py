"""Collect runtime health evidence from a running deterministic Compose stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def _run(command: list[str], *, check: bool = False) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {' '.join(command)}")
    return {"returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def _get_json(url: str, *, timeout: float = 10.0, auth: tuple[str, str] | None = None) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout, auth=auth)
    response.raise_for_status()
    return response.json()


def _get_text(url: str, *, timeout: float = 10.0) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _compose_services() -> list[dict[str, Any]]:
    result = _run(["docker", "compose", "--profile", "demo", "ps", "--format", "json"])
    if result["returncode"] != 0:
        return [{"error": result["stderr"] or result["stdout"]}]
    services: list[dict[str, Any]] = []
    for line in result["stdout"].splitlines():
        if line.strip():
            services.append(json.loads(line))
    return services


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/health-report.json"))
    parser.add_argument("--api-url", default=f"http://127.0.0.1:{os.getenv('API_PORT', '8000')}")
    parser.add_argument("--airflow-url", default=f"http://127.0.0.1:{os.getenv('AIRFLOW_PORT', '8080')}")
    parser.add_argument("--prometheus-url", default=f"http://127.0.0.1:{os.getenv('PROMETHEUS_PORT', '9090')}")
    parser.add_argument("--grafana-url", default=f"http://127.0.0.1:{os.getenv('GRAFANA_PORT', '3000')}")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    grafana_auth = (os.getenv("GRAFANA_ADMIN_USER", "admin"), os.getenv("GRAFANA_ADMIN_PASSWORD", "admin"))
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _run(["git", "rev-parse", "HEAD"])["stdout"],
        "docker_version": _run(["docker", "version", "--format", "{{.Server.Version}}"])["stdout"],
        "compose_version": _run(["docker", "compose", "version", "--short"])["stdout"],
        "compose_project": os.getenv("COMPOSE_PROJECT_NAME", "mobility-control-tower"),
        "services": _compose_services(),
        "overall_status": "unknown",
    }
    checks: dict[str, Any] = {}
    try:
        checks["api_liveness"] = _get_json(f"{args.api_url}/health/live")
        checks["api_readiness"] = _get_json(f"{args.api_url}/health/ready")
        checks["incident_backend"] = checks["api_readiness"].get("incident_repository", {}).get("backend")
    except Exception as exc:
        checks["api_error"] = exc.__class__.__name__
    try:
        checks["airflow_web_health"] = _get_json(f"{args.airflow_url}/health")
    except Exception as exc:
        checks["airflow_web_error"] = exc.__class__.__name__
    scheduler = _run(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "jobs", "check", "--job-type", "SchedulerJob"])
    checks["airflow_scheduler_health"] = {"returncode": scheduler["returncode"], "stderr": scheduler["stderr"][-1000:]}
    dag_list = _run(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "dags", "list", "--output", "json"])
    checks["airflow_dags"] = json.loads(dag_list["stdout"]) if dag_list["returncode"] == 0 and dag_list["stdout"] else []
    try:
        checks["prometheus_ready"] = _get_text(f"{args.prometheus_url}/-/ready")
        checks["prometheus_targets"] = _get_json(f"{args.prometheus_url}/api/v1/targets").get("data", {})
        checks["prometheus_rules"] = _get_json(f"{args.prometheus_url}/api/v1/rules").get("data", {})
    except Exception as exc:
        checks["prometheus_error"] = exc.__class__.__name__
    try:
        checks["grafana_health"] = _get_json(f"{args.grafana_url}/api/health", auth=grafana_auth)
        checks["grafana_datasources"] = _get_json(f"{args.grafana_url}/api/datasources", auth=grafana_auth)
        checks["grafana_dashboard"] = _get_json(f"{args.grafana_url}/api/dashboards/uid/mct-operations", auth=grafana_auth)
    except Exception as exc:
        checks["grafana_error"] = exc.__class__.__name__
    report["checks"] = checks
    report["overall_status"] = "ok" if checks.get("incident_backend") == "postgres" and checks.get("api_readiness", {}).get("status") == "ready" else "failed"
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": _sha256(args.output), "status": report["overall_status"]}, sort_keys=True))
    if report["overall_status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
