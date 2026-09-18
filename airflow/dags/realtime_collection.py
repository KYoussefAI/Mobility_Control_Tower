"""Bounded GTFS-Realtime snapshot collection DAG.

This DAG intentionally collects only one committed snapshot per run. Analytical
refresh, quality validation, and serving publication run in
``realtime_incremental_refresh``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from mct_airflow_utils import notify_failure, notify_success, pipeline_context, run_cli_task

from airflow import DAG

DEFAULT_ARGS = {
    "owner": "mobility-control-tower",
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=3),
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
            cfg["collection_interval"],
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


with DAG(
    dag_id="realtime_snapshot_collection",
    description="Minute-level GTFS-Realtime immutable snapshot collection only.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval="* * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["mobility-control-tower", "gtfs-rt", "collection"],
) as dag:
    collect = PythonOperator(task_id="collect_gtfs_rt", python_callable=collect_gtfs_rt, pool="external_feed")
