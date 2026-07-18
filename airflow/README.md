# Mobility Control Tower Airflow Layer

This directory contains Apache Airflow orchestration only. Business logic stays in the existing `mobility_control_tower.cli` commands.

## Layout

```text
airflow/
  dags/      DAG definitions and small orchestration helpers
  plugins/   reserved for future Airflow plugins
  logs/      local Airflow logs
  config/    local Airflow configuration notes/placeholders
```

## DAGs

- `daily_static_pipeline`: daily static GTFS pipeline from ingestion through dbt, GE validation, and serving.
- `realtime_collection`: minute-level GTFS-Realtime historical collection, dbt history marts, GE validation, and history serving refresh.

Both DAGs call the CLI through Python subprocesses and write execution metadata under `data/pipeline_runs/`.
