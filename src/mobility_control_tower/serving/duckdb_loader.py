"""Build and query the current local DuckDB serving artifact."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from mobility_control_tower.serving.sql_views import QUERY_SQL, create_views

TABLES = ['route_daily_trips', 'route_hourly_departures', 'stop_daily_departures', 'network_daily_summary', 'route_period_summary', 'route_hourly_headway', 'route_type_daily_summary', 'busiest_route_day', 'busiest_stop_day']
ESSENTIAL_TABLES = ("route_daily_trips", "network_daily_summary", "route_period_summary")
SERVING_CONTRACT_VERSION = 1


def _load(connection: duckdb.DuckDBPyConnection, table: str, path: Path) -> dict[str, Any]:
    connection.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=true)", [str(path)])
    count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return {"file": str(path), "row_count": int(count)}


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def current_pointer_path(source_id: str, serving_root: Path = Path("data/serving")) -> Path:
    return serving_root / source_id / "current.json"


def read_current_pointer(source_id: str, serving_root: Path = Path("data/serving")) -> dict[str, Any]:
    pointer = current_pointer_path(source_id, serving_root)
    if not pointer.is_file():
        raise FileNotFoundError(f"Serving current pointer not found: {pointer}")
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    database_path = pointer.parent / payload["database_path"]
    payload["resolved_database_path"] = str(database_path)
    return payload


def resolve_current_database(source_id: str, serving_root: Path = Path("data/serving")) -> Path:
    path = Path(read_current_pointer(source_id, serving_root)["resolved_database_path"])
    if not path.is_file():
        raise FileNotFoundError(f"Serving database does not exist: {path}")
    return path


def validate_serving_database(db_path: Path) -> dict[str, Any]:
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")
    with duckdb.connect(str(db_path), read_only=True) as connection:
        rows = connection.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
    tables = sorted(name for name, kind in rows if kind == "BASE TABLE")
    views = sorted(name for name, kind in rows if kind == "VIEW")
    missing = sorted({"v_network_overview", "v_top_routes_static"} - set(views))
    if missing:
        raise ValueError(f"Serving database is missing required views: {', '.join(missing)}")
    return {"tables": tables, "views": views}


def build_serving_database(
    gold_run: Path,
    serving_root: Path = Path("data/serving"),
    quality_status: str = "unknown",
) -> Path:
    normalized_quality = quality_status.strip().lower()
    if normalized_quality in {"failed", "failure", "invalid", "blocked"}:
        raise ValueError("A failed quality result cannot be published")
    if not gold_run.is_dir():
        raise FileNotFoundError(f"Gold run not found: {gold_run}")
    missing = [f"{table}.csv" for table in ESSENTIAL_TABLES if not (gold_run / f"{table}.csv").is_file()]
    if missing:
        raise ValueError(f"Missing essential Gold files: {', '.join(missing)}")

    run_id = datetime.now(timezone.utc).strftime("serving_%Y%m%dT%H%M%SZ")
    source_id = gold_run.parent.name
    output = serving_root / source_id / "runs" / run_id
    temporary = serving_root / source_id / "runs" / f".{run_id}.tmp"
    if output.exists():
        raise FileExistsError(f"Serving run already exists: {output}")
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True, exist_ok=False)
    db_path = temporary / "mobility_control_tower.duckdb"
    loaded: dict[str, dict[str, Any]] = {}
    try:
        with duckdb.connect(str(db_path)) as connection:
            for table in ['route_daily_trips', 'route_hourly_departures', 'stop_daily_departures', 'network_daily_summary', 'route_period_summary', 'route_hourly_headway', 'route_type_daily_summary', 'busiest_route_day', 'busiest_stop_day']:
                path = gold_run / f"{table}.csv"
                if path.is_file():
                    loaded[table] = _load(connection, table, path)
            views = create_views(connection, set(loaded))
        validation = validate_serving_database(db_path)
        final_db_path = output / "mobility_control_tower.duckdb"
        manifest = {"schema_version": SERVING_CONTRACT_VERSION, "source": source_id, "source_gold_run": str(gold_run), "database_path": str(final_db_path), "quality_status": normalized_quality, "tables_loaded": loaded, "views_created": views, "validation": validation}
        _atomic_json(temporary / "serving_manifest.json", manifest)
        temporary.rename(output)
        _atomic_json(current_pointer_path(source_id, serving_root), {"schema_version": SERVING_CONTRACT_VERSION, "source": source_id, "serving_run_id": run_id, "database_path": f"runs/{run_id}/mobility_control_tower.duckdb", "quality_status": normalized_quality})
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


def query_serving_database(db_path: Path, query_name: str, limit: int = 10) -> pd.DataFrame:
    if query_name not in QUERY_SQL:
        raise ValueError(f"Unknown query '{query_name}'. Available: {', '.join(sorted(QUERY_SQL))}")
    with duckdb.connect(str(db_path), read_only=True) as connection:
        return connection.execute(QUERY_SQL[query_name].format(limit=max(1, min(limit, 1000)))).fetchdf()


def dataframe_to_text_table(frame: pd.DataFrame) -> str:
    return "No rows returned." if frame.empty else frame.to_string(index=False)
