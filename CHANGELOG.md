# Changelog

This changelog records delivered changes using semantic versioning.

## [Unreleased]

- Add durable incident lifecycle and persistence.
- Protect operator mutations with scoped, expiring bearer tokens.
- Add deterministic process-local rate limiting and security edge-case tests.
- Add a health-checked local Docker Compose runtime.

## [0.3.0]

- Add delay, coverage, on-time-performance, cancellation, headway, and excess-waiting models.
- Add reconciliation tests, watermarks, incremental idempotency, and Airflow orchestration.

## [0.2.0]

- Add immutable GTFS-Realtime acquisition, hardened parsing, and static matching.
- Add snapshot KPIs, immutable historical Parquet storage, and dbt historical trend marts.
- Add historical quality contracts, serving views, API reads, and dashboard panels.

## [0.1.0]

- Static analytical MVP with immutable GTFS Schedule ingestion, Raw/Bronze/Silver
  processing, dbt-owned Gold marts, DuckDB serving, FastAPI, and Streamlit.
