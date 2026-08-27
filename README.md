# Mobility Control Tower — Milestone 03

The project now supports the configured static Tisséo GTFS source and preserves each downloaded archive as an immutable Raw artifact with provenance metadata.

```bash
mobility-control-tower ingest-gtfs
```

Repeated ingestion keeps prior source archives intact so every acquired feed remains auditable.
