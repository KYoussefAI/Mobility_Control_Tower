"""CLI wrappers for dbt Core and MCT quality-contract integration.

The wrappers keep Python ETL as the source of ingestion/bronze/silver logic.
dbt is the only production Gold transformation path; this module never
substitutes Python KPI builders for dbt outputs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

DBT_STATIC_MODELS = (
    "route_daily_trips",
    "route_hourly_departures",
    "stop_daily_departures",
    "network_daily_summary",
    "route_period_summary",
    "route_hourly_headway",
    "route_type_daily_summary",
    "busiest_route_day",
    "busiest_stop_day",
)
DBT_HISTORY_MODELS = (
    "realtime_trip_coverage",
    "fct_realtime_delay_observations",
    "route_delay_distribution",
    "stop_delay_distribution",
    "network_delay_distribution",
    "route_on_time_performance",
    "network_on_time_performance",
    "fct_explicit_trip_cancellations",
    "route_cancellation_summary",
    "network_cancellation_summary",
    "fct_observed_headways",
    "fct_headway_reliability_events",
    "route_excess_waiting_time",
    "network_reliability_summary",
    "reliability_incident_snapshot",
    "route_delay_history",
    "stop_delay_history",
    "delay_evolution_by_hour",
    "feed_freshness_trend",
    "trip_match_trend",
    "daily_summary",
)
DBT_MODELS = (*DBT_STATIC_MODELS, *DBT_HISTORY_MODELS)


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _dbt_binary() -> str | None:
    return shutil.which("dbt")


def _require_dbt_binary() -> str:
    binary = _dbt_binary()
    if not binary:
        raise FileNotFoundError(
            "dbt executable not found. Install analytics dependencies with " 'python -m pip install -e ".[analytics]" and rerun the command.'
        )
    return binary


def _run_dbt_command(
    *,
    project_dir: Path,
    profiles_dir: Path,
    command: str | tuple[str, ...],
    vars_payload: dict[str, str],
    db_path: Path,
    target_path: Path,
    select: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    binary = _require_dbt_binary()
    args = [
        binary,
        *(command if isinstance(command, tuple) else (command,)),
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(profiles_dir),
        "--target-path",
        str(target_path),
    ]
    if vars_payload:
        args.extend(["--vars", json.dumps(vars_payload)])
    if select:
        args.extend(["--select", *select])
    env = dict(os.environ)
    env["MCT_DBT_DATABASE_PATH"] = str(db_path)
    return subprocess.run(args, check=True, text=True, capture_output=True, env=env)


def _validate_input_path(path: Path | None, label: str) -> None:
    if path is not None and not path.is_dir():
        raise FileNotFoundError(f"{label} directory not found: {path}")


def _model_selection(silver_run: Path | None, history_run: Path | None) -> tuple[str, ...]:
    selected: list[str] = []
    if silver_run is not None:
        selected.extend(f"+{model}" for model in DBT_STATIC_MODELS)
    if history_run is not None:
        selected.extend(f"+{model}" for model in DBT_HISTORY_MODELS)
    return tuple(selected)


def _source_id(silver_run: Path | None, history_run: Path | None) -> str:
    if silver_run is not None:
        return silver_run.parent.name
    if history_run is not None:
        return history_run.parent.parent.name if history_run.parent.name == "trip_updates" else history_run.parent.name
    raise ValueError("run-dbt requires --silver-run, --history-run, or both")


def _duckdb_table_exists(connection: duckdb.DuckDBPyConnection, table: str) -> bool:
    row = connection.execute(
        "select count(*) from information_schema.tables where table_schema = current_schema() and table_name = ?",
        [table],
    ).fetchone()
    return bool(row and row[0])


def _export_dbt_models(db_path: Path, output_dir: Path) -> dict[str, dict[str, Any]]:
    models_created: dict[str, dict[str, Any]] = {}
    with duckdb.connect(str(db_path), read_only=True) as connection:
        for model in DBT_MODELS:
            if not _duckdb_table_exists(connection, model):
                continue
            csv_path = output_dir / f"{model}.csv"
            parquet_path = output_dir / f"{model}.parquet"
            connection.execute(f"COPY (SELECT * FROM {model}) TO ? (HEADER, DELIMITER ',')", [str(csv_path)])
            connection.execute(f"COPY (SELECT * FROM {model}) TO ? (FORMAT PARQUET)", [str(parquet_path)])
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info('{model}')").fetchall()]
            row = connection.execute(f"SELECT COUNT(*) FROM {model}").fetchone()
            models_created[model] = {
                "relation": model,
                "row_count": int(row[0]) if row else 0,
                "columns": columns,
                "csv": csv_path.name,
                "parquet": parquet_path.name,
            }
    return models_created


def _dbt_version() -> str:
    try:
        completed = subprocess.run([_require_dbt_binary(), "--version"], check=True, text=True, capture_output=True, timeout=15)
        return completed.stdout.strip()
    except subprocess.TimeoutExpired:
        return "dbt version probe timed out after successful dbt command execution"


def run_dbt(
    *,
    silver_run: Path | None = None,
    history_run: Path | None = None,
    project_dir: Path = Path("dbt"),
    profiles_dir: Path = Path("dbt"),
    output_root: Path = Path("data/dbt_gold"),
    use_installed: bool = True,
) -> Path:
    """Run a real dbt build and export dbt-built mart relations."""
    if silver_run is None and history_run is None:
        raise ValueError("run-dbt requires --silver-run, --history-run, or both")
    if not use_installed:
        raise RuntimeError("run-dbt requires the real dbt executable; --no-installed-dbt is no longer supported for Gold builds.")
    _validate_input_path(project_dir, "dbt project")
    _validate_input_path(profiles_dir, "dbt profiles")
    _validate_input_path(silver_run, "Silver run")
    _validate_input_path(history_run, "History run")

    run_id = _utc_run_id()
    source_id = _source_id(silver_run, history_run)
    output_dir = output_root / source_id / run_id
    temp_dir = output_root / source_id / f".{run_id}.tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=False)
    db_path = (temp_dir / "mobility_control_tower_dbt.duckdb").resolve()
    target_path = (temp_dir / "target").resolve()
    vars_payload: dict[str, str] = {}
    if silver_run is not None:
        vars_payload["silver_run"] = str(silver_run.resolve())
    if history_run is not None:
        vars_payload["history_run"] = str(history_run.resolve())
    command_started = datetime.now(timezone.utc)
    command_args = [
        _require_dbt_binary(),
        "build",
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(profiles_dir),
        "--target-path",
        str(target_path),
        "--vars",
        json.dumps(vars_payload),
        "--select",
        *_model_selection(silver_run, history_run),
    ]
    try:
        try:
            completed = _run_dbt_command(
                project_dir=project_dir,
                profiles_dir=profiles_dir,
                command="build",
                vars_payload=vars_payload,
                db_path=db_path,
                target_path=target_path,
                select=_model_selection(silver_run, history_run),
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"dbt build failed with exit code {exc.returncode}. stdout: {(exc.stdout or '')[-2000:]} stderr: {(exc.stderr or '')[-2000:]}"
            ) from exc
        models_created = _export_dbt_models(db_path, temp_dir)
        manifest_path = target_path / "manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"dbt build completed but manifest.json was not found at {manifest_path}")
        final_db_path = (output_dir / db_path.name).resolve()
        final_target_path = (output_dir / target_path.name).resolve()
        final_manifest_path = final_target_path / "manifest.json"
        _write_json(
            temp_dir / "dbt_run_manifest.json",
            {
                "source": source_id,
                "run_id": run_id,
                "generated_timestamp": datetime.now(timezone.utc).isoformat(),
                "command_started_timestamp": command_started.isoformat(),
                "status": "success",
                "tool": "dbt Core",
                "dbt_version": _dbt_version(),
                "command": command_args,
                "project_dir": str(project_dir),
                "profiles_dir": str(profiles_dir),
                "target_path": str(final_target_path),
                "dbt_manifest_path": str(final_manifest_path),
                "database_path": str(final_db_path),
                "silver_run": str(silver_run) if silver_run else None,
                "history_run": str(history_run) if history_run else None,
                "models_created": models_created,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
                "contract": "Run-scoped directory containing the dbt DuckDB database plus CSV/Parquet exports read from dbt-built mart relations.",
            },
        )
        if output_dir.exists():
            raise FileExistsError(f"dbt output directory already exists: {output_dir}")
        temp_dir.rename(output_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return output_dir


def _schema_files(project_dir: Path) -> list[Path]:
    return sorted(project_dir.glob("models/**/schema.yml"))


def test_dbt(project_dir: Path = Path("dbt"), profiles_dir: Path = Path("dbt"), use_installed: bool = True) -> Path:
    """Run real dbt tests."""
    if not use_installed:
        raise RuntimeError("test-dbt requires the real dbt executable; local fallback validation has been removed.")
    db_path = project_dir / "target" / "test.duckdb"
    target_path = project_dir / "target"
    _run_dbt_command(project_dir=project_dir, profiles_dir=profiles_dir, command="test", vars_payload={}, db_path=db_path, target_path=target_path)
    return target_path / "run_results.json"


def generate_dbt_docs(project_dir: Path = Path("dbt"), profiles_dir: Path = Path("dbt"), use_installed: bool = True) -> Path:
    """Generate real dbt docs artifacts."""
    if not use_installed:
        raise RuntimeError("generate-dbt-docs requires the real dbt executable; local docs fallback has been removed.")
    db_path = project_dir / "target" / "docs.duckdb"
    target_path = project_dir / "target"
    _run_dbt_command(
        project_dir=project_dir, profiles_dir=profiles_dir, command=("docs", "generate"), vars_payload={}, db_path=db_path, target_path=target_path
    )
    return target_path / "index.html"


def _read_csv_table(root: Path, table: str) -> pd.DataFrame:
    path = root / f"{table}.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _read_parquet_history(history_run: Path, file_name: str) -> pd.DataFrame:
    files = sorted(history_run.glob(f"date=*/hour=*/snapshot_timestamp=*/{file_name}"))
    if not files:
        return pd.DataFrame()
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)


def _expect_not_null(frame: pd.DataFrame, column: str) -> tuple[bool, int]:
    if frame.empty or column not in frame.columns:
        return False, 0
    failed = int(frame[column].isna().sum() + (frame[column].astype(str).str.strip() == "").sum())
    return failed == 0, failed


def _expect_unique(frame: pd.DataFrame, column: str) -> tuple[bool, int]:
    if frame.empty or column not in frame.columns:
        return False, 0
    failed = int(frame[column].duplicated().sum())
    return failed == 0, failed


def _expect_between(frame: pd.DataFrame, column: str, min_value: float | None = None, max_value: float | None = None) -> tuple[bool, int]:
    if frame.empty or column not in frame.columns:
        return False, 0
    values = pd.to_numeric(frame[column].replace("", pd.NA), errors="coerce")
    mask = pd.Series(False, index=frame.index)
    if min_value is not None:
        mask |= values < min_value
    if max_value is not None:
        mask |= values > max_value
    return int(mask.sum()) == 0, int(mask.sum())


def _expect_exists(frame: pd.DataFrame, column: str, reference: pd.DataFrame, reference_column: str) -> tuple[bool, int]:
    if frame.empty or reference.empty or column not in frame.columns or reference_column not in reference.columns:
        return False, 0
    allowed = set(reference[reference_column].astype(str))
    mask = ~frame[column].astype(str).isin(allowed)
    return int(mask.sum()) == 0, int(mask.sum())


def _load_suite(name: str, ge_root: Path) -> dict[str, Any]:
    path = ge_root / "expectations" / f"{name}_suite.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _tables_for_suite(suite_name: str, silver_run: Path | None, gold_run: Path | None, history_run: Path | None) -> dict[str, pd.DataFrame]:
    if suite_name == "silver" and silver_run:
        return {table: _read_csv_table(silver_run, table) for table in ("routes", "trips", "stop_times", "stops", "calendar", "calendar_dates")}
    if suite_name == "gold" and gold_run:
        return {path.stem: pd.read_csv(path, dtype=str, keep_default_na=False) for path in sorted(gold_run.glob("*.csv"))}
    if suite_name == "history" and history_run:
        return {
            "stop_time_updates": _read_parquet_history(history_run, "stop_time_updates.parquet"),
            "feed_summary": _read_parquet_history(history_run, "feed_summary.parquet"),
        }
    return {}


def run_quality_validation(
    *,
    suite_name: str = "all",
    silver_run: Path | None = None,
    gold_run: Path | None = None,
    history_run: Path | None = None,
    ge_root: Path = Path("quality_contracts"),
    quality_root: Path = Path("data/quality"),
) -> Path:
    """Run MCT quality-contract validation over pipeline outputs."""
    selected = ("silver", "gold", "history") if suite_name == "all" else (suite_name,)
    results: list[dict[str, Any]] = []
    for suite in selected:
        suite_config = _load_suite(suite, ge_root)
        tables = _tables_for_suite(suite, silver_run, gold_run, history_run)
        for expectation in suite_config.get("expectations", []):
            table = expectation["table"]
            frame = tables.get(table, pd.DataFrame())
            kwargs = expectation.get("kwargs", {})
            exp_type = expectation["expectation_type"]
            if exp_type == "expect_column_values_to_not_be_null":
                success, failed = _expect_not_null(frame, kwargs["column"])
            elif exp_type == "expect_column_values_to_be_unique":
                success, failed = _expect_unique(frame, kwargs["column"])
            elif exp_type == "expect_column_values_to_be_between":
                success, failed = _expect_between(frame, kwargs["column"], kwargs.get("min_value"), kwargs.get("max_value"))
            elif exp_type == "expect_column_pair_values_to_exist":
                success, failed = _expect_exists(frame, kwargs["column"], tables.get(kwargs["reference_table"], pd.DataFrame()), kwargs["reference_column"])
            else:
                success, failed = False, 0
            results.append(
                {
                    "suite": suite,
                    "table": table,
                    "expectation_type": exp_type,
                    "column": kwargs.get("column"),
                    "success": bool(success),
                    "unexpected_count": int(failed),
                }
            )

    total = len(results)
    passed = sum(1 for result in results if result["success"])
    summary = {
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "success": passed == total if total else False,
        "success_rate": round((passed / total) * 100, 2) if total else 0,
        "expectations_evaluated": total,
        "expectations_successful": passed,
        "expectations_failed": total - passed,
        "failed_expectations": [result for result in results if not result["success"]],
        "results": results,
        "freshness": {
            "silver_run": str(silver_run) if silver_run else None,
            "gold_run": str(gold_run) if gold_run else None,
            "history_run": str(history_run) if history_run else None,
        },
    }
    run_id = _utc_run_id()
    validation_path = ge_root / "validation_results" / f"{run_id}_{suite_name}.json"
    _write_json(validation_path, summary)
    _write_json(quality_root / "latest_validation_summary.json", summary)
    data_docs = ge_root / "data_docs" / "local_site" / "index.html"
    data_docs.parent.mkdir(parents=True, exist_ok=True)
    data_docs.write_text(
        f"<html><body><h1>MCT Quality Contract Docs</h1><p>Success rate: {summary['success_rate']}%</p><p>Generated: {summary['generated_timestamp']}</p></body></html>\n",
        encoding="utf-8",
    )
    if not summary["success"]:
        raise RuntimeError(
            f"MCT quality validation failed: {summary['expectations_failed']} of {summary['expectations_evaluated']} expectations failed. Results: {validation_path}"
        )
    return validation_path


def run_ge_validation(**kwargs: Any) -> Path:
    """Legacy alias for run_quality_validation."""
    return run_quality_validation(**kwargs)
