# Local lineage and benchmarking

The project includes operator-oriented inspection tools around the existing platform.

- `mobility_control_tower.lineage` writes OpenLineage-compatible JSON Lines events and a small local status document.
- `scripts/lineage_smoke.py` checks the event path without requiring a remote lineage service.
- `mobility-control-tower run-benchmarks` measures existing local artifacts and DuckDB/API setup, recording duration, row count, and traced peak memory.
- `scripts/doctor.py` reports dependency, port, import, storage, and serving-pointer readiness.
- `daily_platform_maintenance` inventories storage and performs bounded maintenance checks through Airflow.

These are reproducible local diagnostics. The local event writer is not a hosted lineage backend, and the benchmark is not a production load test.
