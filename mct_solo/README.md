# Mobility Control Tower

A compact, local-first Data Engineering portfolio project that compares Tisséo’s planned public transport service in Toulouse with observations from scheduled GTFS-Realtime Trip Updates polling.

This project is intentionally sized for a Master’s student or junior Data Engineer. It demonstrates source ingestion, immutable raw storage, typed Parquet, analytics engineering with dbt, orchestration, data quality, and a small dashboard without presenting itself as an enterprise platform.

## Business question

> How does observed public transport service compare with the planned schedule, and how does reliability evolve over time?

The analytical contract is conservative: a trip without a realtime observation is **unknown**. It is not assumed cancelled and is not counted as on-time.

## Architecture

```text
Official Tisséo GTFS Schedule      GTFS-RT Trip Updates
               |                           |
               +-------- Python -----------+
                            |
                Raw bytes + provenance
                            |
          Bronze extraction / Silver Parquet
                            |
                      dbt + DuckDB
                            |
                     six Gold marts
                            |
                 three-page Streamlit app

        Airflow schedules two workflows locally
```

Python owns source collection and normalization. dbt owns all analytical KPI logic. Streamlit reads trusted dbt tables directly from DuckDB, so there is no API layer or second KPI implementation.

## Real public sources

- Dataset page: [Tisséo — Réseau transport urbain toulousain](https://transport.data.gouv.fr/datasets/tisseo-reseau-transport-urbain-toulousain)
- GTFS Schedule: configured official Toulouse Métropole download URL
- GTFS-Realtime Trip Updates: `https://api.tisseo.fr/opendata/gtfsrt/GtfsRt.pb`
- Licence recorded from the source: ODbL

The URLs and freshness thresholds live in `config/source.yml`. Only Tisséo is supported. Vehicle Positions and Service Alerts are deliberately out of scope.

## Pipeline

The daily static workflow downloads the ZIP, saves it unchanged with a SHA-256 checksum, extracts selected GTFS text files into Bronze, writes six typed Silver Parquet tables, checks identifiers and relationships, then runs dbt.

The five-minute realtime workflow fetches one protobuf snapshot, saves the original bytes and metadata, parses Trip Updates into partitioned Silver Parquet, checks keys and published delays, then refreshes dbt. Snapshot IDs combine the publisher header timestamp and content checksum, so a retry of identical content does not append duplicate Silver rows.

Each raw metadata file records the source URL, UTC ingestion time, checksum, byte size, HTTP metadata, feed timestamp where applicable, and row counts. Generated data is stored under `data/` and ignored by Git.

## Gold marts and KPI definitions

| Mart | Grain and definition |
| --- | --- |
| `route_daily_service` | Route/service date; distinct scheduled trips and scheduled stop departures. |
| `route_delay_summary` | Route/service date; distribution and on-time share over matched stop updates with a valid known delay, plus `sample_size_status`. |
| `hourly_delay_summary` | Service date/scheduled hour; delay and on-time trend plus `sample_size_status`. Times after 24:00 wrap to clock hour while staying on their GTFS service date. |
| `network_on_time_performance` | Service date; on-time observations divided by matched observations with a valid known delay. |
| `realtime_coverage` | Service date; distinct matched observed trips divided by eligible scheduled trips on a date with at least one collected snapshot. |
| `feed_freshness` | Snapshot; collection time minus the publisher’s feed-header timestamp. |

An observation is on-time when its delay is between **−60 and +300 seconds inclusive**. Arrival delay is preferred; departure delay is used only when arrival delay is absent. Published delay values outside ±7,200 seconds are preserved and flagged `OUT_OF_RANGE`, but excluded from reliability KPIs. Rows without delay remain `MISSING`. Neither category enters the OTP denominator.

Coverage and OTP answer different questions. Low coverage makes an OTP estimate less representative, which is why both are shown rather than filling missing values.

Route-day and hourly rows are marked `RELIABLE` when they contain at least `min_reliable_sample_size` observations
(5 by default); smaller groups remain visible and are marked `LOW_SAMPLE`. The dashboard warns about these rows rather
than hiding them.

## Data quality

Python checks the file-level and parsing boundary:

- required GTFS files and identifiers;
- unique route, trip, stop, and stop-sequence keys;
- trip-to-route and stop-time relationships;
- GTFS time syntax, including service times after 24:00;
- unique realtime entity/stop keys;
- delay sanity with explicit warnings for preserved outliers.

dbt adds `not_null`, `unique`, `relationships`, and `accepted_values` tests plus business assertions for percentage bounds, coverage reconciliation, delay eligibility, and OTP numerator/denominator reconciliation.

## Local setup

Python 3.11 is the supported local version.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev,analytics]"
```

Run the static workflow, collect several realtime snapshots over time, and refresh analytics:

```bash
mct static-pipeline
mct collect-realtime
mct dbt-build
```

For one full realtime poll including checks and dbt:

```bash
mct realtime-pipeline
```

Launch the dashboard after a dbt build:

```bash
streamlit run dashboard/app.py
```

Local URLs under Docker Compose are Streamlit at `http://localhost:8501` and Airflow at `http://localhost:8080` (`airflow` / `airflow` for local use).

