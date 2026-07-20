# Data Quality

The silver validator checks whether core tables and columns exist, reports row counts, and detects:

- missing key values and duplicate stop, route, or trip identifiers;
- invalid stop latitude and longitude;
- uncommon or invalid obvious `route_type` values;
- invalid arrival and departure time syntax, including support for valid hours above 23;
- stop times referencing unknown trips or stops;
- trips referencing unknown routes or service identifiers.

## Status meanings

- **PASS**: the check found no problems.
- **WARN**: the data deserves review, but the condition may be an extension or a usable non-critical value. The route-type range check uses this status.
- **FAIL**: a required structure, value, format, uniqueness rule, or relationship has a detected problem.

The report's overall status is the most severe individual status. Validation reports findings without modifying silver data or stopping merely because a check fails.

## Limitations

Analytical quality after Silver is handled by dbt tests and MCT quality contracts:

- dbt unit tests catch fan-out and semantic KPI regressions.
- dbt data tests enforce composite grains, non-negative metrics, null keys, reconciliation totals, and delay policy.
- MCT quality contracts validate the authoritative dbt Gold artifact and fail the CLI when expectations fail.

Serving publication records the latest quality status in `serving_manifest.json` and `current.json`. The serving builder validates DuckDB queryability before updating the current pointer; a failed quality-contract run or failed serving validation preserves the prior last known-good artifact.

This is not complete GTFS certification. A dedicated standards validator would still be appropriate before production publication.
