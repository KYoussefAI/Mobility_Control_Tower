# Observability

Compose starts Prometheus and Grafana in the `demo` profile.

Prometheus scrapes:

- `mct-api` at `api:8000/pipeline/metrics` for API request and DuckDB query metrics.
- `mct-exporter` at `metrics-exporter:9108/metrics` for durable pipeline, watermark, collection, quality, and serving metrics.
- `prometheus` itself.

The exporter reads manifests and state from disk. This avoids pretending that metrics emitted by short-lived Airflow or CLI subprocesses are shared with the API process.

Grafana is provisioned automatically from:

```text
observability/grafana/provisioning/
observability/grafana/dashboards/
```

Prometheus rules are versioned under:

```text
observability/prometheus/rules/
```

The rules cover feed freshness, incomplete snapshots, backlog, incremental refresh status, watermark age, quality failures, serving readiness, and API error/latency signals. Phase 2 does not configure Alertmanager receivers, so alerts are visible in Prometheus but are not delivered to external notification systems.
## Incident Metrics And Alerts

Prometheus observes durable incident state through bounded aggregate metrics such as `mct_incidents_active`, `mct_incidents_suppressed`, and `mct_incident_evaluation_last_success_timestamp_seconds`. Prometheus is not the incident system of record. Alert rules monitor evaluator staleness, evaluator failure, and aggregate critical incident presence without high-cardinality incident, route, stop, trip, or actor labels.
# Runtime Observability Proof

Prometheus configuration is validated with real `promtool` commands in CI:

```bash
promtool check config observability/prometheus/prometheus.yml
promtool check rules observability/prometheus/rules/*.yml
promtool test rules observability/prometheus/tests/mct_alerts.test.yml
```

Runtime verification queries Prometheus HTTP APIs and fails if required targets are missing or down. Required targets include the API, metrics exporter, and Prometheus itself. Aggregate alert rules cover evaluator staleness/failures, critical active incidents, unavailable serving artifacts, and required target outages. Incident IDs, entity IDs, route IDs, stop IDs, serving run IDs, actor IDs, and error messages are intentionally not Prometheus labels.

Grafana provisioning is verified against a running Grafana instance through `/api/health`, the provisioned Prometheus datasource, datasource health, dashboard UID `mct-operations`, expected panel titles, and a sample Prometheus-backed query. Dashboard JSON parsing alone is not accepted as provisioning proof.

Release reports are written to:

- `artifacts/runtime/prometheus-targets.json`
- `artifacts/runtime/prometheus-rules.json`
- `artifacts/runtime/grafana-report.json`
- `artifacts/release-evidence/`
