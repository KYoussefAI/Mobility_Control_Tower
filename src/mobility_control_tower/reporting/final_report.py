"""Generate the final academic MVP report."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb


def _table(rows: list[dict]) -> str:
    if not rows:
        return "No rows available."
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")).replace("|", "\\|") for header in headers) + " |")
    return "\n".join(lines)


def _query(db_path: Path, sql: str) -> list[dict]:
    if not db_path.is_file():
        return []
    with duckdb.connect(str(db_path), read_only=True) as connection:
        try:
            return connection.execute(sql).fetchdf().where(lambda frame: frame.notna(), None).to_dict("records")
        except duckdb.Error:
            return []


def generate_final_report(serving_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not serving_run.is_dir():
        raise FileNotFoundError(f"Serving run directory not found: {serving_run}")
    manifest_path = serving_run / "serving_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Serving manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    db_path = Path(manifest["database_path"])
    static_tables = sorted(name for name in manifest.get("tables_loaded", {}) if not name.startswith("rt_"))
    realtime_tables = sorted(name for name in manifest.get("tables_loaded", {}) if name.startswith("rt_"))
    top_routes = _query(db_path, "SELECT route_short_name, route_long_name, total_scheduled_trips FROM v_top_routes_static LIMIT 5")
    feed_health = _query(db_path, "SELECT feed_type, feed_age_seconds, freshness_status, entity_count FROM v_rt_feed_health")
    compatibility = _query(db_path, "SELECT identifier_type, match_percentage, status FROM v_rt_identifier_compatibility")
    report = f"""# Mobility Control Tower - Final Project Report

## 1. Project objective

Mobility Control Tower is a local Data Engineering platform that processes public transport data and produces explainable indicators for an academic PFA demonstration.

## 2. Data source

The project uses Tisseo Toulouse static GTFS and bounded GTFS-Realtime snapshots from official public transport data sources.

## 3. Static pipeline

Static GTFS is preserved as raw data, extracted to bronze, cleaned into silver tables, validated, and aggregated into gold static planning KPIs.

## 4. Realtime snapshot pipeline

One GTFS-Realtime snapshot is preserved as `feed.pb`, parsed into CSV tables, compared with static GTFS identifiers, and summarized as snapshot delay indicators.

## 5. Data quality

The project includes static GTFS quality checks and static/live compatibility checks. Reports are generated as Markdown and JSON artifacts.

## 6. Static KPIs

Loaded static gold tables: `{len(static_tables)}`.

Top routes over the static service period:

{_table(top_routes)}

## 7. Realtime snapshot KPIs

Loaded realtime snapshot tables: `{len(realtime_tables)}`.

Feed health:

{_table(feed_health)}

Identifier compatibility:

{_table(compatibility)}

## 8. Serving layer

The local DuckDB serving layer packages generated CSV data products into SQL tables and views for predefined queries.

## 9. API layer

The FastAPI layer exposes DuckDB views through a local read-only API. It serves DuckDB data products and does not expose arbitrary SQL.

## 10. Dashboard layer

The Streamlit dashboard consumes the local API and presents static planning KPIs plus GTFS-Realtime snapshot indicators for a teacher demo.

## 11. Technical skills demonstrated

- Data ingestion and raw preservation
- Metadata and checksums
- Layered transformations: raw, bronze, silver, gold
- Data-quality validation
- KPI design
- GTFS-Realtime protobuf parsing
- Static/live compatibility analysis
- DuckDB serving
- FastAPI read-only API
- Streamlit local dashboard
- Automated pytest coverage
- Teacher-facing documentation

## 12. Limitations

- This is a local academic MVP, not an enterprise platform.
- Realtime work is snapshot-based, not streaming.
- No production monitoring system is implemented.
- No authentication, deployment, cloud, Docker, Kafka, Spark, Airflow, PostgreSQL, ML, or RAG is included.

## 13. Future work

- Collect repeated GTFS-Realtime snapshots.
- Improve trip-level matching.
- Add a richer dashboard after the API contract is stable.
- Evaluate production storage only after academic MVP validation.

## 14. Final academic MVP status

The project is ready for a local academic demonstration.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"final_project_report_{serving_run.name}.md"
    output.write_text(report, encoding="utf-8")
    return output

