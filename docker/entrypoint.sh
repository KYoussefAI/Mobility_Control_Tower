#!/usr/bin/env sh
set -eu

command="${1:-api}"
shift || true

case "$command" in
  api)
    exec python -m mobility_control_tower.cli serve-api \
      --source "${MCT_GTFS_SOURCE:-tisseo}" \
      --serving-root "${MCT_SERVING_ROOT:-data/serving}" \
      --host "${MCT_API_HOST:-0.0.0.0}" \
      --port "${MCT_API_PORT:-8000}" "$@"
    ;;
  metrics-exporter)
    exec python -m mobility_control_tower.cli serve-metrics \
      --source "${MCT_GTFS_SOURCE:-tisseo}" \
      --feed-type "${MCT_FEED_TYPE:-trip_updates}" \
      --serving-root "${MCT_SERVING_ROOT:-data/serving}" \
      --history-root "${MCT_HISTORY_ROOT:-data/realtime_history}" \
      --watermark-root "${MCT_WATERMARK_ROOT:-data/watermarks}" \
      --quality-root "${MCT_QUALITY_ROOT:-data/quality}" \
      --host "${MCT_METRICS_HOST:-0.0.0.0}" \
      --port "${MCT_METRICS_PORT:-9108}" "$@"
    ;;
  incident-migrate)
    exec python -m mobility_control_tower.cli migrate-incident-store --json "$@"
    ;;
  demo-bootstrap)
    python scripts/bootstrap_demo.py "$@"
    python scripts/seed_demo_incidents.py
    python -m mobility_control_tower.cli evaluate-incidents \
      --evaluation-time "${MCT_DEMO_EVALUATION_TIME:-2026-07-19T15:00:00+00:00}" \
      --correlation-id "${MCT_DEMO_CORRELATION_ID:-demo-bootstrap}" \
      --json
    ;;
  dashboard)
    export MCT_API_URL="${MCT_API_URL:-http://api:${MCT_API_PORT:-8000}}"
    exec streamlit run src/mobility_control_tower/dashboard/app.py \
      --server.address=0.0.0.0 \
      --server.port="${MCT_DASHBOARD_PORT:-8501}" "$@"
    ;;
  airflow-webserver)
    exec airflow webserver --port "${MCT_AIRFLOW_PORT:-8080}" "$@"
    ;;
  airflow-scheduler)
    exec airflow scheduler "$@"
    ;;
  airflow-init)
    airflow db migrate
    airflow pools set external_feed 1 "Bounded external GTFS-Realtime feed requests"
    airflow users create \
      --username "${AIRFLOW_ADMIN_USERNAME:-admin}" \
      --password "${AIRFLOW_ADMIN_PASSWORD:-admin}" \
      --firstname Admin \
      --lastname User \
      --role Admin \
      --email "${AIRFLOW_ADMIN_EMAIL:-admin@example.com}" || true
    ;;
  cli)
    exec python -m mobility_control_tower.cli "$@"
    ;;
  *)
    exec "$command" "$@"
    ;;
esac
