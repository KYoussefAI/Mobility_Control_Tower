"""Daily static GTFS pipeline orchestrated by Airflow.

Every task delegates work to the Mobility Control Tower CLI.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from mct_airflow_utils import notify_failure, notify_success, pipeline_context, run_cli_task


DEFAULT_ARGS = {
    "owner": "mobility-control-tower",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=45),
    "on_failure_callback": notify_failure,
    "on_success_callback": notify_success,
}


def ingest_gtfs(**context):
    cfg = pipeline_context()
    return run_cli_task(
        task_id="ingest_gtfs",
        command_args=[
            "ingest-gtfs",
            "--source",
            cfg["source"],
            "--download",
            "--config",
            cfg["config"],
            "--raw-root",
            cfg["raw_root"],
        ],
        output_label="Raw GTFS preserved in",
        context=context,
    )


def profile_gtfs(**context):
    cfg = pipeline_context()
    raw_run = context["ti"].xcom_pull(task_ids="ingest_gtfs")
    return run_cli_task(
        task_id="profile_gtfs",
        command_args=["profile-gtfs", "--raw-run", raw_run, "--reports-dir", cfg["reports_dir"]],
        output_label="Markdown report written to",
        context=context,
    )


def build_bronze(**context):
    cfg = pipeline_context()
    raw_run = context["ti"].xcom_pull(task_ids="ingest_gtfs")
    return run_cli_task(
        task_id="build_bronze",
        command_args=["build-bronze", "--raw-run", raw_run, "--bronze-root", cfg["bronze_root"]],
        output_label="Bronze GTFS written to",
        context=context,
    )


def build_silver(**context):
    cfg = pipeline_context()
    bronze_run = context["ti"].xcom_pull(task_ids="build_bronze")
    return run_cli_task(
        task_id="build_silver",
        command_args=["build-silver", "--bronze-run", bronze_run, "--silver-root", cfg["silver_root"]],
        output_label="Silver GTFS written to",
        context=context,
    )


def validate_gtfs(**context):
    cfg = pipeline_context()
    silver_run = context["ti"].xcom_pull(task_ids="build_silver")
    return run_cli_task(
        task_id="validate_gtfs",
        command_args=["validate-gtfs", "--silver-run", silver_run, "--reports-dir", cfg["reports_dir"]],
        output_label="Markdown quality report written to",
        context=context,
    )


def build_gold(**context):
    cfg = pipeline_context()
    silver_run = context["ti"].xcom_pull(task_ids="build_silver")
    return run_cli_task(
        task_id="build_gold",
        command_args=["build-gold", "--silver-run", silver_run, "--gold-root", cfg["gold_root"]],
        output_label="Gold KPI tables written to",
        context=context,
    )


def run_dbt_models(**context):
    cfg = pipeline_context()
    silver_run = context["ti"].xcom_pull(task_ids="build_silver")
    return run_cli_task(
        task_id="run_dbt_models",
        command_args=[
            "run-dbt",
            "--silver-run",
            silver_run,
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


def test_dbt_models(**context):
    cfg = pipeline_context()
    return run_cli_task(
        task_id="test_dbt_models",
        command_args=["test-dbt", "--project-dir", cfg["dbt_project_dir"], "--profiles-dir", cfg["dbt_profiles_dir"]],
        output_label="dbt test results written to",
        context=context,
    )


def validate_with_ge(**context):
    cfg = pipeline_context()
    silver_run = context["ti"].xcom_pull(task_ids="build_silver")
    dbt_gold_run = context["ti"].xcom_pull(task_ids="run_dbt_models")
    return run_cli_task(
        task_id="validate_with_ge",
        command_args=[
            "run-ge-validation",
            "--suite",
            "all",
            "--silver-run",
            silver_run,
            "--gold-run",
            dbt_gold_run,
            "--ge-root",
            cfg["ge_root"],
            "--quality-root",
            cfg["quality_root"],
        ],
        output_label="Great Expectations validation written to",
        context=context,
    )


def generate_static_charts(**context):
    cfg = pipeline_context()
    gold_run = context["ti"].xcom_pull(task_ids="run_dbt_models")
    return run_cli_task(
        task_id="generate_static_charts",
        command_args=["generate-static-charts", "--gold-run", gold_run, "--reports-dir", cfg["reports_dir"]],
        output_label="Static charts written to",
        context=context,
    )


def generate_demo_report(**context):
    cfg = pipeline_context()
    gold_run = context["ti"].xcom_pull(task_ids="run_dbt_models")
    return run_cli_task(
        task_id="generate_demo_report",
        command_args=["generate-demo-report", "--gold-run", gold_run, "--reports-dir", cfg["reports_dir"]],
        output_label="Demo report written to",
        context=context,
    )


def build_serving_db(**context):
    cfg = pipeline_context()
    gold_run = context["ti"].xcom_pull(task_ids="run_dbt_models")
    return run_cli_task(
        task_id="build_serving_db",
        command_args=["build-serving-db", "--gold-run", gold_run, "--serving-root", cfg["serving_root"]],
        output_label="Serving database written to",
        context=context,
    )


with DAG(
    dag_id="daily_static_pipeline",
    description="Daily static GTFS ingestion, validation, KPI, report, and serving pipeline.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["mobility-control-tower", "gtfs", "static"],
) as dag:
    ingest = PythonOperator(task_id="ingest_gtfs", python_callable=ingest_gtfs)
    profile = PythonOperator(task_id="profile_gtfs", python_callable=profile_gtfs)
    bronze = PythonOperator(task_id="build_bronze", python_callable=build_bronze)
    silver = PythonOperator(task_id="build_silver", python_callable=build_silver)
    validate = PythonOperator(task_id="validate_gtfs", python_callable=validate_gtfs)
    dbt_run = PythonOperator(task_id="run_dbt_models", python_callable=run_dbt_models)
    dbt_test = PythonOperator(task_id="test_dbt_models", python_callable=test_dbt_models)
    ge = PythonOperator(task_id="validate_with_ge", python_callable=validate_with_ge)
    charts = PythonOperator(task_id="generate_static_charts", python_callable=generate_static_charts)
    report = PythonOperator(task_id="generate_demo_report", python_callable=generate_demo_report)
    serving = PythonOperator(task_id="build_serving_db", python_callable=build_serving_db)

    ingest >> profile >> bronze >> silver >> validate >> dbt_run >> dbt_test >> ge >> charts >> report >> serving
