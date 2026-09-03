"""dbt Core wrappers for the static analytical project."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

STATIC_MODELS = (
    "route_daily_trips", "route_hourly_departures", "stop_daily_departures", "network_daily_summary",
    "route_period_summary", "route_hourly_headway", "route_type_daily_summary", "busiest_route_day", "busiest_stop_day",
)


def _dbt_binary() -> str:
    executable = shutil.which("dbt")
    if not executable:
        raise RuntimeError("dbt Core is required; install the analytics dependencies first")
    return executable


def _run(command: str, project_dir: Path, profiles_dir: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    args = [_dbt_binary(), command, "--project-dir", str(project_dir), "--profiles-dir", str(profiles_dir), *(extra or [])]
    return subprocess.run(args, check=True, text=True, capture_output=True)


def run_dbt(
    *,
    silver_run: Path,
    project_dir: Path = Path("dbt"),
    profiles_dir: Path = Path("dbt"),
    output_root: Path = Path("data/dbt_gold"),
) -> Path:
    if not silver_run.is_dir():
        raise FileNotFoundError(f"Silver run not found: {silver_run}")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = output_root / silver_run.parent.name / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    database_path = (output_dir / "mobility_control_tower_dbt.duckdb").resolve()
    os.environ["MCT_DBT_DATABASE_PATH"] = str(database_path)
    result = _run(
        "build",
        project_dir,
        profiles_dir,
        ["--vars", json.dumps({"silver_run": str(silver_run.resolve())})],
    )
    with duckdb.connect(str(database_path), read_only=True) as connection:
        available = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        for model in STATIC_MODELS:
            if model in available:
                connection.execute(f"COPY (SELECT * FROM {model}) TO ? (HEADER, DELIMITER ',')", [str(output_dir / f"{model}.csv")])
    (output_dir / "dbt_run_manifest.json").write_text(
        json.dumps({"status": "success", "tool": "dbt Core", "silver_run": str(silver_run), "database_path": str(database_path), "stdout": result.stdout}, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_dir


def test_dbt(project_dir: Path = Path("dbt"), profiles_dir: Path = Path("dbt")) -> Path:
    _run("test", project_dir, profiles_dir)
    return project_dir / "target" / "run_results.json"


def generate_dbt_docs(project_dir: Path = Path("dbt"), profiles_dir: Path = Path("dbt")) -> Path:
    _run("docs", project_dir, profiles_dir, ["generate"])
    return project_dir / "target" / "index.html"


def run_quality_validation(
    *,
    suite_name: str,
    silver_run: Path | None = None,
    gold_run: Path | None = None,
    ge_root: Path = Path("quality_contracts"),
    quality_root: Path = Path("data/quality"),
) -> Path:
    selected = ("silver", "gold") if suite_name == "all" else (suite_name,)
    results = []
    for suite in selected:
        run = silver_run if suite == "silver" else gold_run
        if run is None or not run.is_dir():
            raise FileNotFoundError(f"{suite.title()} run not found: {run}")
        definition = json.loads((ge_root / "expectations" / f"{suite}_suite.json").read_text(encoding="utf-8"))
        tables = {path.stem: pd.read_csv(path, dtype=str, keep_default_na=False) for path in run.glob("*.csv")}
        for expectation in definition["expectations"]:
            table = expectation["table"]
            kind = expectation["expectation_type"]
            kwargs = expectation["kwargs"]
            frame = tables.get(table)
            if frame is None:
                results.append({"suite": suite, "table": table, "expectation": kind, "success": False, "unexpected_count": 1})
                continue
            column = kwargs["column"]
            if kind == "expect_column_values_to_not_be_null":
                bad = frame[column].astype(str).str.strip().eq("")
            elif kind == "expect_column_values_to_be_unique":
                bad = frame[column].duplicated(keep=False)
            elif kind == "expect_column_values_to_be_between":
                values = pd.to_numeric(frame[column], errors="coerce")
                bad = values.isna()
                if kwargs.get("min_value") is not None:
                    bad |= values < float(kwargs["min_value"])
                if kwargs.get("max_value") is not None:
                    bad |= values > float(kwargs["max_value"])
            elif kind == "expect_column_pair_values_to_exist":
                reference = tables[kwargs["reference_table"]][kwargs["reference_column"]]
                bad = ~frame[column].isin(set(reference))
            else:
                raise ValueError(f"Unsupported expectation type: {kind}")
            results.append({"suite": suite, "table": table, "expectation": kind, "success": not bool(bad.any()), "unexpected_count": int(bad.sum())})
    failed = sum(not item["success"] for item in results)
    quality_root.mkdir(parents=True, exist_ok=True)
    output = quality_root / "latest_validation_summary.json"
    output.write_text(json.dumps({"success": failed == 0, "expectations_evaluated": len(results), "expectations_failed": failed, "results": results}, indent=2) + "\n", encoding="utf-8")
    if failed:
        raise ValueError(f"Quality validation failed: {failed} expectations failed. Results: {output}")
    return output
