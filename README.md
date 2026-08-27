# Mobility Control Tower

## Overview

Mobility Control Tower is a local-first public-transport data engineering project. In this snapshot, it provides reproducible ingestion for the configured Tisséo static GTFS feed. Each acquisition is retained as an immutable Raw archive with provenance and integrity metadata, creating an auditable source for later processing.

## Architecture

```text
Configured GTFS source -> Raw run directory -> archive + manifest
```

The ingestion layer downloads the source without interpreting its tables. Run-specific storage prevents later acquisitions from overwriting earlier evidence.

## Running the Project

```bash
python -m pip install -e .
mobility-control-tower --help
mobility-control-tower ingest-gtfs
```

Source configuration is held in `config/sources.yml`. See [`docs/data_source.md`](docs/data_source.md) for the source and provenance contract.

## Current Boundary

This snapshot covers acquisition and Raw preservation only. It does not profile or transform GTFS tables, validate analytical quality, build marts, or provide a serving interface. Storage is local and execution is manual.
