# Durable Incident Lifecycle

The incident evaluator consumes authoritative serving and quality evidence; it
does not recalculate dbt reliability KPIs. Versioned rules open, update,
acknowledge, suppress, resolve, and reopen incidents through explicit state
transitions. Evidence fingerprints and correlation keys make repeated evaluation
idempotent, while incident events form an append-only audit trail.

SQLite is the local default. PostgreSQL implements the same repository contract
for the composed runtime and is configured separately from Airflow metadata.
Run `migrate-incident-store` before evaluation. This stage adds durable domain
state and CLI operations; authenticated HTTP operator workflows follow
separately.
