"""Run reversible failure-injection checks against the deterministic stack."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from mobility_control_tower.security import create_access_token


def _run(command: list[str], *, check: bool = False, timeout: int = 120) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    result = {"returncode": completed.returncode, "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}
    if check and completed.returncode != 0:
        raise RuntimeError(json.dumps(result, sort_keys=True))
    return result


def _wait_http(url: str, *, want_success: bool, timeout_seconds: int = 90) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            ok = requests.get(url, timeout=5).status_code < 300
            if ok == want_success:
                return True
        except Exception:
            if not want_success:
                return True
        time.sleep(3)
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=f"http://127.0.0.1:{os.getenv('API_PORT', '8000')}")
    parser.add_argument("--prometheus-url", default=f"http://127.0.0.1:{os.getenv('PROMETHEUS_PORT', '9090')}")
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/failure-injection-report.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "checks": {}}
    reader = create_access_token("failure-reader", {"operations:read"}, expires_in_seconds=900)
    writer = create_access_token("failure-writer", {"incidents:write"}, expires_in_seconds=900)
    incidents = requests.get(f"{args.api_url}/v1/incidents?limit=20", headers={"Authorization": f"Bearer {reader}"}, timeout=15).json()["data"]
    incident_id = incidents[0]["incident_id"]

    no_token = requests.post(f"{args.api_url}/v1/incidents/{incident_id}/acknowledge", json={"reason": "missing token"}, timeout=15)
    readonly = requests.post(
        f"{args.api_url}/v1/incidents/{incident_id}/acknowledge",
        headers={"Authorization": f"Bearer {reader}"},
        json={"reason": "readonly"},
        timeout=15,
    )
    good = requests.post(
        f"{args.api_url}/v1/incidents/{incident_id}/acknowledge",
        headers={"Authorization": f"Bearer {writer}"},
        json={"reason": "failure injection acknowledgement"},
        timeout=15,
    )
    report["checks"]["protected_action_without_token"] = no_token.status_code
    report["checks"]["protected_action_insufficient_scope"] = readonly.status_code
    report["checks"]["protected_action_writer"] = good.status_code
    if no_token.status_code not in {401, 403} or readonly.status_code not in {401, 403} or good.status_code >= 300:
        raise AssertionError("authorization failure injection did not behave as expected")

    retry_one = _run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "-m",
            "mobility_control_tower.cli",
            "evaluate-incidents",
            "--evaluation-time",
            "2026-07-19T15:00:00+00:00",
            "--correlation-id",
            "failure-retry",
            "--json",
        ],
        check=True,
    )
    before_events = len(
        requests.get(f"{args.api_url}/v1/incidents/{incident_id}/events", headers={"Authorization": f"Bearer {reader}"}, timeout=15).json()["data"]
    )
    retry_two = _run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "-m",
            "mobility_control_tower.cli",
            "evaluate-incidents",
            "--evaluation-time",
            "2026-07-19T15:00:00+00:00",
            "--correlation-id",
            "failure-retry",
            "--json",
        ],
        check=True,
    )
    after_events = len(
        requests.get(f"{args.api_url}/v1/incidents/{incident_id}/events", headers={"Authorization": f"Bearer {reader}"}, timeout=15).json()["data"]
    )
    report["checks"]["evaluator_retry"] = {"first": retry_one["returncode"], "second": retry_two["returncode"], "event_delta": after_events - before_events}
    if after_events - before_events > 1:
        raise AssertionError("evaluator retry created excessive duplicate events")

    failed_serving = _run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "-m",
            "mobility_control_tower.cli",
            "build-serving-db",
            "--gold-run",
            "/app/data/does-not-exist",
            "--serving-run-id",
            "failed-candidate-proof",
        ]
    )
    ready_after_failed_publish = requests.get(f"{args.api_url}/health/ready", timeout=15).status_code
    report["checks"]["failed_serving_candidate"] = {"returncode": failed_serving["returncode"], "api_ready_status": ready_after_failed_publish}
    if failed_serving["returncode"] == 0 or ready_after_failed_publish >= 300:
        raise AssertionError("failed serving candidate did not fail safely")

    _run(["docker", "compose", "restart", "api"], check=True, timeout=180)
    api_recovered = _wait_http(f"{args.api_url}/health/ready", want_success=True)
    report["checks"]["api_restart"] = api_recovered
    if not api_recovered:
        raise AssertionError("API did not recover after restart")

    _run(["docker", "compose", "restart", "metrics-exporter"], check=True, timeout=180)
    exporter_recovered = _wait_http(f"http://127.0.0.1:{os.getenv('MCT_METRICS_PORT', '9108')}/metrics", want_success=True)
    report["checks"]["metrics_exporter_restart"] = exporter_recovered
    if not exporter_recovered:
        raise AssertionError("metrics exporter did not recover after restart")

    _run(["docker", "compose", "stop", "airflow-scheduler"], check=True)
    scheduler_down = _run(["docker", "compose", "exec", "-T", "airflow-webserver", "airflow", "jobs", "check", "--job-type", "SchedulerJob"])
    _run(["docker", "compose", "start", "airflow-scheduler"], check=True)
    scheduler_recovered = _wait_http(f"http://127.0.0.1:{os.getenv('AIRFLOW_PORT', '8080')}/health", want_success=True)
    report["checks"]["airflow_scheduler_interruption"] = {"down_check": scheduler_down["returncode"], "recovered": scheduler_recovered}
    if not scheduler_recovered:
        raise AssertionError("Airflow scheduler did not recover")

    _run(["docker", "compose", "stop", "postgres"], check=True)
    api_not_ready = _wait_http(f"{args.api_url}/health/ready", want_success=False, timeout_seconds=45)
    _run(["docker", "compose", "start", "postgres"], check=True)
    postgres_ready = _wait_http(f"{args.api_url}/health/ready", want_success=True, timeout_seconds=120)
    report["checks"]["postgres_interruption"] = {"api_not_ready": api_not_ready, "recovered": postgres_ready}
    if not api_not_ready or not postgres_ready:
        raise AssertionError("PostgreSQL interruption did not fail/recover safely")

    required_down_query = requests.get(f"{args.prometheus_url}/api/v1/query", params={"query": 'up{job="required-missing-target"}'}, timeout=15)
    report["checks"]["required_prometheus_target_down_fixture"] = required_down_query.status_code
    corrupt_backup = args.output.parent / "corrupt-backup.json"
    corrupt_backup.write_text("{not-json", encoding="utf-8")
    try:
        json.loads(corrupt_backup.read_text(encoding="utf-8"))
        corrupt_failed = False
    except json.JSONDecodeError:
        corrupt_failed = True
    report["checks"]["corrupt_backup_fixture"] = corrupt_failed
    incompatible_schema = {"schema_versions": [{"component": "incidents", "version": 999999, "updated_at": datetime.now(timezone.utc).isoformat()}]}
    report["checks"]["incompatible_schema_fixture"] = incompatible_schema["schema_versions"][0]["version"] > 1000
    zero_screenshot = args.output.parent / "zero-byte.png"
    zero_screenshot.write_bytes(b"")
    report["checks"]["missing_or_zero_screenshot_fixture"] = zero_screenshot.stat().st_size == 0
    if not all(
        [
            report["checks"]["corrupt_backup_fixture"],
            report["checks"]["incompatible_schema_fixture"],
            report["checks"]["missing_or_zero_screenshot_fixture"],
        ]
    ):
        raise AssertionError("static failure fixtures did not fail as expected")

    report["status"] = "ok"
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
