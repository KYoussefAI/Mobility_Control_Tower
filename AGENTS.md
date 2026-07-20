# Mobility Control Tower Agent Notes

Supported setup:

- `python -m pip install -e ".[dev,quality,analytics]"`

Quality and verification commands:

- `ruff check .`
- `black --check .`
- `isort --check-only .`
- `mypy src`
- `coverage run -m pytest`
- `coverage report --fail-under=80`
- `dbt deps --project-dir dbt --profiles-dir dbt`
- `dbt parse --project-dir dbt --profiles-dir dbt`
- `dbt build --project-dir dbt --profiles-dir dbt --vars '<fixture vars>'`
- `docker build -t mobility-control-tower:ci .`

Architecture boundaries:

- Python owns ingestion, parsing, Raw, Bronze, Silver, and GTFS-Realtime historical Parquet collection.
- dbt owns staging, intermediate analytical models, and Gold marts from Silver and historical Parquet.
- DuckDB serves dbt-produced Gold artifacts and historical Parquet views.

Rules:

- Do not add fake-success fallbacks for dbt, quality validation, tests, or docs.
- Do not silently substitute Python Gold builders for dbt Gold.
- Keep local-first operation and avoid Kafka, Spark, Kubernetes, microservices, or cloud warehouses.
- Preserve public CLI compatibility where reasonable; mark legacy or diagnostic behavior clearly when retained.
- Do not commit generated data, local databases, coverage output, dbt target output, or validation run artifacts.
