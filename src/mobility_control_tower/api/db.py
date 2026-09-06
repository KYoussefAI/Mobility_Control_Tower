"""DuckDB helpers for the read-only local API."""

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
        rows = connection.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name").fetchall()
    return ([name for name, kind in rows if kind == "BASE TABLE"], [name for name, kind in rows if kind == "VIEW"])


def database_connected(db_path: Path) -> bool:
    try:
        with _connect(db_path) as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except duckdb.Error:
        return False


def view_exists(db_path: Path, view_name: str) -> bool:
    return view_name in list_tables_and_views(db_path)[1]


def query_view(db_path: Path, view_name: str, limit: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (filters or {}).items():
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with _connect(db_path) as connection:
        cursor = connection.execute(f"SELECT * FROM {view_name}{where} LIMIT ?", params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
