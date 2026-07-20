"""Daily platform maintenance and full-history checks."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from airflow.operators.python import PythonOperator
from mct_airflow_utils import notify_failure, notify_success, pipeline_context, run_cli_task

from airflow import DAG
from mobility_control_tower.operations.storage_inventory import cleanup_stale_temp_dirs, inventory_storage

DEFAULT_ARGS = {
    "owner": "mobility-control-tower",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
    "on_failure_callback": notify_failure,
    "on_success_callback": notify_success,
}


def full_history_quality(**context):
    cfg = pipeline_context()
    return run_cli_task(
        task_id="full_history_quality",
        command_args=[
            "run-quality-validation",
            "--suite",
            "history",
            "--history-run",
            cfg["history_run"],
            "--ge-root",
            cfg["ge_root"],
            "--quality-root",
            cfg["quality_root"],
        ],
        output_label="MCT quality validation written to",
        context=context,
    )


def storage_inventory(**context):
    cfg = pipeline_context()
    inventory = inventory_storage(
        raw_history_root=Path(cfg["raw_history_root"]),
        parsed_history_root=Path(cfg["history_root"]),
        serving_root=Path(cfg["serving_root"]),
    )
    removed = cleanup_stale_temp_dirs(Path(cfg["serving_root"]), older_than_hours=24)
    inventory["stale_temp_dirs_removed"] = [str(path) for path in removed]
    output = Path(cfg["pipeline_runs_root"]) / "maintenance" / context["run_id"].replace("/", "_").replace(":", "_") / "storage_inventory.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(output)


def evaluate_platform_incidents(**context):
    cfg = pipeline_context()
    return run_cli_task(
        task_id="evaluate_platform_incidents",
        command_args=[
            "evaluate-incidents",
            "--source",
            cfg["source"],
            "--correlation-id",
            f"{context.get('run_id', 'manual')}:platform",
            "--serving-root",
            cfg["serving_root"],
            "--history-root",
            cfg["history_root"],
            "--quality-root",
            cfg["quality_root"],
            "--json",
        ],
        context=context,
    )


with DAG(
    dag_id="daily_platform_maintenance",
    description="Daily full-history quality checks and safe storage inventory.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["mobility-control-tower", "maintenance"],
) as dag:
    quality = PythonOperator(task_id="full_history_quality", python_callable=full_history_quality)
    inventory = PythonOperator(task_id="storage_inventory", python_callable=storage_inventory)
    incidents = PythonOperator(task_id="evaluate_platform_incidents", python_callable=evaluate_platform_incidents)

    quality >> inventory >> incidents
