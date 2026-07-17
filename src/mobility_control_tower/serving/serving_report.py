"""Generate a Markdown report for the local DuckDB serving layer."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from mobility_control_tower.serving.duckdb_loader import query_serving_database


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows available."
    headers = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def _try_query(db_path: Path, query_name: str, limit: int = 10) -> str:
    try:
        return _markdown_table(query_serving_database(db_path, query_name, limit))
    except ValueError:
        return "Unavailable for this serving run."


def generate_serving_report(serving_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not serving_run.is_dir():
        raise FileNotFoundError(f"Serving run directory not found: {serving_run}")
    manifest_path = serving_run / "serving_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Serving manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    db_path = Path(manifest["database_path"])
    tables = manifest.get("tables_loaded", {})
    static_tables = {name: details for name, details in tables.items() if not name.startswith("rt_")}
    realtime_tables = {name: details for name, details in tables.items() if name.startswith("rt_")}
    table_rows = pd.DataFrame(
        [{"table": name, "rows": details.get("row_count", 0)} for name, details in sorted(tables.items())]
    )
    views = pd.DataFrame([{"view": name} for name in manifest.get("views_created", [])])
    report = f"""# Mobility Control Tower - Serving Layer Report

## 1. What the serving database contains

This local DuckDB serving layer stores queryable data products built from generated CSV files. It is not a production database.

- Database: `{db_path}`
- Static gold run: `{manifest.get('static_gold_run_path')}`
- Real-time gold run: `{manifest.get('realtime_gold_run_path') or 'not loaded'}`

## 2. Static tables loaded

{_markdown_table(pd.DataFrame([{"table": name, "rows": details.get("row_count", 0)} for name, details in sorted(static_tables.items())]))}

## 3. Real-time snapshot tables loaded

{_markdown_table(pd.DataFrame([{"table": name, "rows": details.get("row_count", 0)} for name, details in sorted(realtime_tables.items())])) if realtime_tables else "No real-time snapshot tables loaded."}

## 4. SQL views created

{_markdown_table(views)}

## 5. Example query results

### Network overview - first 7 days

{_try_query(db_path, "network-overview", 7)}

### Top 10 routes over the static service period

{_try_query(db_path, "top-routes", 10)}

### Route type summary sample

{_try_query(db_path, "route-types", 10)}

### Real-time feed health

{_try_query(db_path, "rt-feed-health", 10)}

### Real-time identifier compatibility

{_try_query(db_path, "rt-compatibility", 10)}

### Top delayed routes snapshot

{_try_query(db_path, "rt-top-delayed-routes", 10)}

## 6. What this proves technically

The project can package static and snapshot-based real-time outputs into a local DuckDB file with SQL views and predefined query examples. This makes the generated data products easy to inspect with SQL.

## 7. Current limitations

- This is a local DuckDB serving layer, not a production database.
- There is no API, dashboard, scheduler, or streaming system.
- Real-time outputs remain snapshot-based.
- Rebuild the database after regenerating CSV files.

## 8. Next project step

Use the local SQL views during demos and decide which views would be worth exposing later through an API or dashboard.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"serving_report_{serving_run.name}.md"
    output.write_text(report, encoding="utf-8")
    return output
