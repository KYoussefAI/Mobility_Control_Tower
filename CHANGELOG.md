# Changelog

This changelog records delivered changes using semantic versioning.

## [Unreleased]

- Establish feature-branch review and basic Python/dbt CI.
- Add hardened realtime snapshot acquisition and analytics.
- Persist parsed observations in immutable partitioned historical Parquet storage.

## [0.1.0]

- Static analytical MVP with immutable GTFS Schedule ingestion, Raw/Bronze/Silver
  processing, dbt-owned Gold marts, DuckDB serving, FastAPI, and Streamlit.
