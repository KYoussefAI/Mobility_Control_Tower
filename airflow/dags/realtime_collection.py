"""Scheduled GTFS-Realtime historical collection orchestrated by Airflow."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from mct_airflow_utils import latest_child, notify_failure, notify_success, pipeline_context, run_cli_task


DEFAULT_ARGS = {
    "owner": "mobility-control-tower",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=20),
    "on_failure_callback": notify_failure,
    "on_success_callback": notify_success,
}


def collect_gtfs_rt(**context):
    cfg = pipeline_context()
    return run_cli_task(
        task_id="collect_gtfs_rt",
        command_args=[
            "collect-gtfs-rt",
            "--source",
            cfg["source"],
            "--feed-type",
            cfg["feed_type"],
            "--interval",
            cfg["polling_interval"],
            "--config",
            cfg["config"],
            "--raw-history-root",
            cfg["raw_history_root"],
            "--history-root",
            cfg["history_root"],
            "--max-polls",
            "1",
        ],
        context=context,
    )


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


def validate_history_with_ge(**context):
    cfg = pipeline_context()
    history_gold_run = context["ti"].xcom_pull(task_ids="run_dbt_history")
    return run_cli_task(
        task_id="validate_history_with_ge",
        command_args=[
            "run-ge-validation",
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
        output_label="Great Expectations validation written to",
        context=context,
    )


def build_serving_db_history(**context):
    cfg = pipeline_context()
    history_gold_run = context["ti"].xcom_pull(task_ids="run_dbt_history")
    static_gold_run = cfg["latest_static_gold_run"] or latest_child(Path(cfg["gold_root"]) / cfg["source"])
    return run_cli_task(
        task_id="build_serving_db_history",
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
        ],
        output_label="Serving database written to",
        context=context,
    )


with DAG(
    dag_id="realtime_collection",
    description="Minute-level GTFS-Realtime polling, historical KPI, and serving refresh pipeline.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval="* * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["mobility-control-tower", "gtfs-rt", "history"],
) as dag:
    collect = PythonOperator(task_id="collect_gtfs_rt", python_callable=collect_gtfs_rt)
    dbt_history = PythonOperator(task_id="run_dbt_history", python_callable=run_dbt_history)
    ge_history = PythonOperator(task_id="validate_history_with_ge", python_callable=validate_history_with_ge)
    serving = PythonOperator(task_id="build_serving_db_history", python_callable=build_serving_db_history)

    collect >> dbt_history >> ge_history >> serving
