# Security Model

Phase 3 adds a minimal local-first operator security model.

Read-only analytical endpoints remain suitable for a public API when deployed behind the production reverse proxy and bounded query parameters. Incident mutations require expiring bearer tokens with the `incidents:write` scope. Tokens are HMAC signed with `MCT_AUTH_SECRET`; demo fallback secrets are allowed only outside the production profile.

Implemented controls:

- scoped bearer tokens with expiry;
- generic authentication errors for operator mutations;
- bounded API limits on collection endpoints;
- no arbitrary SQL endpoint;
- no filesystem database paths in readiness or metadata responses;
- local secret-pattern scan via `make security-check`;
- production Compose overlay requires `MCT_AUTH_SECRET` and `MCT_PUBLIC_HOSTNAME`;
- Caddy reverse proxy adds basic security headers and exposes only API/docs/dashboard paths.

Current limitations:

- no external OIDC provider is configured;
- no internet deployment was executed;
- rate limiting and dependency/container vulnerability scanners are represented by local and CI gates, not a managed WAF;
- Grafana, Prometheus, Airflow, and PostgreSQL must remain internal in production deployment.
## Incident Permissions

Incident reads require `operations:read`; incident mutations require `incidents:write`; manual evaluation requires `admin`. Mutation actors are derived from the authenticated bearer token subject and recorded in append-only incident events. Incident evidence intentionally avoids paths, secrets, SQL text, stack traces, and unbounded row samples.
# Runtime Security Checks

The release-proof workflow verifies incident mutation authorization through real API calls:

- missing bearer token cannot mutate incidents;
- `operations:read` cannot acknowledge or resolve incidents;
- `incidents:write` can acknowledge incidents and the actor is audited;
- repeated acknowledgement is idempotent and does not create duplicate acknowledgement events.

Production overlay validation asserts that PostgreSQL, Airflow, Prometheus, and the incident metrics exporter do not publish host ports. API and dashboard traffic is intended to pass through the reverse proxy, and production requires a non-demo `MCT_AUTH_SECRET`.

Demo credentials in `.env.example` are local/demo only and must not be reused for production-style deployments.
