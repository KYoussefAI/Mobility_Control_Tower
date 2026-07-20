"""Build and query a local DuckDB serving database from generated CSV data products."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from mobility_control_tower.serving.sql_views import QUERY_SQL, create_history_views, create_views

STATIC_TABLES = (
    "route_daily_trips",
    "route_hourly_departures",
    "stop_daily_departures",
    "network_daily_summary",
    "route_period_summary",
    "route_hourly_headway",
    "route_type_daily_summary",
    "busiest_route_day",
    "busiest_stop_day",
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
)
ESSENTIAL_STATIC_TABLES = ("route_daily_trips", "network_daily_summary", "route_period_summary")
RT_TABLES = (
    "rt_feed_health_snapshot",
    "rt_trip_update_enriched",
    "rt_route_delay_snapshot",
    "rt_stop_delay_snapshot",
    "rt_identifier_compatibility_snapshot",
)
SERVING_CONTRACT_VERSION = 1
REQUIRED_PUBLIC_VIEWS = ("v_network_overview", "v_top_routes_static")


def _csv_path(run_dir: Path, table: str) -> Path:
    return run_dir / f"{table}.csv"


def _load_csv_table(connection: duckdb.DuckDBPyConnection, table: str, csv_path: Path) -> dict[str, Any]:
    connection.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=true)", [str(csv_path)])
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info('{table}')").fetchall()]
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    row_count = row[0] if row else 0
    return {"file": str(csv_path), "row_count": int(row_count), "columns": columns}


def _validate_essential_static(gold_run: Path) -> None:
    manifest_path = gold_run / "dbt_run_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "success" or manifest.get("tool") != "dbt Core":
            raise ValueError(f"Gold artifact is not a successful dbt run: {manifest_path}")
    else:
        raise ValueError(f"Serving requires a dbt-produced Gold artifact with dbt_run_manifest.json: {gold_run}")
    missing = [f"{table}.csv" for table in ESSENTIAL_STATIC_TABLES if not _csv_path(gold_run, table).is_file()]
    if missing:
        raise ValueError(f"Missing essential static gold files: {', '.join(missing)}")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def current_pointer_path(source_id: str, serving_root: Path = Path("data/serving")) -> Path:
    return serving_root / source_id / "current.json"


def read_current_pointer(source_id: str, serving_root: Path = Path("data/serving")) -> dict[str, Any]:
    pointer = current_pointer_path(source_id, serving_root)
    if not pointer.is_file():
        raise FileNotFoundError(f"Serving current pointer not found: {pointer}")
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SERVING_CONTRACT_VERSION:
        raise ValueError(f"Unsupported serving pointer schema in {pointer}")
    database_path = Path(payload.get("database_path", ""))
    if not database_path.is_absolute():
        database_path = pointer.parent / database_path
    payload["resolved_database_path"] = str(database_path)
    return payload


def resolve_current_database(source_id: str, serving_root: Path = Path("data/serving")) -> Path:
    payload = read_current_pointer(source_id, serving_root)
    db_path = Path(payload["resolved_database_path"])
    if not db_path.is_file():
        raise FileNotFoundError(f"Serving database from current pointer does not exist: {db_path}")
    return db_path


def validate_serving_database(db_path: Path, *, require_history: bool = False) -> dict[str, Any]:
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")
    with duckdb.connect(str(db_path), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
        views = {name for name, table_type in rows if table_type == "VIEW"}
        tables = {name for name, table_type in rows if table_type == "BASE TABLE"}
        missing = [view for view in REQUIRED_PUBLIC_VIEWS if view not in views]
        if missing:
            raise ValueError(f"Serving database is missing required public views: {', '.join(missing)}")
        static_row = connection.execute("SELECT COUNT(*) FROM v_network_overview").fetchone()
        static_rows = int(static_row[0] if static_row else 0)
        if static_rows < 0:
            raise ValueError("Serving database returned an impossible negative static row count")
        history_rows = None
        if require_history:
            historical_views = sorted(
                view
                for view in views
                if view.startswith("v_") and ("history" in view or "vehicle" in view or "alert" in view or view == "v_collection_summary")
            )
            if not historical_views:
                raise ValueError("Historical serving publication requires at least one historical public view")
            if "v_collection_summary" in views:
                history_row = connection.execute("SELECT COUNT(*) FROM v_collection_summary").fetchone()
                history_rows = int(history_row[0] if history_row else 0)
            else:
                history_rows = 0
            if history_rows < 0:
                raise ValueError("Serving database returned an impossible negative historical row count")
    return {"tables": sorted(tables), "views": sorted(views), "static_rows": static_rows, "historical_rows": history_rows}


def build_serving_database(
    gold_run: Path,
    rt_gold_run: Path | None = None,
    serving_root: Path = Path("data/serving"),
    *,
    history_run: Path | None = None,
    history_gold_run: Path | None = None,
    quality_status: str = "unknown",
    serving_run_id: str | None = None,
    publish_current: bool = True,
) -> Path:
    if not gold_run.is_dir():
        raise FileNotFoundError(f"Static gold run directory not found: {gold_run}")
    if rt_gold_run is not None and not rt_gold_run.is_dir():
        raise FileNotFoundError(f"Real-time gold run directory not found: {rt_gold_run}")
    if history_run is not None and not history_run.is_dir():
        raise FileNotFoundError(f"Historical real-time directory not found: {history_run}")
    if history_gold_run is not None and not history_gold_run.is_dir():
        raise FileNotFoundError(f"Historical gold directory not found: {history_gold_run}")
    _validate_essential_static(gold_run)
    source_id = gold_run.parent.name
    run_id = serving_run_id or f"serving_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    runs_root = serving_root / source_id / "runs"
    output_dir = runs_root / run_id
    temp_dir = runs_root / f".{run_id}.tmp"
    if output_dir.exists():
        raise FileExistsError(f"Serving run already exists and will not be overwritten: {output_dir}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=False)
    temp_db_path = temp_dir / "mobility_control_tower.duckdb"
    loaded_tables: dict[str, dict[str, Any]] = {}
    try:
        with duckdb.connect(str(temp_db_path)) as connection:
            for table in STATIC_TABLES:
                path = _csv_path(gold_run, table)
                if path.is_file():
                    loaded_tables[table] = _load_csv_table(connection, table, path)
            if rt_gold_run is not None:
                for table in RT_TABLES:
                    path = _csv_path(rt_gold_run, table)
                    if path.is_file():
                        loaded_tables[table] = _load_csv_table(connection, table, path)
            views_created = create_views(connection, set(loaded_tables))
            views_created.extend(create_history_views(connection, history_run, history_gold_run))
        validation = validate_serving_database(temp_db_path, require_history=history_run is not None or history_gold_run is not None)
        manifest = {
            "schema_version": SERVING_CONTRACT_VERSION,
            "source": source_id,
            "serving_run_id": run_id,
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            "static_gold_run_id": gold_run.name,
            "dbt_gold_run_id": gold_run.name,
            "static_gold_run_path": _relative_or_absolute(gold_run),
            "realtime_gold_run_path": _relative_or_absolute(rt_gold_run) if rt_gold_run else None,
            "realtime_run_id": rt_gold_run.name if rt_gold_run else None,
            "historical_realtime_run_path": _relative_or_absolute(history_run) if history_run else None,
            "historical_gold_run_path": _relative_or_absolute(history_gold_run) if history_gold_run else None,
            "latest_included_realtime_snapshot": None,
            "database_path": "mobility_control_tower.duckdb",
            "quality_status": quality_status,
            "tables_loaded": loaded_tables,
            "views_created": views_created,
            "validation": validation,
            "example_query_names": sorted(QUERY_SQL),
            "assumptions": [
                "Static CSV gold outputs are exports read from the successful dbt-built DuckDB mart relations.",
                "DuckDB is used as an embedded analytical database, not a server.",
                "Real-time tables remain snapshot-based when loaded.",
                "Historical views query Parquet files directly through DuckDB read_parquet.",
            ],
            "limitations": [
                "This is not a public production database.",
                "Historical collection uses scheduled polling, not a streaming broker.",
                "Rebuild or refresh the serving artifact after regenerating dbt data products.",
            ],
        }
        _atomic_write_json(temp_dir / "serving_manifest.json", manifest)
        temp_dir.rename(output_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    if publish_current:
        pointer = {
            "schema_version": SERVING_CONTRACT_VERSION,
            "source": source_id,
            "serving_run_id": run_id,
            "canonical_database_path": f"runs/{run_id}/mobility_control_tower.duckdb",
            "database_path": f"runs/{run_id}/mobility_control_tower.duckdb",
            "serving_manifest_path": f"runs/{run_id}/serving_manifest.json",
            "dbt_gold_run_id": gold_run.name,
            "static_input_run_id": gold_run.name,
            "latest_included_realtime_snapshot": None,
            "quality_status": quality_status,
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            "contract_version": SERVING_CONTRACT_VERSION,
        }
        _atomic_write_json(current_pointer_path(source_id, serving_root), pointer)
    return output_dir


def query_serving_database(db_path: Path, query_name: str, limit: int = 10) -> pd.DataFrame:
    if query_name not in QUERY_SQL:
        available = ", ".join(sorted(QUERY_SQL))
        raise ValueError(f"Unknown query name '{query_name}'. Available query names: {available}")
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")
    safe_limit = max(1, min(int(limit), 1000))
    sql = QUERY_SQL[query_name].format(limit=safe_limit)
    with duckdb.connect(str(db_path), read_only=True) as connection:
        try:
            return connection.execute(sql).fetchdf()
        except duckdb.CatalogException as exc:
            raise ValueError(f"Query '{query_name}' is unavailable because its required view/table is missing") from exc


def dataframe_to_text_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows returned."
    text_frame = frame.astype(str)
    columns = list(text_frame.columns)
    widths = {column: max(len(column), *(len(value) for value in text_frame[column].tolist())) for column in columns}
    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    rows = [" | ".join(row[column].ljust(widths[column]) for column in columns) for _, row in text_frame.iterrows()]
    return "\n".join([header, separator, *rows])
