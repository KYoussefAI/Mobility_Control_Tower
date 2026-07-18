"""Build and query a local DuckDB serving database from generated CSV data products."""

from __future__ import annotations

import json
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
)
ESSENTIAL_STATIC_TABLES = ("route_daily_trips", "network_daily_summary", "route_period_summary")
RT_TABLES = (
    "rt_feed_health_snapshot",
    "rt_trip_update_enriched",
    "rt_route_delay_snapshot",
    "rt_stop_delay_snapshot",
    "rt_identifier_compatibility_snapshot",
)


def _csv_path(run_dir: Path, table: str) -> Path:
    return run_dir / f"{table}.csv"


def _load_csv_table(connection: duckdb.DuckDBPyConnection, table: str, csv_path: Path) -> dict[str, Any]:
    connection.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=true)", [str(csv_path)])
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info('{table}')").fetchall()]
    row_count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return {"file": str(csv_path), "row_count": int(row_count), "columns": columns}


def _validate_essential_static(gold_run: Path) -> None:
    missing = [f"{table}.csv" for table in ESSENTIAL_STATIC_TABLES if not _csv_path(gold_run, table).is_file()]
    if missing:
        raise ValueError(f"Missing essential static gold files: {', '.join(missing)}")


def build_serving_database(
    gold_run: Path,
    rt_gold_run: Path | None = None,
    serving_root: Path = Path("data/serving"),
    *,
    history_run: Path | None = None,
    history_gold_run: Path | None = None,
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
    output_dir = serving_root / source_id / gold_run.name
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "mobility_control_tower.duckdb"
    if db_path.exists():
        db_path.unlink()
    loaded_tables: dict[str, dict[str, Any]] = {}
    with duckdb.connect(str(db_path)) as connection:
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
    manifest = {
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "static_gold_run_path": str(gold_run),
        "realtime_gold_run_path": str(rt_gold_run) if rt_gold_run else None,
        "realtime_run_id": rt_gold_run.name if rt_gold_run else None,
        "historical_realtime_run_path": str(history_run) if history_run else None,
        "historical_gold_run_path": str(history_gold_run) if history_gold_run else None,
        "database_path": str(db_path),
        "tables_loaded": loaded_tables,
        "views_created": views_created,
        "example_query_names": sorted(QUERY_SQL),
        "assumptions": [
            "CSV gold outputs are the source of truth for this local serving database.",
            "DuckDB is used as an embedded analytical database, not a server.",
            "Real-time tables remain snapshot-based when loaded.",
            "Historical views query Parquet files directly through DuckDB read_parquet.",
        ],
        "limitations": [
            "This is not a production database.",
            "Historical collection uses scheduled polling, not a streaming broker.",
            "Rebuild the database after regenerating CSV data products.",
        ],
    }
    (output_dir / "serving_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
