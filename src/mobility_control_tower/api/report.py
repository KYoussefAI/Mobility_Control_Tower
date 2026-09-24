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
        "GET /v1/static/network-overview",
        "GET /v1/static/top-routes",
        "GET /v1/static/hourly-headway",
        "GET /v1/static/route-types",
    ]
    realtime_endpoints = [
        "GET /v1/realtime/feed-health",
        "GET /v1/realtime/compatibility",
        "GET /v1/realtime/top-delayed-routes",
        "GET /v1/realtime/top-delayed-stops",
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

- `GET http://127.0.0.1:8000/v1/health`
- `GET http://127.0.0.1:8000/v1/metadata`
- `GET http://127.0.0.1:8000/v1/static/top-routes?limit=5`
- `GET http://127.0.0.1:8000/v1/static/hourly-headway?route_id=line:69&limit=10`
- `GET http://127.0.0.1:8000/v1/realtime/feed-health`

FastAPI interactive documentation is available at `/docs` while the local server is running.

## 6. Example response snippets

### Top routes

{_sample(resolved, "v_top_routes_static", 3)}

### Real-time feed health

{_sample(resolved, "v_rt_feed_health", 1)}

### Real-time compatibility

{_sample(resolved, "v_rt_identifier_compatibility", 3)}

## 7. What this proves technically

The project serves trusted local DuckDB data products through bounded HTTP reads. The Streamlit dashboard consumes this API, while scoped incident endpoints support audited operator actions.

## 8. Current limitations

- This is not a production API.
- Analytical reads are public in the local profile; incident reads and mutations use expiring scoped bearer tokens.
- Realtime data comes from scheduled polling and committed snapshots, not event streaming.
- Docker, Prometheus, Grafana, Airflow, and PostgreSQL are configured, but their runtime behavior requires the separate Docker verification pass.
- Optional S3 storage is an adapter capability, not evidence of a cloud deployment.

## 9. Next project step

Use `/v1` as the canonical contract. Unversioned read routes are compatibility-only; unversioned mutations are not exposed.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"api_report_{_run_id_from_db_path(resolved)}.md"
    output.write_text(report, encoding="utf-8")
    return output
