# Local DuckDB serving layer

## What a serving layer is

A serving layer is the place where generated data products become easy to query. In this project, it means publishing a validated, run-scoped DuckDB artifact built from dbt-produced Gold outputs and optional historical Parquet views.

## Why CSV files alone are not ideal

CSV files are simple and transparent, but analysis across several CSV files quickly becomes inconvenient. SQL views make it easier to demonstrate the project, compare indicators, and answer teacher questions without manually opening many files.

## Why DuckDB is used locally

DuckDB is local and embedded. It does not require a database server, user accounts, networking, Docker, or cloud services for analytical serving. It works well with dbt-produced tables and Parquet-backed historical views.

## Current pointer contract

Consumers normally do not hardcode a timestamped database path. They resolve:

```text
data/serving/<source>/current.json
data/serving/<source>/runs/<serving_run_id>/mobility_control_tower.duckdb
data/serving/<source>/runs/<serving_run_id>/serving_manifest.json
```

`current.json` records source, serving run id, database path, dbt Gold run id, quality status, generated timestamp, and contract version.

## Atomic publication

Serving publication follows this order:

1. Build in `data/serving/<source>/runs/.<serving_run_id>.tmp`.
2. Validate the database opens.
3. Validate required public views and smoke queries.
4. Write `serving_manifest.json`.
5. Rename the temp directory to `runs/<serving_run_id>`.
6. Atomically replace `current.json`.

Failed builds never replace `current.json`, so the API continues to read the last known-good artifact.

## Tables and views

The serving database loads available static gold tables such as `route_daily_trips`, `network_daily_summary`, `route_period_summary`, and `route_hourly_headway`.

If a real-time snapshot gold run is provided, it also loads tables such as `rt_feed_health_snapshot`, `rt_route_delay_snapshot`, and `rt_identifier_compatibility_snapshot`.

Authoritative reliability views are thin DuckDB views over dbt-produced marts.
They are not recalculated in Python or inside the serving layer:

- `v_network_reliability`;
- `v_network_reliability_summary`;
- `v_route_reliability`;
- `v_route_on_time_performance`;
- `v_route_delay_distribution`;
- `v_realtime_trip_coverage`;
- `v_explicit_cancellations`;
- `v_observed_headways`;
- `v_headway_reliability_events`;
- `v_headway_reliability`;
- `v_excess_waiting_time`;
- `v_reliability_incident_snapshot`.

Other SQL views include:

- `v_network_overview`;
- `v_top_routes_static`;
- `v_route_hourly_headway`;
- `v_route_type_daily_summary`;
- `v_rt_feed_health`;
- `v_rt_identifier_compatibility`;
- `v_rt_top_delayed_routes_snapshot`;
- `v_rt_top_delayed_stops_snapshot`.

Serving publication validates required reliability views. If a required dbt
reliability relation is missing, publication fails before `current.json` is
updated and the previous serving artifact remains current.

## How this prepares future API or dashboard work

The serving layer gives future API or dashboard code a clear source to query. Instead of reading many CSV files directly, a later phase could query the same SQL views.

## Why PostgreSQL is not introduced yet

Compose uses PostgreSQL for Airflow metadata. DuckDB remains the analytical serving artifact because it is the dbt-produced local Gold contract consumed by API and dashboard.
