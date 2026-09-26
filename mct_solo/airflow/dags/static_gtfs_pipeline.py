"""Daily static GTFS workflow: preserve, transform, validate, and build dbt."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from airflow.decorators import dag, task

from mct_solo.config import data_root, load_source
from mct_solo.dbt import build_dbt
from mct_solo.quality import require_pass, validate_static
from mct_solo.realtime_pipeline import ensure_empty_realtime_tables
from mct_solo.static_pipeline import download_static, transform_static


@dag(
    dag_id="static_gtfs_pipeline",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["mct", "gtfs"],
)
def static_gtfs_pipeline():
    @task
    def download_and_preserve() -> str:
        return str(download_static(load_source(), data_root()))

    @task
    def build_silver(raw_run: str) -> str:
        return str(transform_static(Path(raw_run), data_root()))

    @task
    def quality_checks(silver_run: str) -> str:
        run = Path(silver_run)
        report_path = data_root() / "quality" / f"static-{run.name}.json"
        report = validate_static(run, report_path)
        require_pass(report)
        return silver_run

    @task
    def dbt_build(silver_run: str) -> str:
        ensure_empty_realtime_tables(data_root())
        return str(build_dbt(Path(silver_run), data_root()))

    dbt_build(quality_checks(build_silver(download_and_preserve())))


static_gtfs_pipeline()
