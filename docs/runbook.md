# Mobility Control Tower Runbook

Operational guide for the local-first Mobility Control Tower platform.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,quality,analytics,orchestration]'
pytest
```

Run all commands from the repository root.

## One-Command Deterministic Demo

```bash
cp .env.example .env
make demo
make demo-smoke
```

The demo does not fetch live feeds. It creates deterministic Silver and historical fixtures, runs real dbt and MCT Quality Contracts, publishes DuckDB through `data/serving/tisseo/current.json`, and starts API, dashboard, PostgreSQL-backed Airflow, Prometheus, Grafana, and the MCT metrics exporter.

Use `make doctor` for non-mutating local diagnostics and `make demo-reset` for a full local reset.

## Static Workflow

```bash
python -m mobility_control_tower.cli ingest-gtfs --source tisseo --download
python -m mobility_control_tower.cli profile-gtfs --raw-run data/raw/tisseo/<static_run_id>
python -m mobility_control_tower.cli build-bronze --raw-run data/raw/tisseo/<static_run_id>
python -m mobility_control_tower.cli build-silver --bronze-run data/bronze/tisseo/<static_run_id>
python -m mobility_control_tower.cli validate-gtfs --silver-run data/silver/tisseo/<static_run_id>
python -m mobility_control_tower.cli run-dbt --silver-run data/silver/tisseo/<static_run_id>
python -m mobility_control_tower.cli run-quality-validation --suite all --silver-run data/silver/tisseo/<static_run_id> --gold-run data/dbt_gold/tisseo/<dbt_run_id>
python -m mobility_control_tower.cli build-serving-db --gold-run data/dbt_gold/tisseo/<dbt_run_id>
```

Manual fallback: place `Tisseo_GTFS.zip` in `data/raw/manual/` and use `--local-zip data/raw/manual/Tisseo_GTFS.zip`.

## Realtime Snapshot Workflow

```bash
python -m mobility_control_tower.cli fetch-gtfs-rt --source tisseo --feed-type trip_updates
python -m mobility_control_tower.cli parse-gtfs-rt --raw-rt-run data/raw_realtime/tisseo/trip_updates/<rt_run_id>
python -m mobility_control_tower.cli report-gtfs-rt --rt-run data/realtime/tisseo/trip_updates/<rt_run_id>
python -m mobility_control_tower.cli check-rt-compatibility --silver-run data/silver/tisseo/<static_run_id> --rt-run data/realtime/tisseo/trip_updates/<rt_run_id>
python -m mobility_control_tower.cli build-rt-gold --silver-run data/silver/tisseo/<static_run_id> --rt-run data/realtime/tisseo/trip_updates/<rt_run_id>
python -m mobility_control_tower.cli generate-rt-charts --rt-gold-run data/realtime_gold/tisseo/trip_updates/<rt_run_id>
python -m mobility_control_tower.cli generate-rt-snapshot-report --rt-gold-run data/realtime_gold/tisseo/trip_updates/<rt_run_id>
```

Use careful wording: this is a GTFS-Realtime snapshot observed at fetch time, not streaming.

## Realtime Cadences

| Workflow | Schedule | Purpose | Failure behavior |
| --- | --- | --- | --- |
| `daily_static_pipeline` | daily | Static Raw to Silver, dbt Gold, quality, serving publish | No current pointer update on dbt, quality, or serving failure |
| `realtime_snapshot_collection` | every minute | One bounded raw + parsed committed snapshot | Incomplete snapshots are ignored by analytics |
| `realtime_incremental_refresh` | every 10 minutes | New committed snapshots, dbt history, quality, serving refresh, watermark update | Watermark advances only after publication |
| `daily_platform_maintenance` | daily | Full-history quality and storage inventory | Never deletes immutable raw history |

## Serving Workflow

```bash
python -m mobility_control_tower.cli build-serving-db \
  --gold-run data/dbt_gold/tisseo/<dbt_run_id> \
  --history-run data/realtime_history/tisseo/trip_updates \
  --history-gold-run data/dbt_gold/tisseo/<dbt_run_id>

python -m mobility_control_tower.cli query-serving-db \
  --db data/serving/tisseo/runs/<serving_run_id>/mobility_control_tower.duckdb \
  --query-name top-routes \
  --limit 10

