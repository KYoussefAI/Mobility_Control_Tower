# Local DuckDB serving layer

## What a serving layer is

A serving layer is the place where generated data products become easy to query. In this project, it means loading static gold KPIs and optional real-time snapshot KPIs into a local DuckDB file.

## Why CSV files alone are not ideal

CSV files are simple and transparent, but analysis across several CSV files quickly becomes inconvenient. SQL views make it easier to demonstrate the project, compare indicators, and answer teacher questions without manually opening many files.

## Why DuckDB is used locally

DuckDB is local and embedded. It does not require a database server, user accounts, networking, Docker, or cloud services. It works well with CSV files and is easy to run from Python.

## Tables and views

The serving database loads available static gold tables such as `route_daily_trips`, `network_daily_summary`, `route_period_summary`, and `route_hourly_headway`.

If a real-time snapshot gold run is provided, it also loads tables such as `rt_feed_health_snapshot`, `rt_route_delay_snapshot`, and `rt_identifier_compatibility_snapshot`.

Main SQL views include:

- `v_network_overview`;
- `v_top_routes_static`;
- `v_route_hourly_headway`;
- `v_route_type_daily_summary`;
- `v_rt_feed_health`;
- `v_rt_identifier_compatibility`;
- `v_rt_top_delayed_routes_snapshot`;
- `v_rt_top_delayed_stops_snapshot`.

## How this prepares future API or dashboard work

The serving layer gives future API or dashboard code a clear source to query. Instead of reading many CSV files directly, a later phase could query the same SQL views.

## Why PostgreSQL is not introduced yet

PostgreSQL would add server setup, administration, credentials, and deployment choices. DuckDB is enough for the current academic MVP because the goal is local SQL demonstration, not production database operations.
