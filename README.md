# Mobility Control Tower

## Overview

FastAPI provides a read interface over the published DuckDB serving artifact. Health, metadata, and schedule-analytics endpoints separate consumers from database paths while preserving dbt as the owner of Gold transformations.

## Architecture

```text
GTFS -> Raw/Bronze/Silver -> dbt Gold -> DuckDB publication -> FastAPI
```

The API opens the current validated serving database and applies bounded query patterns. It does not rebuild analytical logic or mutate source data.

## Running the Project

```bash
python -m pip install -e '.[quality,analytics]'
mobility-control-tower build-serving-db
mobility-control-tower serve-api
```

Use CLI help for serving paths and host/port options. The DuckDB choice is documented in [`docs/adr/0001-duckdb-serving.md`](docs/adr/0001-duckdb-serving.md).

## Limitations

The API exposes static scheduled-service analytics only. There is no dashboard, authentication, realtime ingestion, incident state, or orchestration.
