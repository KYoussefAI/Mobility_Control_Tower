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

Tests validate DAG structure without presenting scheduler import success as runtime proof. The full local stack now has a deterministic fixture/bootstrap path and browser-driven evidence capture for the API and dashboard.

## Reproducible demo evidence

Fixture generation, stack bootstrap, browser capture, and evidence collection are scripted so a reviewer can reproduce the demonstrated state. Generated runtime data and screenshots remain excluded from source control. See [`docs/final_demo_guide.md`](docs/final_demo_guide.md).