## Deterministic development and CI

Fixture evidence is intentionally separate from live-source evidence:

```bash
python scripts/create_ci_fixture.py data/ci
mct --data-root data/ci dbt-build \
  --static-run data/ci/silver/static/20260101T120000000000Z
```

The one GitHub Actions workflow runs Ruff, Black, isort, MyPy, pytest with an 80% coverage floor, a real dbt build/test over generated deterministic Parquet fixtures, and a Docker image build. The nested `.github/workflows/ci.yml` is intended to move with `mct_solo/` when this independent project becomes its own repository root.

## Airflow and Docker Compose

There are exactly two DAGs:

- `static_gtfs_pipeline`: preserve → Silver → quality → dbt build/test
- `realtime_pipeline`: fetch/parse/append → quality → dbt build/test

Start the local environment with:

```bash
cp .env.example .env
docker compose up --build -d
```

Airflow uses SQLite and the SequentialExecutor inherited from its local default. That choice keeps the portfolio environment understandable; it is not a high-availability deployment design. The scheduler, webserver, and dashboard share the ignored local `data/` volume.

## Dashboard

The Streamlit app has three pages only:

1. **Network Overview** — scheduled service, known observations, network OTP, and hourly delay.
2. **Route Reliability** — route-level sample size, median/P90 delay, and on-time trend.
3. **Data Quality / Feed Health** — freshness history, realtime coverage, and unknown-status explanation.

The app displays empty-state messages when no eligible delay observations exist rather than inventing zero-valued performance.

## Real-data smoke evidence

A live smoke run was executed on **2026-09-23** against both configured Tisséo URLs:

- Static Raw → Bronze → Silver and Python checks completed.
- Static Silver contained 124 routes, 40,427 trips, 5,721 stops, and 902,869 stop-time rows.
- Two Trip Updates snapshots were fetched and parsed with feed ages of 4 and 2 seconds.
- The real-data dbt build completed successfully: 16 models and 38 tests, 54 operations total.
- Realtime/static coverage for the sampled service date was 32 matched trips out of 12,902 scheduled trips (0.25%).
- The two late-evening snapshots published no delay value eligible under the ±7,200-second sanity rule: 844 populated delays were approximately one day negative and were flagged `OUT_OF_RANGE`; 849 observations had no delay. Network OTP therefore correctly remained unknown/empty.

This is a short smoke test, not evidence of representative network reliability. It demonstrates that the real source can be collected, preserved, normalized, joined, tested, and served while invalid or absent observations remain explicit.

## Example analytical queries

```sql
-- Daily network reliability over eligible observations only
select *
from network_on_time_performance
order by service_date desc;

-- Routes with the worst observed P90 delay, keeping sample size visible
select route_short_name, observed_trips, p90_delay_seconds, on_time_percentage
from route_delay_summary
where service_date = current_date
order by p90_delay_seconds desc;

-- Coverage: unknown trips are explicit, not classified as on-time/cancelled
select service_date, eligible_scheduled_trips, observed_matched_trips,
       trips_with_unknown_status, coverage_percentage
from realtime_coverage
order by service_date desc;
```

## Limitations

- GTFS-RT is polled, not streamed. Results depend on poll cadence and collection duration.
- Trip Updates describe predictions/updates, not independently measured passenger arrivals.
- Tisséo’s sampled Trip Updates omitted `start_date` and showed low static trip-ID compatibility.
- In the 2026-09-23 smoke sample, 32 of 210 distinct realtime `trip_id` values matched the static feed exactly;
  178 did not. Realtime IDs such as `10:A:2`, `10:R:4`, and `11:A:1` were absent from `stg_trips`, while
  static trips on the same `line:204` route used IDs such as `2281803`. Exact-ID matching is retained
  intentionally instead of using a heuristic that could silently assign updates to the wrong scheduled trip.
- When `start_date` is absent, the fallback uses the Europe/Paris observation date; this remains approximate because wall-clock observation time does not identify the trip’s actual scheduled service day.
- Source-published delay anomalies are excluded rather than guessed or silently corrected.
- OTP is observation-weighted, not passenger-weighted, and should be read alongside coverage.
- DuckDB and SQLite-backed local Airflow are appropriate for this portfolio scope, not concurrent production workloads.
- The dashboard and Docker Compose were designed for local demonstration; availability, authentication, and TLS are out of scope.

## Sensible future improvements

- Collect daytime and peak-period snapshots for several weeks before interpreting reliability trends.
- Investigate Tisséo trip-ID and service-day semantics with source documentation and retain any reconciliation rule as a tested, source-specific transformation.
- Add a small retention policy only if local history growth becomes a practical issue.
- Move this folder to its own repository so its included GitHub Actions workflow runs natively.

The detailed implementation boundary and acceptance criteria are in [PROJECT_PLAN.md](PROJECT_PLAN.md).
