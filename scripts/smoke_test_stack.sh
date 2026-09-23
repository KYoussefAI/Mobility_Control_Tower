#!/usr/bin/env bash
set -euo pipefail

api="http://127.0.0.1:${API_PORT:-8000}"
prom="http://127.0.0.1:${PROMETHEUS_PORT:-9090}"
grafana="http://127.0.0.1:${GRAFANA_PORT:-3000}"
exporter="http://127.0.0.1:${MCT_METRICS_PORT:-9108}"

curl -fsS "$api/health/live" | grep -q '"status":"live"'
curl -fsS "$api/health/ready" | grep -q '"status":"ready"'
curl -fsS "$api/static/network-overview" | grep -q '"count"'
curl -fsS "$api/history/summary" | grep -q '"count"'
curl -fsS "$exporter/metrics" | grep -q '^mct_serving_artifact_ready'
curl -fsS "$prom/-/ready" >/dev/null
curl -fsS "$prom/api/v1/targets?state=active" | grep -q '"health":"up"'
curl -fsS "$grafana/api/health" | grep -q '"database":"ok"'
curl -fsS "$grafana/api/datasources/name/Prometheus" | grep -q '"type":"prometheus"'
echo "Mobility Control Tower stack smoke test passed"
