# Mobility Control Tower

## Overview

Apache Airflow orchestrates the command-line workflows for daily static processing, bounded realtime collection, and incremental historical refresh. DAGs preserve the established ownership boundaries instead of embedding alternative transformation logic in the scheduler.

## Orchestration

```text
Airflow DAG -> CLI tasks -> Python ingestion/layers -> dbt Gold -> quality -> DuckDB publication
                    \-> realtime history -> watermark advanced last
```

The incremental DAG orders collection, analytical refresh, validation, publication, and watermark commitment so failure leaves the previous accepted state recoverable. See [`airflow/README.md`](airflow/README.md), [`docs/architecture/airflow_dag_overview.md`](docs/architecture/airflow_dag_overview.md), and [`docs/historical_collection.md`](docs/historical_collection.md).

## Verification and Limitations

Tests validate DAG structure without presenting scheduler import success as runtime proof. Airflow remains a local orchestrator. The repository also includes the PostgreSQL incident domain, scoped operator authentication, process-local rate limits, containers, observability, release gates, and reproducible browser evidence.

## Multi-city and storage portability

The source catalogue now contains Toulouse and Rennes. Typed settings select a source and a storage backend, while the storage abstraction supports the local filesystem by default and an optional S3-compatible implementation through boto3. See [`docs/multi_city.md`](docs/multi_city.md).

The platform is still local-first. Multi-city configuration and an optional cloud storage adapter do not prove distributed scale, high availability, or a managed cloud deployment.
