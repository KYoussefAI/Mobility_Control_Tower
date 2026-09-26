# Mobility Control Tower — Solo Rebuild Plan

## Goal and scope

Build a believable one-month Data Engineering portfolio project for one network: Tisséo in Toulouse. The project answers one question: **how does observed service compare with the published schedule, and how does reliability evolve over time?**

Only two public sources are in scope:

- GTFS Schedule (daily archive)
- GTFS-Realtime Trip Updates (scheduled polling)

Missing realtime updates remain unknown. They are never converted into cancellations or on-time observations.

## Final architecture

```text
Tisséo GTFS Schedule       Tisséo GTFS-RT Trip Updates
          |                              |
          +---------- Python ------------+
                         |
            immutable Raw + metadata
                         |
              normalized Silver Parquet
                         |
                   dbt + DuckDB
                         |
                  six Gold marts
                         |
             Streamlit (direct SQL reads)

Airflow: two small orchestration DAGs
Docker Compose: Airflow + dashboard
GitHub Actions: lint, unit tests, fixture dbt build
```

Python owns downloads, raw preservation, GTFS parsing, GTFS-RT protobuf parsing, Silver Parquet, and lightweight pre-dbt checks. dbt owns analytical joins, definitions, tests, and Gold marts. DuckDB stores dbt outputs. Streamlit is read-only and does not introduce an API layer.

## Concepts reused from the reference project

- Preserve source bytes before transforming them.
- Record source URL, UTC ingestion time, SHA-256 checksum, size, row counts, and feed header time where available.
- Keep static and realtime identifiers unchanged so compatibility can be measured.
- Partition historical realtime Parquet by collection date.
- Use arrival delay when present and departure delay as a documented fallback.
- Make feed freshness and realtime/static match coverage visible.
- Keep dbt authoritative for Gold analytics.
- Treat missing observations as unknown rather than as on-time service or cancellation evidence.

These are concepts, not copied subsystems. The new implementation uses a much smaller module and model surface.

## Deliberately removed

- Multi-city configuration and provider abstractions
- Vehicle Positions and Service Alerts
- FastAPI and all authentication, rate limiting, and mutation endpoints
- Incident detection, lifecycle, persistence, and operator workflows
- PostgreSQL application storage
- Prometheus, Grafana, and alerting infrastructure
- OpenLineage, S3 adapters, benchmarking, backup/restore, failure injection
- Reverse proxies, TLS, production Compose overlays, release-evidence automation
- Python-built Gold metrics and parallel KPI implementations
- Maintenance DAGs and broad command surfaces

## Proposed directory tree

```text
mct_solo/
├── PROJECT_PLAN.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── config/
│   └── source.yml
├── src/mct_solo/
│   ├── __init__.py
│   ├── config.py
│   ├── io.py
│   ├── static_pipeline.py
│   ├── realtime_pipeline.py
│   ├── quality.py
│   ├── dbt.py
│   └── cli.py
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/{staging,intermediate,marts}/
│   └── tests/
├── airflow/dags/
│   ├── static_gtfs_pipeline.py
│   └── realtime_pipeline.py
├── dashboard/app.py
├── scripts/create_ci_fixture.py
├── tests/
│   ├── fixtures/static/
│   ├── test_static_pipeline.py
│   ├── test_realtime_pipeline.py
│   └── test_quality.py
└── .github/workflows/ci.yml
```

Generated `data/`, dbt targets, local DuckDB files, Airflow logs, caches, and coverage output are ignored.

## Pipeline stages

### Static GTFS pipeline

1. Download the official GTFS ZIP with a timeout and HTTP validation.
2. Save the unchanged ZIP under `data/raw/static/<run_id>/`.
3. Write provenance metadata including URL, timestamp, SHA-256, byte size, and ZIP members.
4. Read required GTFS tables and normalize only types needed downstream.
5. Write `routes`, `trips`, `stops`, `stop_times`, `calendar`, and `calendar_dates` as Silver Parquet plus a manifest with row counts.
6. Run focused Python integrity checks.
7. Build and test dbt models in DuckDB.

### Realtime pipeline

1. Fetch one official GTFS-RT Trip Updates protobuf snapshot.
2. Derive an idempotent snapshot identifier from feed timestamp and content checksum.
3. Preserve the protobuf and provenance metadata under Raw.
4. Parse trip updates, stop-time updates, feed header time, schedule relationship, and delays.
5. Write append-only, date-partitioned Silver Parquet for snapshots, trip updates, and stop-time updates. A retry of the same snapshot does not append duplicate Silver rows.
6. Check delay sanity, required identifiers, feed age, and within-snapshot key uniqueness.
7. Rebuild/update dbt models and run dbt tests.

This is scheduled polling, not event streaming.

## dbt models

### Staging

