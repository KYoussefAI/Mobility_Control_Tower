# Mobility Control Tower Portfolio Case Study

## Problem

Public transport data is often available as GTFS schedules and GTFS-Realtime feeds, but raw files alone do not answer operational questions. The project turns open mobility feeds into validated, queryable, historical analytics.

## Architecture

The platform uses Python ETL for ingestion and Silver creation, dbt for analytical marts, Great Expectations for validation, DuckDB for serving, FastAPI for read-only access, Streamlit for exploration, Airflow for orchestration, and optional S3-compatible storage abstraction for cloud readiness.

## Engineering Decisions

- DuckDB keeps analytical serving simple and local.
- Parquet is used for historical GTFS-Realtime because it is columnar, compressed, and queryable by DuckDB.
- Airflow calls the CLI instead of duplicating business logic.
- dbt starts after Silver so ingestion and parsing stay in Python.
- Great Expectations validates data contracts without replacing transformation code.
- Docker Compose makes the platform reproducible for review.

## Tradeoffs

- Local DuckDB is not a multi-user warehouse.
- Scheduled polling is simpler than Kafka but not true streaming.
- The S3 implementation is an abstraction, not an AWS deployment.
- Coverage is improved honestly rather than by excluding difficult modules.

## Challenges

- Preserving historical snapshots without overwrites.
- Keeping CLI, Airflow, Docker, and tests aligned.
- Maintaining compatibility while adding versioned API paths.
- Avoiding hardcoded Tisseo assumptions by adding Rennes STAR config.

## Lessons Learned

- A stable CLI contract is valuable for orchestration and testing.
- Medallion boundaries make evolution easier.
- Observability and validation should be added as first-class layers, not afterthoughts.

## Future Improvements

- Native S3 integration in every writer.
- Authentication and rate limiting for API.
- More city feeds and automated city-level comparison.
- Real Grafana/Prometheus Compose profile.
- Higher coverage for CLI and dashboard branches.

