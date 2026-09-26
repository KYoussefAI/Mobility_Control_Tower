# Project summary

## Title

Mobility Control Tower

## Objective

Build a local Data Engineering platform that processes public transport data and produces reliability-oriented evidence for an academic PFA demo.

## Data source

Tisseo Toulouse and STAR Rennes source configurations for static GTFS and GTFS-Realtime snapshot feeds.

## Implemented components

- Static GTFS ingestion
- Raw, Bronze, Silver, and dbt-owned Gold layers
- Mandatory MCT quality contracts
- Static planning KPIs
- GTFS-Realtime snapshot parsing
- Static/live compatibility
- Realtime snapshot KPIs
- DuckDB serving database
- FastAPI API with bounded reads and scoped incident operations
- Process-local rate limiting for authenticated operator mutations
- Streamlit local dashboard
- Airflow DAGs for thin CLI orchestration
- Prometheus/Grafana configuration and incident observability
- SQLite/PostgreSQL incident repository adapters
- Reports and documentation
- Automated tests

## Generated outputs

CSV tables, JSON manifests, Markdown reports, PNG charts, DuckDB database, API responses, and dashboard views.

## Technical skills demonstrated

Python, pandas, GTFS, GTFS-Realtime protobuf, dbt, data validation, layered data architecture, KPI design, DuckDB SQL, FastAPI, Streamlit, Airflow orchestration, scoped authentication, pytest, and documentation.

## Current limitations

Realtime is polling/snapshot-based, not event streaming. The dashboard is local. Scoped bearer authentication and a process-local limiter protect incident operations; neither is an external identity or distributed edge system. S3 is an optional storage adapter, not proof of cloud deployment. Docker/PostgreSQL/Prometheus/Grafana evidence comes from the release-proof workflow rather than an availability claim.

## Known gaps

Source-specific trip-matching evidence remains limited, and the repository does not demonstrate a production deployment architecture.

## Final status

Ready for academic demonstration.
