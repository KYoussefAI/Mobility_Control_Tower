"""Shared Airflow helpers for Mobility Control Tower DAGs.

This module intentionally contains orchestration glue only. All data processing
continues to run through the public CLI.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from mobility_control_tower.observability import PIPELINE_DURATION, PIPELINE_FAILURES, PIPELINE_SUCCESS, ROWS_PROCESSED
except Exception:  # pragma: no cover - Airflow can import DAGs before package installation
    PIPELINE_DURATION = PIPELINE_FAILURES = PIPELINE_SUCCESS = ROWS_PROCESSED = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METADATA_ROOT = PROJECT_ROOT / "data" / "pipeline_runs"
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def airflow_variable(name: str, default: str) -> str:
    """Read an Airflow Variable with an environment fallback for local tests."""
    try:
        from airflow.models import Variable

        return Variable.get(name, default_var=default)
    except Exception:
        return os.environ.get(name.upper(), default)


def airflow_int_variable(name: str, default: int) -> int:
    value = airflow_variable(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def latest_child(parent: str | Path) -> str:
    path = Path(parent)
    children = [child for child in path.iterdir() if child.is_dir()] if path.is_dir() else []
    if not children:
        raise FileNotFoundError(f"No run directories found under {path}")
    return str(max(children, key=lambda child: child.stat().st_mtime))


def parse_output_path(stdout: str, label: str) -> str:
    pattern = re.compile(rf"{re.escape(label)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(stdout)
    if not match:
        raise ValueError(f"CLI output did not include expected label '{label}'. Output:\n{stdout}")
    return match.group(1).strip()


def parse_rows_processed(stdout: str) -> int | None:
    patterns = [
        r"Collected poll \d+:\s*(\d+)\s+stop updates",
        r'"row_count":\s*(\d+)',
        r"(\d+)\s+rows",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, stdout)
        if matches:
            return sum(int(value) for value in matches)
    return None


def pipeline_context() -> dict[str, str]:
    source = airflow_variable("mct_gtfs_source", "tisseo")
    feed_type = airflow_variable("mct_realtime_feed_type", "trip_updates")
    return {
        "source": source,
        "feed_type": feed_type,
        "config": airflow_variable("mct_sources_config", "config/sources.yml"),
        "raw_root": airflow_variable("mct_raw_root", "data/raw"),
        "bronze_root": airflow_variable("mct_bronze_root", "data/bronze"),
        "silver_root": airflow_variable("mct_silver_root", "data/silver"),
        "gold_root": airflow_variable("mct_gold_root", "data/gold"),
        "reports_dir": airflow_variable("mct_reports_dir", "data/reports"),
        "serving_root": airflow_variable("mct_serving_root", "data/serving"),
        "raw_history_root": airflow_variable("mct_raw_history_root", "data/raw_realtime/historical"),
        "history_root": airflow_variable("mct_history_root", "data/realtime_history"),
        "history_gold_root": airflow_variable("mct_history_gold_root", "data/history_gold"),
        "dbt_project_dir": airflow_variable("mct_dbt_project_dir", "dbt"),
        "dbt_profiles_dir": airflow_variable("mct_dbt_profiles_dir", "dbt"),
        "dbt_output_root": airflow_variable("mct_dbt_output_root", "data/dbt_gold"),
        "ge_root": airflow_variable("mct_ge_root", "great_expectations"),
        "quality_root": airflow_variable("mct_quality_root", "data/quality"),
        "pipeline_runs_root": airflow_variable("mct_pipeline_runs_root", str(DEFAULT_METADATA_ROOT)),
        "polling_interval": str(airflow_int_variable("mct_polling_interval", 30)),
        "history_run": str(Path(airflow_variable("mct_history_root", "data/realtime_history")) / source / feed_type),
        "latest_static_gold_run": airflow_variable("mct_latest_static_gold_run", ""),
    }


def build_cli_command(*args: str) -> list[str]:
    return [sys.executable, "-m", "mobility_control_tower.cli", *args]


def write_metadata(
    *,
    dag_id: str,
    task_id: str,
    airflow_run_id: str,
    command: list[str],
    start: datetime,
    end: datetime,
    status: str,
    output_path: str | None,
    stdout: str,
    stderr: str,
    rows_processed: int | None = None,
    metadata_root: str | Path = DEFAULT_METADATA_ROOT,
) -> Path:
    safe_run_id = airflow_run_id.replace("/", "_").replace(":", "_")
    output_dir = Path(metadata_root) / dag_id / safe_run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": airflow_run_id,
        "dag_id": dag_id,
        "task_id": task_id,
        "command": command,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_seconds": round((end - start).total_seconds(), 3),
        "status": status,
        "rows_processed": rows_processed,
        "output_path": output_path,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
    }
    path = output_dir / f"{task_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def run_cli_task(
    *,
    task_id: str,
    command_args: list[str],
    output_label: str | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    context = context or {}
    dag = context.get("dag")
    task = context.get("task")
    dag_id = getattr(dag, "dag_id", "manual")
    airflow_task_id = getattr(task, "task_id", task_id)
    airflow_run_id = context.get("run_id", "manual")
    metadata_root = pipeline_context()["pipeline_runs_root"]
    command = build_cli_command(*command_args)
    start = utc_now()
    output_path: str | None = None
    stdout = ""
    stderr = ""
    try:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, check=True)
        stdout = completed.stdout
        stderr = completed.stderr
        if output_label:
            output_path = parse_output_path(stdout, output_label)
        end = utc_now()
        rows_processed = parse_rows_processed(stdout)
        if PIPELINE_DURATION is not None:
            PIPELINE_DURATION.labels(pipeline=dag_id, task=airflow_task_id).observe((end - start).total_seconds())
            PIPELINE_SUCCESS.labels(pipeline=dag_id, task=airflow_task_id).inc()
            if rows_processed:
                ROWS_PROCESSED.labels(pipeline=dag_id, task=airflow_task_id).inc(rows_processed)
        write_metadata(
            dag_id=dag_id,
            task_id=airflow_task_id,
            airflow_run_id=airflow_run_id,
            command=command,
            start=start,
            end=end,
            status="success",
            output_path=output_path,
            stdout=stdout,
            stderr=stderr,
            rows_processed=rows_processed,
            metadata_root=metadata_root,
        )
        logger.info(stdout)
        if stderr:
            logger.warning(stderr)
        return output_path or stdout
    except subprocess.CalledProcessError as exc:
        end = utc_now()
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if PIPELINE_DURATION is not None:
            PIPELINE_DURATION.labels(pipeline=dag_id, task=airflow_task_id).observe((end - start).total_seconds())
            PIPELINE_FAILURES.labels(pipeline=dag_id, task=airflow_task_id).inc()
        write_metadata(
            dag_id=dag_id,
            task_id=airflow_task_id,
            airflow_run_id=airflow_run_id,
            command=command,
            start=start,
            end=end,
            status="failed",
            output_path=output_path,
            stdout=stdout,
            stderr=stderr,
            metadata_root=metadata_root,
        )
        logger.info(stdout)
        logger.error(stderr)
        raise


def notify_failure(context: dict[str, Any]) -> None:
    task = context.get("task_instance")
    logger.error("[notification-ready] Task failed: %s. Extend this callback for email or Slack.", task)


def notify_success(context: dict[str, Any]) -> None:
    task = context.get("task_instance")
    logger.info("[notification-ready] Task succeeded: %s. Extend this callback for email or Slack.", task)
