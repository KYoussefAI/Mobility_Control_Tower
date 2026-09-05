# Mobility Control Tower

## Overview

Mobility Control Tower publishes dbt-produced Gold marts as a local DuckDB serving artifact. Publication builds and validates a replacement separately, then updates the current pointer so readers do not observe a partially constructed analytical store.

## Architecture

```text
GTFS -> Python Raw/Bronze/Silver -> dbt Gold -> quality gate -> DuckDB serving artifact
```

DuckDB is a serving boundary, not the owner of transformations. dbt remains authoritative for Gold logic; serving exposes stable views over accepted outputs. See [`docs/adr/0001-duckdb-serving.md`](docs/adr/0001-duckdb-serving.md).

## Running the Project

```bash
python -m pip install -e '.[quality,analytics]'
mobility-control-tower build-serving-db
```

Supply the Gold run and destination arguments shown by CLI help. Quality behavior is documented in [`docs/data_quality.md`](docs/data_quality.md).

## Limitations

Serving is embedded and local. There is no network API, dashboard, realtime processing, or scheduler.
