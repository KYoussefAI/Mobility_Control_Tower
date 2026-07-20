# MCT Quality Contracts

Mobility Control Tower uses custom MCT quality contracts, not Great Expectations. The implementation loads explicit JSON suites from `quality_contracts/expectations/`, validates Silver CSV, dbt Gold exports, and historical Parquet with pandas, writes machine-readable results, generates simple local validation docs, and raises an error when required expectations fail.

## Commands

```bash
python -m mobility_control_tower.cli run-quality-validation \
  --suite all \
  --silver-run data/silver/tisseo/<run_id> \
  --gold-run data/dbt_gold/tisseo/<dbt_run_id> \
  --history-run data/realtime_history/tisseo/trip_updates
```

`run-ge-validation` remains only as a legacy alias for compatibility and emits a deprecation warning.

Outputs:

```text
quality_contracts/validation_results/
quality_contracts/data_docs/local_site/index.html
data/quality/latest_validation_summary.json
```

The dashboard Data Quality page reads the latest summary through the API.
