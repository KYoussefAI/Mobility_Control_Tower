"""Incremental analytical refresh for committed GTFS-Realtime snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from mct_airflow_utils import notify_failure, notify_success, pipeline_context, run_cli_task

from airflow import DAG
from mobility_control_tower.operations.watermarks import advance_watermark_after_publish, read_watermark, select_snapshots_after_watermark, watermark_lock
from mobility_control_tower.realtime.historical_storage import discover_committed_snapshots

DEFAULT_ARGS = {
    "owner": "mobility-control-tower",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=20),
    "on_failure_callback": notify_failure,
    "on_success_callback": notify_success,
}


def discover_new_snapshots(**context):
    cfg = pipeline_context()
    snapshots = discover_committed_snapshots(Path(cfg["history_run"]))
    watermark = read_watermark(Path(cfg["watermark_root"]), cfg["source"], cfg["feed_type"], "incremental_refresh")
    selected = select_snapshots_after_watermark(snapshots, watermark, int(cfg["incremental_lookback_count"]))
    if not selected:
        raise AirflowSkipException("No committed realtime snapshots beyond the analytical watermark.")
    context["ti"].xcom_push(key="latest_snapshot", value=selected[-1])
    return {"snapshots_selected": len(selected), "latest_snapshot_id": selected[-1].get("snapshot_id")}


def run_dbt_history(**context):
    cfg = pipeline_context()
    return run_cli_task(
        task_id="run_dbt_history",
        command_args=[
            "run-dbt",
            "--history-run",
            cfg["history_run"],
            "--project-dir",
            cfg["dbt_project_dir"],
            "--profiles-dir",
            cfg["dbt_profiles_dir"],
            "--output-root",
            cfg["dbt_output_root"],
        ],
        output_label="dbt gold output written to",
        context=context,
    )


def validate_recent_quality(**context):
    cfg = pipeline_context()
    history_gold_run = context["ti"].xcom_pull(task_ids="run_dbt_history")
    return run_cli_task(
        task_id="validate_recent_quality",
        command_args=[
            "run-quality-validation",
            "--suite",
            "history",
            "--gold-run",
            history_gold_run,
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


def publish_serving_refresh(**context):
    cfg = pipeline_context()
    history_gold_run = context["ti"].xcom_pull(task_ids="run_dbt_history")
    static_gold_run = cfg["latest_static_gold_run"]
    if not static_gold_run:
        raise ValueError("mct_latest_static_gold_run must be set by daily_static_pipeline before realtime refresh can publish serving.")
    return run_cli_task(
        task_id="publish_serving_refresh",
        command_args=[
            "build-serving-db",
            "--gold-run",
            static_gold_run,
            "--serving-root",
            cfg["serving_root"],
            "--history-run",
            cfg["history_run"],
            "--history-gold-run",
            history_gold_run,
            "--quality-status",
            "passed",
        ],
        output_label="Serving database written to",
        context=context,
    )


def advance_refresh_watermark(**context):
    cfg = pipeline_context()
    latest_snapshot = context["ti"].xcom_pull(task_ids="discover_new_snapshots", key="latest_snapshot")
    serving_db_path = Path(context["ti"].xcom_pull(task_ids="publish_serving_refresh"))
    serving_run_id = serving_db_path.parent.name
    with watermark_lock(Path(cfg["watermark_root"]), cfg["source"], cfg["feed_type"], "incremental_refresh"):
        return str(
            advance_watermark_after_publish(
                Path(cfg["watermark_root"]),
                source=cfg["source"],
                feed_type=cfg["feed_type"],
                workflow="incremental_refresh",
                snapshot=latest_snapshot,
                serving_run_id=serving_run_id,
                status="success",
            )
        )


def evaluate_reliability_incidents(**context):
    cfg = pipeline_context()
    latest_snapshot = context["ti"].xcom_pull(task_ids="discover_new_snapshots", key="latest_snapshot")
    correlation_id = f"{context.get('run_id', 'manual')}:{latest_snapshot.get('snapshot_id') if latest_snapshot else 'unknown'}"
    return run_cli_task(
        task_id="evaluate_reliability_incidents",
        command_args=[
            "evaluate-incidents",
            "--source",
            cfg["source"],
            "--correlation-id",
            correlation_id,
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
    dag_id="realtime_incremental_refresh",
    description="Refresh dbt historical marts and serving from committed realtime snapshots.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval="*/10 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["mobility-control-tower", "gtfs-rt", "incremental"],
) as dag:
    discover = PythonOperator(task_id="discover_new_snapshots", python_callable=discover_new_snapshots)
    dbt_history = PythonOperator(task_id="run_dbt_history", python_callable=run_dbt_history)
    quality = PythonOperator(task_id="validate_recent_quality", python_callable=validate_recent_quality)
    serving = PythonOperator(task_id="publish_serving_refresh", python_callable=publish_serving_refresh)
    incidents = PythonOperator(task_id="evaluate_reliability_incidents", python_callable=evaluate_reliability_incidents)
    watermark = PythonOperator(task_id="advance_refresh_watermark", python_callable=advance_refresh_watermark)

    discover >> dbt_history >> quality >> serving >> incidents >> watermark
