"""Five-minute GTFS-RT workflow: collect, validate, and refresh dbt marts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from airflow.decorators import dag, task

from mobility_control_tower.config import data_root, latest_run, load_source
from mobility_control_tower.dbt import build_dbt
from mobility_control_tower.quality import require_pass, validate_realtime
from mobility_control_tower.realtime_pipeline import download_realtime


@dag(
    dag_id="realtime_pipeline",
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["mct", "gtfs-rt"],
)
def realtime_pipeline():
    @task
    def fetch_parse_and_append() -> str:
        metadata = download_realtime(load_source(), data_root())
        return str(metadata["snapshot_id"])

    @task
    def quality_checks(snapshot_id: str) -> str:
        report_path = data_root() / "quality" / f"realtime-{snapshot_id}.json"
        require_pass(validate_realtime(data_root(), report_path))
        return snapshot_id

    @task
    def dbt_build(_: str) -> str:
        static_run = latest_run(data_root() / "silver" / "static")
        return str(build_dbt(Path(static_run), data_root()))

    dbt_build(quality_checks(fetch_parse_and_append()))


realtime_pipeline()