python -m mobility_control_tower.cli generate-serving-report \
  --serving-run data/serving/tisseo/runs/<serving_run_id>
```

Useful query names: `network-overview`, `top-routes`, `hourly-headway`, `route-types`, `rt-feed-health`, `rt-compatibility`, `rt-top-delayed-routes`, `rt-top-delayed-stops`.

## API Workflow

```bash
python -m mobility_control_tower.cli serve-api \
  --source tisseo \
  --serving-root data/serving \
  --host 127.0.0.1 \
  --port 8000
```

Open:

- `http://127.0.0.1:8000/health/live`
- `http://127.0.0.1:8000/health/ready`
- `http://127.0.0.1:8000/metadata`
- `http://127.0.0.1:8000/static/top-routes?limit=5`
- `http://127.0.0.1:8000/realtime/feed-health`
- `http://127.0.0.1:8000/docs`

Generate report:

```bash
python -m mobility_control_tower.cli generate-api-report \
  --db data/serving/tisseo/<static_run_id>/mobility_control_tower.duckdb
```

## Dashboard Workflow

Start the API first.

```bash
streamlit run src/mobility_control_tower/dashboard/app.py
```

Or:

```bash
python -m mobility_control_tower.cli serve-dashboard --api-url http://127.0.0.1:8000
```

The dashboard is read-only. It consumes API endpoints and does not write data.

## Final Report

```bash
python -m mobility_control_tower.cli generate-final-report \
  --serving-run data/serving/tisseo/<static_run_id>
```

## Teacher Demo Sequence

1. Show the architecture diagram in the README.
2. Run `pytest`.
3. Show raw/bronze/silver/gold folders.
4. Open quality and KPI reports.
5. Show realtime snapshot compatibility.
6. Query DuckDB with `top-routes`.
7. Start API and open `/docs`.
8. Start dashboard and explain each section.
9. Open the final project report.

## Troubleshooting

- API down in dashboard: start `serve-api` first.
- Missing realtime endpoints: rebuild serving DB with `--rt-gold-run`.
- API live but not ready: publish serving with `build-serving-db` or run `make demo`.
- Missing DuckDB file: check `data/serving/<source>/current.json` and the referenced run directory.
- Trip compatibility WARN: selected static GTFS may not match all realtime trip IDs.
- Download failure: use manual static ZIP placement or saved realtime snapshots.

## Clean Generated Data Safely

Generated data is ignored by git. To clean local outputs, remove specific generated subfolders only, for example:

```bash
rm -r data/reports/<specific_file_or_folder>
rm -r data/serving/tisseo/<static_run_id>
```

Do not delete source code, docs, config, or tests.

## What Not To Commit

Do not commit:

- downloaded GTFS ZIP files;
- GTFS-Realtime `feed.pb` snapshots;
- generated CSV data under `data/`;
- DuckDB files;
- generated PNG charts;
- generated reports from real data unless explicitly approved.
## Incident Evaluation

Run `python -m mobility_control_tower.cli migrate-incident-store` after deployment or restore. After each authoritative serving publication, run `python -m mobility_control_tower.cli evaluate-incidents --source tisseo --json`. A failed evaluation must be investigated from `/v1/incidents/evaluations`; do not interpret evaluator failure as a healthy network. Operator acknowledgement, resolution, suppression, and unsuppression are audited in the incident event history. Full rule semantics are documented in `docs/incidents.md`.
# Release-Proof Runtime Checks

Use `make demo` for local Docker runtime proof when Docker is available. Then run:

```bash
make demo-smoke
make browser-smoke
make capture-screenshots
make verify-prometheus-runtime
make verify-grafana-runtime
make verify-postgres-restore
```

`/health/live` proves the API process is alive. `/health/ready` additionally proves the current serving artifact is queryable and the configured incident repository is migrated and reachable. A failed readiness check must not be interpreted as "all healthy."

The GitHub Actions `release-proof` job uploads `artifacts/release-evidence/` with health, Airflow, Prometheus, Grafana, browser, restore, failure-injection, screenshot, Compose status, and container-log evidence. Preserve these artifacts for failed runs; they are the first diagnostic source.

If Docker is unavailable in local WSL, run the non-Docker gates and rely on GitHub Actions for runtime proof. Do not report Compose, PostgreSQL runtime persistence, Grafana provisioning, or screenshots as verified without actual runtime artifacts.
