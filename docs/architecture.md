# Architecture

## Data flow

Mobility Control Tower has two source paths that converge in Silver Parquet and dbt:

```text
Tisséo GTFS ZIP                         Tisséo GTFS-RT TripUpdates
      |                                             |
      v                                             v
Raw ZIP + metadata                         Raw protobuf + metadata
      |                                             |
      v                                             v
Bronze selected text                    Silver partitioned Parquet
      |                                             |
      v                                             |
Silver typed Parquet --------------------------------+
                          |
                          v
              dbt staging → intermediate → marts
                          |
                          v
                        DuckDB
                          |
                          v
                       Streamlit
```

## Component responsibilities

Python owns network calls, exact source-payload preservation, provenance metadata, GTFS and GTFS-Realtime parsing, typed Parquet output, and validation that runs before analytics. Static inputs are immutable per run. Realtime payloads are partitioned by collection date and snapshot identifier; identical retries are idempotent.

dbt owns service-date expansion, schedule and realtime joins, observation eligibility, metric definitions, six analytical marts, and analytical tests.

DuckDB is the dbt target and the read-only data source for Streamlit. Streamlit queries the marts directly.

Airflow owns schedules and task dependencies. Its DAGs call the package's pipeline, validation, and dbt functions.

## Layer responsibilities

- **Raw:** exact downloaded bytes, source metadata, checksum, timestamps, and completion marker.
- **Bronze:** selected GTFS text files extracted from the static archive.
- **Silver:** normalized, typed Parquet datasets for schedule and realtime records.
- **dbt staging:** column selection, casting, and null normalization.
- **dbt intermediate:** reusable service-date expansion and schedule/realtime reconciliation.
- **dbt marts:** route service, delay, on-time performance, coverage, and feed-health tables.

## Realtime semantics

Airflow collects GTFS-Realtime TripUpdates every five minutes. Coverage depends on collection cadence and exact trip-identifier compatibility. A missing realtime match remains `UNKNOWN` and does not imply cancellation, punctuality, or delay.

Arrival delay is used when present; departure delay is the fallback. Delays outside ±7,200 seconds are retained as `OUT_OF_RANGE` but excluded from on-time performance and delay distributions. When a TripUpdate omits `start_date`, the Europe/Paris observation date provides the service-date fallback.

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

dbt tests cover model keys and relationships, accepted statuses, percentage ranges, delay eligibility, observation reconciliation, coverage reconciliation, and sample-size classification. dbt failures propagate to the caller.

## Local runtime

Docker Compose runs Airflow initialization, webserver, scheduler, and Streamlit services. All services share the `data/` volume. Airflow stores its local state in SQLite, dbt writes marts to DuckDB, and Streamlit opens that DuckDB database read-only.

Schema-only realtime Parquet files allow a static-data dbt build before the first realtime snapshot, with empty realtime analytical results.
