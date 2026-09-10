# Mobility Control Tower

## Overview

Mobility Control Tower includes a Streamlit dashboard that consumes the FastAPI service. The application presents static schedule analytics published through DuckDB; it does not read transformation outputs directly.

## Architecture

```text
GTFS -> Python layers -> dbt Gold -> DuckDB -> FastAPI -> Streamlit
GTFS-Realtime endpoint -> immutable checksummed Raw snapshot
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

The dashboard still represents planned static service. The realtime layer in
this release preserves acquisition evidence only; it does not yet parse payloads
or produce operational metrics. Components run as local processes and there is
no scheduler, authentication, or operational state store.

## Development And Releases

New work uses focused feature branches and pull requests. See `CONTRIBUTING.md`,
`CHANGELOG.md`, and `docs/release_process.md`.

## Realtime Acquisition

`mobility_control_tower.realtime.gtfs_rt_raw.fetch_realtime_snapshot` fetches
one configured Trip Updates, Vehicle Positions, or Service Alerts payload and
stores `feed.pb` beside acquisition time, HTTP metadata, size, source provenance,
and SHA-256. Raw run directories are never overwritten.
