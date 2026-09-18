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

Tests validate DAG structure without presenting scheduler import success as runtime proof. Airflow is a local orchestrator here; there is no PostgreSQL incident domain, authentication, container stack, or observability deployment.
