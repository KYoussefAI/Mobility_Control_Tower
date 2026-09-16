# Mobility Control Tower

## Overview

Historical realtime observations and scheduled service support reliability analytics in dbt. Gold marts cover observed delay, on-time performance, explicit cancellations, coverage, headway reliability, and excess waiting time, with reconciliation and domain tests guarding interpretation.

## Analytical Boundary

```text
Silver schedule + historical GTFS-Realtime Parquet
        -> dbt staging/intermediate
        -> tested reliability Gold marts
        -> DuckDB -> FastAPI -> Streamlit
```

Missing realtime updates are not classified as cancellations; cancellation measures require explicit evidence. Headway and excess-waiting metrics are produced only where eligibility rules are satisfied. See [`docs/realtime_snapshot_kpis.md`](docs/realtime_snapshot_kpis.md) and [`docs/static_mvp_explanation.md`](docs/static_mvp_explanation.md).

## Verification and Limitations

dbt tests check percentage ranges, percentile ordering, reconciliation, positive headways, and mutually exclusive reliability events. Processing is still manually invoked and history refreshes are not watermark-driven. Results reflect collected observations, not an exhaustive record of agency operations.
