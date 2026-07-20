"""Verify Prometheus runtime targets and rule groups from the HTTP API."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REQUIRED_TARGETS = {"prometheus", "mct-api", "mct-exporter"}
REQUIRED_ALERTS = {
    "CriticalMobilityIncidentsPresent",
    "IncidentEvaluatorStale",
    "IncidentEvaluationFailures",
    "MCTServingArtifactNotReady",
    "RequiredPrometheusTargetDown",
}


def _get(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus API returned {payload.get('status')}")
    return payload["data"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prometheus-url", default=f"http://127.0.0.1:{os.getenv('PROMETHEUS_PORT', '9090')}")
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/prometheus-targets.json"))
    parser.add_argument("--rules-output", type=Path, default=Path("artifacts/runtime/prometheus-rules.json"))
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    targets = _get(f"{args.prometheus_url}/api/v1/targets")
    active_targets = targets.get("activeTargets", [])
    by_job: dict[str, list[dict[str, Any]]] = {}
    for target in active_targets:
        by_job.setdefault(target.get("labels", {}).get("job", ""), []).append(target)
    missing = sorted(REQUIRED_TARGETS - set(by_job))
    down = sorted({job for job, entries in by_job.items() if job in REQUIRED_TARGETS and not any(entry.get("health") == "up" for entry in entries)})
    target_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required_targets": sorted(REQUIRED_TARGETS),
        "missing_targets": missing,
        "down_targets": down,
        "targets": active_targets,
        "status": "ok" if not missing and not down else "failed",
    }
    args.output.write_text(json.dumps(target_report, indent=2, sort_keys=True), encoding="utf-8")

    groups = _get(f"{args.prometheus_url}/api/v1/rules").get("groups", [])
    alerts = {rule.get("name") for group in groups for rule in group.get("rules", []) if rule.get("type") == "alerting"}
    missing_alerts = sorted(REQUIRED_ALERTS - alerts)
    rules_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "required_alerts": sorted(REQUIRED_ALERTS),
        "missing_alerts": missing_alerts,
        "groups": groups,
        "status": "ok" if not missing_alerts else "failed",
    }
    args.rules_output.write_text(json.dumps(rules_report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"targets": target_report["status"], "rules": rules_report["status"]}, sort_keys=True))
    if target_report["status"] != "ok" or rules_report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
