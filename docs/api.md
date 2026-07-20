# Operator API

The FastAPI service exposes bounded analytical reads and scoped operator mutations over the current atomic DuckDB serving artifact. It does not expose arbitrary SQL, raw feed payloads, internal database paths, stack traces, or feed credentials.

## Health

- `GET /health/live`: process liveness only.
- `GET /health/ready`: validates the current serving pointer, manifest, DuckDB openability, and required public views.
- `GET /metadata`: lists tables and views without exposing filesystem paths.

## Source And Trust

- `GET /sources`: source capability registry, including unavailable feeds.
- `GET /data-quality/status`: latest MCT Quality Contracts summary.
- `GET /lineage/status`: honest lineage availability. Local OpenLineage-compatible events do not imply a backend is running.

## Operational Reads

- `GET /network/status`
- `GET /network/reliability`
- `GET /routes`
- `GET /routes/{route_id}/reliability`
- `GET /routes/{route_id}/headways`
- `GET /vehicles`
- `GET /alerts/active`
- `GET /incidents`

Collection endpoints enforce bounded `limit` values. Vehicle and map-style outputs are limited so stale or large artifacts cannot create unbounded responses.

Reliability endpoints read only dbt-produced serving views such as
`v_network_reliability`, `v_route_reliability`, `v_route_on_time_performance`,
and `v_headway_reliability`. If those views are absent from the current serving
artifact, the endpoint returns an unavailable response instead of recalculating
the KPI in Python or falling back to raw history.

## Operator Mutations

- `POST /incidents/{incident_id}/acknowledge`
- `POST /incidents/{incident_id}/resolve`

These require `Authorization: Bearer <token>` with the `incidents:write` scope. Tokens are expiring HMAC bearer tokens signed with `MCT_AUTH_SECRET`. Demo fallback secrets are not accepted for production-style configuration.

## Response Shape

Most read endpoints return:

```json
{
  "data": [],
  "count": 0,
  "source": "view_or_system",
  "notes": []
}
```

Operational KPI rows include calculation version, coverage, confidence, or limitations where applicable. Missing Trip Updates are represented as unknown coverage, not on-time service.
## Incident API

Versioned incident endpoints live under `/v1/incidents`. `operations:read` can list incidents, incident events, and evaluator runs. `incidents:write` can acknowledge, resolve, suppress, and unsuppress. `admin` can trigger evaluation. Manual resolution requires a nonempty reason; suppression requires a reason and expiry. Evidence is structured and excludes filesystem paths, secrets, raw SQL, and stack traces. See `docs/incidents.md`.
# Runtime API Health

The API exposes two health contracts:

- `GET /health/live` verifies the FastAPI process and HTTP server are alive.
- `GET /health/ready` verifies the current serving pointer, serving DuckDB validation, required serving views, incident repository reachability, and incident migration version.

Readiness returns non-2xx when serving data or incident persistence is unavailable. It must not be interpreted as healthy when the evaluator or repository failed.

Release-proof browser/API smoke tests verify protected incident mutations with missing, read-only, writer, and admin tokens. OpenAPI is loaded from the running demo profile and checked for incident and reliability schemas.
