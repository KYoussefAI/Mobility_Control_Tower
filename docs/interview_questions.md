# Interview Questions

## Why DuckDB?

DuckDB is embedded, fast for analytical SQL, reads Parquet directly, and avoids running a database server for a local data engineering platform.

## Why Airflow?

Airflow provides scheduling, retries, dependency graphs, and operational visibility. In this project it calls the CLI, so orchestration does not duplicate business logic.

## Why dbt?

dbt documents and tests SQL models after Silver. It brings lineage, model contracts, and analytics engineering practices without replacing Python ingestion.

## Why Great Expectations?

Great Expectations makes data quality explicit. It validates Silver, Gold, and historical datasets and produces Data Docs for review.

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

