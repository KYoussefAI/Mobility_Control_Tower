#!/usr/bin/env bash
set -euo pipefail

timeout_seconds="${MCT_STACK_WAIT_TIMEOUT:-240}"
deadline=$((SECONDS + timeout_seconds))
project_args=(--profile demo)

diagnostics() {
  echo "Compose service status:" >&2
  if ! docker compose "${project_args[@]}" ps >&2; then
    echo "Unable to collect compose ps output" >&2
  fi
  echo "Recent compose logs:" >&2
  if ! docker compose "${project_args[@]}" logs --tail=200 >&2; then
    echo "Unable to collect compose logs" >&2
  fi
}

check() {
  local name="$1"
  local url="$2"
  if curl -fsS "$url" >/dev/null; then
    printf '%s ready\n' "$name"
    return 0
  fi
  printf '%s not ready: %s\n' "$name" "$url" >&2
  return 1
}

while (( SECONDS < deadline )); do
  if check "api-live" "http://127.0.0.1:${API_PORT:-8000}/health/live" \
    && check "api-ready" "http://127.0.0.1:${API_PORT:-8000}/health/ready" \
    && check "dashboard" "http://127.0.0.1:${DASHBOARD_PORT:-8501}/_stcore/health" \
    && check "airflow-webserver" "http://127.0.0.1:${AIRFLOW_PORT:-8080}/health" \
    && check "metrics-exporter" "http://127.0.0.1:${MCT_METRICS_PORT:-9108}/metrics" \
    && check "prometheus" "http://127.0.0.1:${PROMETHEUS_PORT:-9090}/-/ready" \
    && check "grafana" "http://127.0.0.1:${GRAFANA_PORT:-3000}/api/health"; then
    exit 0
  fi
  sleep "${MCT_STACK_WAIT_INTERVAL:-5}"
done

diagnostics
echo "Timed out waiting for Mobility Control Tower demo stack" >&2
exit 1
