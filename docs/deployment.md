# Local Container Runtime

The multi-stage Docker image runs as a non-root user. Docker Compose wires the
API, dashboard, PostgreSQL incident store, and Airflow services on one developer
host with health checks and named volumes.

```bash
docker compose --profile core config
docker compose --profile core up --build -d
docker compose --profile core ps
docker compose --profile core down
```

Copy `.env.example` to `.env` and change demo credentials before any shared-host
use. This is a reproducible local platform, not a highly available or distributed
deployment.
