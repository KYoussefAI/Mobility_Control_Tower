# Mobility Control Tower

## Overview

This snapshot extends immutable Tisséo GTFS ingestion with source profiling and a Bronze representation. Raw remains the acquisition record; Bronze extracts the feed into table-level files while preserving source values for inspection and downstream transformation.

## Architecture

```text
GTFS source -> immutable Raw archive -> profile -> Bronze tables
```

Raw runs retain the archive and provenance metadata. Profiling records structural characteristics of the feed, while Bronze materializes source tables without applying the canonical cleaning rules of a curated layer.

## Running the Project

```bash
python -m pip install -e .
mobility-control-tower --help
mobility-control-tower ingest-gtfs
```

Use CLI help for the profiling and Bronze options available here. Source details are in [`docs/data_source.md`](docs/data_source.md).

## Verification and Limitations

Tests cover GTFS profiling in addition to ingestion. The pipeline remains local and manually invoked. There is no Silver layer, formal quality contract, analytical mart, or serving component.
