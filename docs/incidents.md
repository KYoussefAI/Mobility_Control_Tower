# Operational Incidents

Application incidents are the durable source of truth for operator workflow. Prometheus alerts summarize evaluator health and aggregate incident pressure, but Prometheus and future Alertmanager notification routing are not incident storage.

## Architecture

```text
authoritative reliability and platform state
        ↓
candidate normalization
        ↓
versioned rule evaluation
        ↓
transactional deduplication and transitions
        ↓
incident repository and immutable events
        ↓
API/dashboard and aggregate Prometheus metrics
```

dbt owns production reliability analytics. The evaluator consumes serving views such as `v_reliability_incident_snapshot`, `v_realtime_trip_coverage`, `v_headway_reliability_events`, the serving `current.json` pointer, committed realtime manifests, and MCT quality summaries. It does not calculate coverage, headways, delay percentiles, OTP, or cancellations.

## Rules

| Rule | Input | Scope | Version | Opens | Resolves |
|---|---|---|---|---|---|
| stale realtime feed | committed realtime snapshot manifests | `source + feed_type` | `stale_feed_v1` | enabled feed age above warning or critical threshold | two healthy observations below warning threshold |
| low realtime coverage | `v_realtime_trip_coverage` | network and route service period | `low_coverage_v1` | eligible denominator meets minimum and coverage is below threshold | two high-confidence observations at or above healthy threshold |
| severe service gap | `v_headway_reliability_events` | route, direction, stop, operational window | `service_gap_v1` | `SERVICE_GAP` only, never `BUNCHING` | healthy observations from later authoritative evidence |
| blocking quality failure | `latest_validation_summary.json` | source artifact type | `quality_failure_v1` | failed or unavailable blocking quality summary | one later successful blocking validation |
| stale serving artifact | serving `current.json` and manifest | source | `stale_serving_v1` | missing, unreadable, or old current artifact | two successful fresh publications |

Default thresholds live in `mobility_control_tower.incidents.default_rule_config`. Environment overrides are supported with `MCT_INCIDENT_RULES_JSON`; source-specific overrides are nested under `source_overrides`. Threshold validation rejects negative durations, critical-before-warning freshness, and coverage hysteresis that would flap.

## State

Statuses are `OPEN`, `ACKNOWLEDGED`, `MONITORING`, `RESOLVED`, and `SUPPRESSED`. Valid transitions are explicit in code and invalid transitions fail. Repeated unhealthy evidence updates the existing deduplication key and preserves acknowledgement. Severity escalation and de-escalation are evented. Healthy evidence starts `MONITORING`; automatic resolution requires the configured healthy count. Manual resolution requires a nonempty reason and preserves the operator note in event history.

Suppressions store actor, reason, start, and expiry. While suppressed, evaluation keeps evidence current but does not create duplicate operator-facing active incidents. Expired suppression reopens to `OPEN` when the condition is still unhealthy, or resolves when healthy.

Resolved incidents recur on the same incident record: the evaluator appends `REOPENED`, increments `recurrence_count`, clears active resolution fields, and preserves prior resolution details in events.

## Storage

Local mode uses `data/incidents/incidents.sqlite` with explicit migrations in `schema_versions`. Events are append-only in SQLite and mirrored to `incident_events.jsonl` for local backup compatibility. Compose can mount the same application store separately from Airflow metadata; incident tables must not be treated as Airflow XCom or Airflow metadata state.

Each candidate application is transactional: find incident, create or update incident, append event, commit. SQLite local mode uses a lock row with expiry for evaluator concurrency. PostgreSQL deployments should use the same repository contract with advisory or lock-row semantics in the application database or schema.

## CLI

```bash
python -m mobility_control_tower.cli migrate-incident-store
python -m mobility_control_tower.cli evaluate-incidents --source tisseo --evaluation-time 2026-07-19T12:00:00+00:00 --json
python -m mobility_control_tower.cli evaluate-incidents --source tisseo --dry-run --json
python -m mobility_control_tower.cli list-incidents --json
python -m mobility_control_tower.cli show-incident --incident-id inc_...
```

Dry run evaluates real candidates and returns proposed actions without acquiring the write lock or mutating incident state.

## API And Permissions

Read endpoints require `operations:read`; operator mutations require `incidents:write`; manual evaluation requires `admin`.

```text
GET  /v1/incidents
GET  /v1/incidents/{incident_id}
GET  /v1/incidents/{incident_id}/events
GET  /v1/incidents/evaluations
POST /v1/incidents/evaluate
POST /v1/incidents/{incident_id}/acknowledge
POST /v1/incidents/{incident_id}/resolve
POST /v1/incidents/{incident_id}/suppress
POST /v1/incidents/{incident_id}/unsuppress
```

Responses expose structured evidence, rule version, calculation version, serving run, confidence, and coverage where available. Evidence intentionally excludes filesystem paths, secrets, row samples, raw SQL, and stack traces.

## Metrics

The durable exporter emits bounded labels only:

```text
mct_incidents_active
mct_incidents_suppressed
mct_incident_evaluation_last_success_timestamp_seconds
mct_incident_evaluation_last_failure_timestamp_seconds
mct_incident_evaluation_candidates
mct_incident_evaluation_transitions
```

Labels are limited to source, rule, severity, status, result, and transition. Incident IDs, entity IDs, route IDs, stop IDs, trip IDs, snapshot IDs, serving runs, actors, and error messages are not metric labels.

## Troubleshooting

If evaluation fails, check `/v1/incidents/evaluations`, Airflow task metadata, and the incident store migration version. A failed evaluation never marks active incidents healthy. A lock conflict records `SKIPPED_LOCKED` and does not process candidates. If the serving view is unavailable, analytical candidates are not generated and platform rules still run from manifests.
# Runtime Persistence

Local non-Docker execution defaults to SQLite under `data/incidents/`. Docker Compose and production use PostgreSQL:

```text
MCT_INCIDENT_BACKEND=postgres
MCT_INCIDENT_DATABASE_URL=postgresql://<app-user>:<password>@postgres:5432/<app-db>
```

The Airflow metadata database and Mobility Control Tower application incident database are separated on the same PostgreSQL server. `incident-migrate` runs the application incident migrations before API, dashboard, metrics exporter, or Airflow incident evaluation depend on the store.

`python -m mobility_control_tower.cli migrate-incident-store --json` reports backend, sanitized target, starting schema version, ending schema version, applied migrations, and status. Production rejects SQLite unless an explicit unsafe development override is set.

## Release Evidence

The release-proof job verifies PostgreSQL-backed incident persistence through:

- repository contract tests against a real PostgreSQL database;
- deterministic evaluator retries with identical inputs;
- API and dashboard reads from durable state;
- Prometheus metrics derived from durable incidents;
- backup, destructive reset, restore, and evaluator deduplication after restore;
- reversible failure injection for service restarts and PostgreSQL interruption.

Prometheus and future Alertmanager routing are observers only. Application incidents and immutable incident events remain the system of record.
