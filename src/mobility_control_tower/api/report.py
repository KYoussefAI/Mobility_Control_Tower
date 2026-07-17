"""Generate Markdown documentation for the local API."""

from __future__ import annotations

from pathlib import Path

from mobility_control_tower.api.db import list_tables_and_views, query_view, validate_database_path, view_exists


def _markdown_table(rows: list[dict]) -> str:
    if not rows:
        return "No rows available."
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")).replace("|", "\\|") for header in headers) + " |")
    return "\n".join(lines)


def _sample(db_path: Path, view_name: str, limit: int = 2) -> str:
    if not view_exists(db_path, view_name):
        return "Unavailable in this serving database."
    return _markdown_table(query_view(db_path, view_name, limit))


def _run_id_from_db_path(db_path: Path) -> str:
    return db_path.parent.name


def generate_api_report(db_path: Path, reports_dir: Path = Path("data/reports")) -> Path:
    resolved = validate_database_path(db_path)
    tables, views = list_tables_and_views(resolved)
    static_endpoints = [
        "GET /static/network-overview",
        "GET /static/top-routes",
        "GET /static/hourly-headway",
        "GET /static/route-types",
    ]
    realtime_endpoints = [
        "GET /realtime/feed-health",
        "GET /realtime/compatibility",
        "GET /realtime/top-delayed-routes",
        "GET /realtime/top-delayed-stops",
    ]
    report = f"""# Mobility Control Tower - Local API Report

## 1. What the API exposes

The API is a local read-only API that serves DuckDB data products as JSON responses. It exposes static planning views and, when available, GTFS-Realtime snapshot views.

## 2. Database used

- DuckDB path: `{resolved}`
- Tables available: `{len(tables)}`
- Views available: `{len(views)}`

## 3. Available static endpoints

{chr(10).join(f'- `{endpoint}`' for endpoint in static_endpoints)}

## 4. Available real-time snapshot endpoints

{chr(10).join(f'- `{endpoint}`' for endpoint in realtime_endpoints)}

Real-time endpoints are snapshot-based and return 404 when the serving database does not contain real-time snapshot views.

## 5. Example requests

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/metadata`
- `GET http://127.0.0.1:8000/static/top-routes?limit=5`
- `GET http://127.0.0.1:8000/static/hourly-headway?route_id=line:69&limit=10`
- `GET http://127.0.0.1:8000/realtime/feed-health`

FastAPI interactive documentation is available at `/docs` while the local server is running.

## 6. Example response snippets

### Top routes

{_sample(resolved, "v_top_routes_static", 3)}

### Real-time feed health

{_sample(resolved, "v_rt_feed_health", 1)}

### Real-time compatibility

{_sample(resolved, "v_rt_identifier_compatibility", 3)}

## 7. What this proves technically

The project can serve trusted local DuckDB data products through a read-only HTTP API. This prepares future consumers such as a dashboard, notebook, teacher demo, or later monitoring interface.

## 8. Current limitations

- This is not a production API.
- There is no authentication because the server is local-only and read-only in this phase.
- There is no dashboard yet.
- There is no streaming, database server, Docker, cloud service, or real-time monitoring system.

## 9. Next project step

Use this API as the backend contract for a later dashboard or demonstration interface.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"api_report_{_run_id_from_db_path(resolved)}.md"
    output.write_text(report, encoding="utf-8")
    return output

