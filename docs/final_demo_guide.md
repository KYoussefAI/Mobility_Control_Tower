# Final demo guide

## Full demo sequence

1. Install:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e '.[dev]'
   ```

2. Run tests:

   ```bash
   pytest
   ```

3. Download and ingest static GTFS:

   ```bash
   python -m mobility_control_tower.cli ingest-gtfs --source tisseo --download
   ```

4. Build static layers:

   ```bash
   python -m mobility_control_tower.cli profile-gtfs --raw-run data/raw/tisseo/<static_run_id>
   python -m mobility_control_tower.cli build-bronze --raw-run data/raw/tisseo/<static_run_id>
   python -m mobility_control_tower.cli build-silver --bronze-run data/bronze/tisseo/<static_run_id>
   python -m mobility_control_tower.cli validate-gtfs --silver-run data/silver/tisseo/<static_run_id>
   python -m mobility_control_tower.cli build-gold --silver-run data/silver/tisseo/<static_run_id>
   ```

5. Generate static evidence:

   ```bash
   python -m mobility_control_tower.cli generate-static-charts --gold-run data/gold/tisseo/<static_run_id>
   python -m mobility_control_tower.cli generate-demo-report --gold-run data/gold/tisseo/<static_run_id>
   ```

6. Fetch and parse one GTFS-Realtime snapshot:

   ```bash
   python -m mobility_control_tower.cli fetch-gtfs-rt --source tisseo --feed-type trip_updates
   python -m mobility_control_tower.cli parse-gtfs-rt --raw-rt-run data/raw_realtime/tisseo/trip_updates/<rt_run_id>
   ```

7. Build realtime snapshot KPIs:

   ```bash
   python -m mobility_control_tower.cli build-rt-gold --silver-run data/silver/tisseo/<static_run_id> --rt-run data/realtime/tisseo/trip_updates/<rt_run_id>
   ```

8. Build DuckDB serving database:

   ```bash
   python -m mobility_control_tower.cli build-serving-db --gold-run data/gold/tisseo/<static_run_id> --rt-gold-run data/realtime_gold/tisseo/trip_updates/<rt_run_id>
   ```

9. Start API:

   ```bash
   python -m mobility_control_tower.cli serve-api --db data/serving/tisseo/<static_run_id>/mobility_control_tower.duckdb
   ```

10. Start dashboard in another terminal:

    ```bash
    streamlit run src/mobility_control_tower/dashboard/app.py
    ```

11. Generate final report:

    ```bash
    python -m mobility_control_tower.cli generate-final-report --serving-run data/serving/tisseo/<static_run_id>
    ```

## Five-minute demo script

1. "This project turns official Tisseo transport data into trusted local data products."
2. "The static GTFS pipeline preserves raw data, cleans it, validates it, and builds planning KPIs."
3. "The realtime part is snapshot-based. It parses one GTFS-Realtime feed and compares IDs with static GTFS."
4. "DuckDB makes the outputs queryable with SQL."
5. "FastAPI exposes read-only JSON endpoints."
6. "The Streamlit dashboard consumes the API and shows the final local demo."
7. "This is not production monitoring; it is a complete academic MVP."

## Deterministic Docker Demo

For release-candidate proof, prefer the deterministic Compose path:

```bash
make demo
make demo-smoke
make browser-smoke
make capture-screenshots
make verify-prometheus-runtime
make verify-grafana-runtime
make verify-postgres-restore
make demo-down
```

When Docker is unavailable locally, GitHub Actions `release-proof` is the authoritative runtime evidence gate. Do not mark local Compose verification as passed unless containers actually started.

Screenshots are generated into `artifacts/screenshots/` with `manifest.json`. Portfolio screenshots under `docs/screenshots/` should only be updated from a successful deterministic capture.
