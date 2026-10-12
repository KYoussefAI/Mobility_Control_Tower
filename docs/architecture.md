# Architecture

## Data flow

Mobility Control Tower has two source paths that converge in typed Silver Parquet before dbt builds the analytical layer:

```text
Tisséo GTFS ZIP                         Tisséo GTFS-RT TripUpdates
      │                                             │
      ▼                                             ▼
Raw ZIP + metadata                         Raw protobuf + metadata
      │                                             │
      ▼                                             ▼
Bronze selected text                    Silver partitioned Parquet
      │                                             │
      ▼                                             │
Silver typed Parquet ───────────────────────────────┘
                          │
                          ▼
              dbt staging → intermediate → marts
                          │
                          ▼
                        DuckDB
                          │
                          ▼
                       Streamlit
```

## Component responsibilities

Python owns network calls, exact source-payload preservation, provenance metadata, GTFS and GTFS-Realtime parsing, typed Parquet output, and validation before analytics. Static inputs are immutable per run. Realtime payloads are partitioned by collection date and snapshot identifier; identical retries are idempotent.

dbt owns service-date expansion, date-aware schedule/realtime reconciliation, source-quality classification, canonical observation selection, metric definitions, seven analytical marts, and analytical tests.

DuckDB is the dbt target and Streamlit's read-only data source. Streamlit queries only analytical marts. Airflow owns schedules and task dependencies and calls the package's pipeline, validation, and dbt functions.

## Layer responsibilities

- **Raw:** exact downloaded bytes, source metadata, checksum, timestamps, and completion marker.
- **Bronze:** selected GTFS text files extracted from the static archive.
- **Silver:** normalized, typed Parquet datasets that preserve schedule and realtime source records.
- **dbt staging:** column selection, casting, and null normalization.
- **dbt intermediate:** service-date expansion, source-key classification, exact-duplicate collapse, date-aware schedule matching, and canonical trip-stop selection.
- **dbt marts:** route service, route and hourly delay, network on-time performance, realtime coverage, feed health, and rebuild coverage metadata.

The dbt project contains 8 staging models, 4 intermediate models, and 7 marts. See [Data Model](data_model.md) for their grains and contracts.

## Canonical realtime path

Airflow polls TripUpdates every five minutes. Because the same trip-stop can appear in many snapshots, poll-level updates are unsuitable as independent KPI observations.

`int_delay_observations` groups the source key `(snapshot_id, entity_id, stop_sequence)`. Exact analytical duplicates collapse into one row. Conflicting variants are marked `AMBIGUOUS_SOURCE`; delays are separately classified as valid, missing, or outside the ±7,200-second sanity bound.

`int_trip_stop_observations` is the canonical KPI source. It:

1. accepts only unambiguous observations with known, in-range delays;
2. matches `trip_id` to a scheduled trip on the same service date;
3. verifies the route when supplied and the scheduled stop sequence and stop identifier when supplied; and
4. retains the latest effective publication for each `(service_date, trip_id, stop_sequence)`.

The effective publication uses the update timestamp, with collection time as its fallback. The result represents the latest published GTFS-Realtime state, not verified physical arrival.

## Schedule compatibility and unknowns

Schedule matching is deliberately date-aware. A trip identifier that exists elsewhere in the GTFS archive does not make a realtime record eligible on a different service date. Realtime dates outside the selected static archive's validity window remain available for feed-health analysis but do not produce schedule-comparison metrics.

A scheduled trip without a canonical realtime match remains `UNKNOWN`. No cancellation, on-time, or delayed outcome is inferred from absence.

## Orchestration

`static_gtfs_pipeline` runs daily at 03:00 UTC:

```text
download_and_preserve → build_silver → quality_checks → dbt_build
```

`realtime_pipeline` runs every five minutes:

```text
fetch_parse_and_append → quality_checks → dbt_build
```

Both DAGs use `max_active_runs=1` and disable catchup.

## Quality boundaries

Python validation covers archive shape, required identifiers, primary-key uniqueness, static relationships, realtime lineage, duplicate observations, and delay sanity warnings. Failures stop the workflow before dbt runs.

The dbt project contains 57 data tests and 9 unit tests. These cover model keys and relationships, accepted statuses, percentage ranges, delay eligibility, canonical uniqueness, date compatibility, observation and coverage reconciliation, and sample-size classification. dbt failures propagate to the caller.

## Local analytical runtime

Accumulated history makes repeated full-Parquet scans expensive. The source-key and canonical trip-stop intermediates are therefore materialized as DuckDB tables and reused by downstream marts. Local dbt execution uses one thread, a 2 GB DuckDB memory limit, insertion-order preservation disabled, and a configured temporary directory for disk spilling.

Docker Compose runs Airflow initialization, webserver, scheduler, and Streamlit services against a shared `data/` volume. Airflow stores local state in SQLite, dbt writes marts to DuckDB, and Streamlit opens that database read-only.

Schema-only realtime Parquet files allow a static-data dbt build before the first realtime snapshot, with empty realtime analytical results.
