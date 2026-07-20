# Interview Questions

## Why DuckDB?

DuckDB is embedded, fast for analytical SQL, reads Parquet directly, and avoids running a database server for a local data engineering platform.

## Why Airflow?

Airflow provides scheduling, retries, dependency graphs, and operational visibility. In this project it calls the CLI, so orchestration does not duplicate business logic.

## Why dbt?

dbt documents and tests SQL models after Silver. It brings lineage, model contracts, and analytics engineering practices without replacing Python ingestion.

## Why MCT quality contracts?

The project uses custom MCT quality contracts so validation behavior is honest and local-first. It validates Silver, dbt Gold, and historical datasets, writes machine-readable results, generates local validation docs, and fails when expectations fail.

## Why FastAPI?

FastAPI provides typed, documented, read-only API endpoints with OpenAPI support and easy local serving.

## Why Streamlit?

Streamlit is fast for creating an analytical dashboard and is appropriate for a local portfolio MVP.

## Why Parquet?

Parquet is columnar, compressed, typed, partition-friendly, and efficient for DuckDB scans over historical GTFS-Realtime data.

## Why Medallion Architecture?

Raw, Bronze, Silver, and Gold layers separate preservation, extraction, cleaning, and analytics. This keeps the pipeline explainable and auditable.

## Why Scheduled Polling Instead Of Kafka?

The use case needs historical snapshots, not high-throughput streaming. Scheduled polling is simpler, cheaper, and easier to explain.

## How Is It Cloud Ready?

The project keeps local mode but adds a storage abstraction that can target local filesystem or S3 via boto3.
## Incident Engine Discussion

Key talking point: application incidents are separate from Prometheus alerts. dbt computes reliability facts, serving publishes trusted inputs, and the evaluator performs deterministic state transitions with deduplication keys, evidence fingerprints, suppression expiry, and append-only event history. Prometheus monitors aggregate incident state and evaluator health but does not own the operator workflow.
# Runtime-Proof Talking Points

**How do you prove the demo is release-candidate ready?** The `release-proof` CI job builds the Docker image, starts the deterministic Compose stack, waits on bounded health checks, verifies PostgreSQL incident persistence, checks Airflow scheduler/DAG parsing, validates Prometheus with `promtool`, verifies Grafana through its HTTP API, runs Playwright browser smoke tests, captures real screenshots, performs PostgreSQL backup/restore, runs reversible failure injection, and uploads a release-evidence bundle.

**Why keep SQLite?** SQLite remains the local deterministic fallback for non-Docker development and fast tests. Compose and production use PostgreSQL through the same repository contract, and production rejects SQLite unless an explicit unsafe development override is set.

**What is not claimed locally?** If Docker is unavailable in WSL, local commands can prove Python/dbt/static checks but cannot prove Compose, PostgreSQL runtime persistence, Grafana provisioning, screenshots, or container restart behavior. Those claims come only from the `release-proof` workflow artifacts.
