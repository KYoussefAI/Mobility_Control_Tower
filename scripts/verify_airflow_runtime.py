"""Collect Airflow runtime proof from the running Compose stack."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_DAGS = {"daily_static_pipeline", "daily_platform_maintenance", "realtime_snapshot_collection", "realtime_incremental_refresh"}


def _run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    return {"returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/airflow-report.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    version = _run(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "version"])
    scheduler = _run(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "jobs", "check", "--job-type", "SchedulerJob"])
    dag_list = _run(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "dags", "list", "--output", "json"])
    import_errors = _run(["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", "dags", "list-import-errors", "--output", "json"])
    parsed = json.loads(dag_list["stdout"]) if dag_list["returncode"] == 0 and dag_list["stdout"] else []
    parsed_ids = {row.get("dag_id") for row in parsed}
    missing = sorted(EXPECTED_DAGS - parsed_ids)
    errors = json.loads(import_errors["stdout"]) if import_errors["returncode"] == 0 and import_errors["stdout"] else []
    refresh_order = _run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "airflow-scheduler",
            "python",
            "-c",
            "from airflow.models.dagbag import DagBag; d=DagBag('/app/airflow/dags').get_dag('realtime_incremental_refresh'); print(d.task_dict['evaluate_reliability_incidents'].upstream_task_ids)",
        ]
    )
    status = "ok" if scheduler["returncode"] == 0 and not missing and not errors and "publish_serving_refresh" in refresh_order["stdout"] else "failed"
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "airflow_version": version["stdout"],
        "scheduler_health": scheduler,
        "dag_list": parsed,
        "missing_dags": missing,
        "import_errors": errors,
        "realtime_incremental_refresh_order": refresh_order,
        "status": status,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": status}, sort_keys=True))
    if status != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
