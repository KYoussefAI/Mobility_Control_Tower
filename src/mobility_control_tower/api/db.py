"""DuckDB helpers for the read-only local API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb


def validate_database_path(db_path: str | Path) -> Path:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {path}")
    return path


def _connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True)


def list_tables_and_views(db_path: Path) -> tuple[list[str], list[str]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()
    tables = [name for name, table_type in rows if table_type == "BASE TABLE"]
    views = [name for name, table_type in rows if table_type == "VIEW"]
    return tables, views


def database_connected(db_path: Path) -> bool:
    try:
        with _connect(db_path) as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except duckdb.Error:
        return False


def view_exists(db_path: Path, view_name: str) -> bool:
    _, views = list_tables_and_views(db_path)
    return view_name in views


def query_view(db_path: Path, view_name: str, limit: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    filters = filters or {}
    where_clauses: list[str] = []
    params: list[Any] = []
    for column, value in filters.items():
        if value is not None:
            where_clauses.append(f"{column} = ?")
            params.append(value)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    params.append(limit)
    with _connect(db_path) as connection:
        try:
            rows = connection.execute(f"SELECT * FROM {view_name}{where_sql} LIMIT ?", params).fetchdf()
        except duckdb.CatalogException as exc:
            raise ValueError(f"View '{view_name}' is not available in this serving database") from exc
    return rows.where(rows.notna(), None).to_dict("records")

