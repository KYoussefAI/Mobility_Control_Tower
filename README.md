# Mobility Control Tower

## Overview

Mobility Control Tower includes a Streamlit dashboard that consumes the FastAPI service. The application presents static schedule analytics published through DuckDB; it does not read transformation outputs directly.

## Architecture

```text
GTFS -> Python layers -> dbt Gold -> DuckDB -> FastAPI -> Streamlit
```

This consumer boundary keeps analytical ownership in dbt and query access in the API while allowing the user interface to remain a replaceable client.

## Running the Project

```bash
python -m pip install -e '.[quality,analytics]'
mobility-control-tower serve-api
mobility-control-tower serve-dashboard
```

Build and publish a serving database first, start the API, then configure the dashboard with its base URL. Use CLI help for exact options.

## Limitations

The dashboard represents planned static service, not live operations. Components run as local processes and there is no scheduler, authentication, or operational state store.

## Development And Releases

New work uses focused feature branches and pull requests. See `CONTRIBUTING.md`,
`CHANGELOG.md`, and `docs/release_process.md`.
