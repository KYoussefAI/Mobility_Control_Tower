# Teacher presentation notes

## Simple explanation

Mobility Control Tower is a local Data Engineering platform for public transport data. It transforms official transport files into validated tables, KPIs, reports, an API, and a dashboard.

## Public transport data

Public transport data describes stops, routes, trips, schedules, and sometimes live service updates.

## GTFS Schedule

GTFS Schedule is the planned offer: where stops are, which routes exist, and what trips are scheduled.

## GTFS-Realtime

GTFS-Realtime is operational data observed around fetch time. In this project it is handled as saved snapshots, not streaming.

## Pipeline

The pipeline preserves raw files, creates bronze copies, cleans silver tables, validates quality, computes gold KPIs, serves data through DuckDB and FastAPI, then displays a local dashboard.

## Why raw, bronze, silver, gold

- Raw: immutable source evidence.
- Bronze: extracted source files.
- Silver: cleaned canonical tables.
- Gold: analytical data products.

## Why DuckDB and FastAPI

DuckDB provides local SQL without a server. FastAPI exposes the trusted DuckDB views as bounded JSON endpoints for the dashboard and other local clients.

## Dashboard

The dashboard shows API health, static planning KPIs, GTFS-Realtime snapshot feed health, compatibility, and observed delay indicators.

## Implemented

Ingestion, validation, dbt-owned KPI computation, historical realtime snapshots, DuckDB serving, a bounded operator API, dashboard, incident lifecycle, Airflow orchestration, local containers, observability configuration, reports, and tests.

## Not implemented

No Kafka, Spark, Kubernetes, managed cloud platform, ML prediction, external identity provider, distributed edge rate limiter, certified production dispatch system, or continuous event-stream processing.

## Known limitations

Source-specific trip-matching evidence remains limited, and no production infrastructure has been evaluated or deployed.
