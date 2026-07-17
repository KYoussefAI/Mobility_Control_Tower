# Project summary

## Title

Mobility Control Tower

## Objective

Build a local Data Engineering platform that processes public transport data and produces reliability-oriented evidence for an academic PFA demo.

## Data source

Tisseo Toulouse static GTFS and GTFS-Realtime snapshot feeds.

## Implemented components

- Static GTFS ingestion
- Raw, bronze, silver, gold layers
- Quality validation
- Static planning KPIs
- GTFS-Realtime snapshot parsing
- Static/live compatibility
- Realtime snapshot KPIs
- DuckDB serving database
- FastAPI read-only API
- Streamlit local dashboard
- Reports and documentation
- Automated tests

## Generated outputs

CSV tables, JSON manifests, Markdown reports, PNG charts, DuckDB database, API responses, and dashboard views.

## Technical skills demonstrated

Python, pandas, GTFS, GTFS-Realtime protobuf, data validation, layered data architecture, KPI design, DuckDB SQL, FastAPI, Streamlit, pytest, documentation.

## Current limitations

Realtime is snapshot-based, not streaming. The dashboard is local. No production deployment or authentication is included.

## Future work

Repeated snapshot collection, improved trip matching, richer visual analytics, and production architecture evaluation.

## Final status

Ready for academic demonstration.
