# Single-Host Deployment

The production artifacts are prepared for a Linux VM running Docker Compose. No public deployment was executed in this repository.

Validate configuration:

```bash
MCT_PUBLIC_HOSTNAME=mct.example.test \
MCT_AUTH_SECRET=replace-with-real-secret \
TLS_EMAIL=ops@example.test \
docker compose -f docker-compose.yml -f deploy/production.compose.yml --profile production config
```

Automated production-overlay assertions are available after rendering Compose JSON:

```bash
docker compose -f docker-compose.yml -f deploy/production.compose.yml --profile production config --format json > artifacts/runtime/production-compose.json
python scripts/verify_production_overlay.py --compose-json artifacts/runtime/production-compose.json
```

Public exposure is limited to the Caddy reverse proxy on ports 80 and 443. PostgreSQL, Airflow, Prometheus, the metrics exporter, and Grafana should remain internal unless a separate protected access path is configured.

Required production settings:

- `MCT_PUBLIC_HOSTNAME`
- `MCT_AUTH_SECRET`
- database credentials that are not demo defaults
- TLS email or equivalent certificate-management configuration
- persistent Docker volumes for PostgreSQL, Airflow metadata, serving artifacts, Prometheus, Grafana, and Caddy

Rollback uses two layers:

1. redeploy the prior application image;
2. restore the prior serving `current.json` pointer from backup if the new artifact was published incorrectly.

The serving publication protocol is atomic, so failed serving builds should not advance `current.json`.

## Incident Database Separation

Compose uses one PostgreSQL server with two databases:

- Airflow metadata: `${AIRFLOW_DB_NAME:-airflow}`
- Mobility Control Tower application incidents: `${MCT_DB_NAME:-mct_app}`

The application database is initialized by `docker/postgres-init/010-create-mct-app-db.sh` and migrated by the one-shot `incident-migrate` service. Production rejects SQLite incidents unless an explicit unsafe development override is set.

## Release-Proof Runtime Gate

The GitHub Actions `release-proof` job is the release-candidate runtime gate. It builds the image, starts the deterministic stack, verifies PostgreSQL-backed incidents, Airflow scheduler health, Prometheus targets/rules, Grafana provisioning, browser product smoke tests, screenshots, PostgreSQL restore, and reversible failure injection. Evidence is uploaded under `artifacts/release-evidence/`.
