# Mobility Control Tower Runbook

Operational guide for the local academic MVP.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

Run all commands from the repository root.

## Static Workflow

```bash
python -m mobility_control_tower.cli ingest-gtfs --source tisseo --download
python -m mobility_control_tower.cli profile-gtfs --raw-run data/raw/tisseo/<static_run_id>
python -m mobility_control_tower.cli build-bronze --raw-run data/raw/tisseo/<static_run_id>
python -m mobility_control_tower.cli build-silver --bronze-run data/bronze/tisseo/<static_run_id>
python -m mobility_control_tower.cli validate-gtfs --silver-run data/silver/tisseo/<static_run_id>
python -m mobility_control_tower.cli build-gold --silver-run data/silver/tisseo/<static_run_id>
python -m mobility_control_tower.cli generate-static-charts --gold-run data/gold/tisseo/<static_run_id>
python -m mobility_control_tower.cli generate-demo-report --gold-run data/gold/tisseo/<static_run_id>
python -m mobility_control_tower.cli generate-static-mvp-report --gold-run data/gold/tisseo/<static_run_id>
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

## Serving Workflow

```bash
python -m mobility_control_tower.cli build-serving-db \
  --gold-run data/gold/tisseo/<static_run_id> \
  --rt-gold-run data/realtime_gold/tisseo/trip_updates/<rt_run_id>

python -m mobility_control_tower.cli query-serving-db \
  --db data/serving/tisseo/<static_run_id>/mobility_control_tower.duckdb \
  --query-name top-routes \
  --limit 10

python -m mobility_control_tower.cli generate-serving-report \
  --serving-run data/serving/tisseo/<static_run_id>
```

Useful query names: `network-overview`, `top-routes`, `hourly-headway`, `route-types`, `rt-feed-health`, `rt-compatibility`, `rt-top-delayed-routes`, `rt-top-delayed-stops`.

## API Workflow

```bash
python -m mobility_control_tower.cli serve-api \
  --db data/serving/tisseo/<static_run_id>/mobility_control_tower.duckdb \
  --host 127.0.0.1 \
  --port 8000
```

Open:

- `http://127.0.0.1:8000/health`
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
- Missing DuckDB file: run `build-serving-db`.
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