- `stg_routes`: route names and type
- `stg_trips`: trip, route, service, and direction identifiers
- `stg_stop_times`: stop sequence and parsed scheduled time seconds
- `stg_calendar`: regular weekday service windows
- `stg_calendar_dates`: added/removed service exceptions
- `stg_realtime_updates`: normalized stop-time delay observations
- `stg_feed_snapshots`: collection and feed freshness metadata

### Intermediate

- `int_service_dates`: expands regular calendars and applies exceptions
- `int_scheduled_trips`: scheduled trips by route and service date
- `int_delay_observations`: deduplicated realtime observations matched to static trips and scheduled stop times

### Gold marts

- `route_daily_service`: scheduled trips and departures by route/day
- `route_delay_summary`: observed delay distribution and on-time percentage by route/day
- `hourly_delay_summary`: observed delays by scheduled service hour/day
- `network_on_time_performance`: daily network OTP over known delay observations
- `realtime_coverage`: observed matched trips divided by eligible scheduled trips by day
- `feed_freshness`: per-snapshot feed age and a documented freshness status

The on-time definition is delay between **-60 and +300 seconds inclusive**. Delay is arrival delay when available, otherwise departure delay. Percentages use only eligible known observations. Coverage is reported separately.

## Airflow DAGs

1. `static_gtfs_pipeline` (daily): download/preserve → transform to Silver → Python quality checks → dbt build/test.
2. `realtime_pipeline` (every five minutes): fetch/preserve/parse one snapshot → realtime quality checks → dbt build/test against the latest static Silver run.

No maintenance or platform-management DAGs are planned.

## Test strategy

- Unit tests build tiny deterministic GTFS ZIPs and GTFS-RT protobufs.
- Static tests verify raw immutability metadata, time parsing including values after 24:00, Silver schemas, and relationship failures.
- Realtime tests verify protobuf parsing, arrival/departure delay fallback inputs, freshness metadata, and idempotent writes.
- Quality tests cover identifier relationships, delay sanity bounds, and duplicate keys.
- dbt schema tests cover not-null, unique, relationships, and accepted values.
- Custom dbt assertions cover percentage bounds, delay bounds, coverage reconciliation, and the rule that unobserved service is not counted as on-time.
- CI creates deterministic Parquet fixtures and executes a real `dbt build`; fixture success is identified as CI evidence, not real-data evidence.
- Development includes separate real-source smoke commands. Any command not executed or component not available is reported as unverified.

## Dashboard scope

One Streamlit app with three pages:

1. **Network Overview** — scheduled service, known observations, network OTP, and hourly delay trend.
2. **Route Reliability** — route/date filter, delay distribution summary, observed sample size, and low-coverage warning.
3. **Data Quality / Feed Health** — feed age trend, latest freshness, match coverage, and explicit explanation of unknown observations.

The dashboard queries trusted dbt tables directly from DuckDB and performs no KPI recomputation.

## Implementation phases

1. **Scope and foundation** — plan, packaging, configuration, paths, CLI, ignores.
2. **Static pipeline** — raw preservation, Silver conversion, metadata, unit tests.
3. **Realtime history** — polling snapshot, protobuf parser, idempotent Parquet append, unit tests.
4. **Analytics engineering** — compact dbt graph, KPI definitions, schema/custom tests, deterministic fixture build.
5. **Presentation and orchestration** — three-page dashboard, two Airflow DAGs, Docker Compose.
6. **Evidence and documentation** — real-data smoke test where reachable, broad validation, README with honest limitations.

## Final acceptance criteria

- All authored files are inside `mct_solo/`; the reference project is unchanged.
- Exactly one network and two source feeds are configured.
- Raw GTFS and GTFS-RT bytes are retained with provenance and checksums.
- Static and realtime Silver data are Parquet and inspectable.
- A repeated realtime retry cannot duplicate a Silver snapshot.
- Six compact, documented dbt Gold marts answer the stated analytical question.
- dbt and Python checks keep unknown realtime observations out of OTP and cancellation claims.
- Two DAGs cover only the important static and realtime workflows.
- The dashboard has no more than three pages and reads DuckDB directly.
- Docker Compose documents reproducible local startup.
- One CI workflow runs lint, pytest, and a deterministic dbt build/test.
- A real Tisséo smoke test is attempted and its actual outcome is documented without conflating it with fixtures.
- README explains the problem, architecture, sources, KPI definitions, setup, example queries, limitations, and sensible future work.
- The project stays close to 30–60 meaningful files and remains explainable by a junior Data Engineer.

## Reference audit note

The requested `33.md` was not present in the repository at planning time. The existing source tree, its focused GTFS/GTFS-RT modules, documentation, dbt graph, and the large `Mobility_Control_Tower.md` project-history document were inspected as reference material. This absence does not change the deliberately smaller target scope.
