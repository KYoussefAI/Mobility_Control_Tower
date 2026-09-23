# Backup And Recovery

Local backup commands:

```bash
make backup
make restore BACKUP=data/backups/<backup_id>
make verify-restore
```

The backup bundle includes source configuration, incidents and audit events, watermarks, serving pointers and manifests, quality summary state, and lineage status when present. Immutable raw protobuf history and parsed historical Parquet should be copied with the storage backend’s native file-copy mechanism; this phase does not automatically delete raw history.

Project recovery targets, not guarantees:

- RPO: latest successful backup for metadata and serving pointers; raw history depends on storage copy cadence.
- RTO: under one hour for a local deterministic restore on a developer machine.

Restore verification checks that the source registry restores, serving pointers remain valid JSON when present, and the backup manifest is readable.
## Incident State

Backups include the incident repository under `data/incidents`, including SQLite state, append-only JSONL event history, evaluation runs, suppressions, and migration version. `make verify-restore` seeds incident records and verifies that active, acknowledged, suppressed, and event states survive restore; it also checks that post-restore evaluation deduplicates and that the API can read restored incident state.
# PostgreSQL Incident Restore Proof

The release-candidate runtime restore test runs against the Compose PostgreSQL application incident database, not the local SQLite fallback:

```bash
docker compose --profile demo exec -T api python scripts/verify_postgres_restore.py
```

The verifier exports `schema_versions`, `incidents`, `incident_events`, and `incident_evaluation_runs`, destructively clears the application incident tables, restores the rows, verifies acknowledged and suppressed states, checks immutable event history, reruns the evaluator, and verifies API readiness. CI copies the restore report and backup JSON into `artifacts/runtime/` and then into `artifacts/release-evidence/`.

Local `make verify-restore` remains the SQLite-compatible backup/restore smoke test. Do not use it as evidence for PostgreSQL restore.
