# ADR 0005: Durable Incident Evaluator

## Status

Accepted

## Context

Reliability analytics are authoritative in dbt and served through DuckDB views. Operators need persistent incidents with acknowledgement, suppression, resolution, recurrence, and audit history. Prometheus alerts are useful for aggregate visibility, but they are not a durable operator workflow.

## Decision

Implement a versioned Python incident evaluator that consumes authoritative serving views, committed realtime manifests, quality summaries, and serving pointers. Persist local state in a migrated SQLite repository with append-only events and a JSONL audit mirror. Compose deployments keep incident storage separate from Airflow metadata; PostgreSQL can implement the same repository contract with advisory or lock-row concurrency.

## Consequences

The evaluator is idempotent under retries and uses deterministic deduplication keys plus evidence fingerprints. It does not calculate reliability KPIs. Airflow triggers evaluation after serving publication and during maintenance. Prometheus exports bounded aggregate incident metrics only.
