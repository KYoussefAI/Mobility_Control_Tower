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

The realtime views describe one saved snapshot and must not be interpreted as
passenger experience or recurring service reliability. Components run as local
processes and there is no scheduler, authentication, or operational state store.

## Development And Releases

New work uses focused feature branches and pull requests. See `CONTRIBUTING.md`,
`CHANGELOG.md`, and `docs/release_process.md`.

## Realtime Acquisition

`mobility_control_tower.realtime.gtfs_rt_raw.fetch_realtime_snapshot` fetches
one configured Trip Updates, Vehicle Positions, or Service Alerts payload and
stores `feed.pb` beside acquisition time, HTTP metadata, size, source provenance,
and SHA-256. Raw run directories are never overwritten.

Snapshot-level KPI tables, charts, DuckDB views, API routes, and dashboard panels
are available for feed health, identifier matching, and observed delays. These
are bounded diagnostics from one acquisition, not historical service claims.

Malformed payloads now fail before partial publication. Timestamp, duplicate,
missing-identifier, relationship, and partial-update behavior is documented in
`docs/realtime_input_hardening.md`; unusable snapshots cannot populate operational
delay tables.

Immutable history is now modeled by dbt staging and trend marts for delay
evolution, feed freshness, and trip matching. These models describe collected
observations and coverage; they do not prove passenger experience.

The first authoritative realtime reliability slice adds delay facts,
distributions, scheduled-trip coverage, and route/network OTP. Missing realtime
updates remain unknown and do not become cancellations. See
`docs/delay_coverage_otp.md`.
