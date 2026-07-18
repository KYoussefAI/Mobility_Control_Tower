#!/usr/bin/env sh
set -eu

command="${1:-api}"
shift || true

case "$command" in
  api)
    exec python -m mobility_control_tower.cli serve-api \
      --db "${MCT_DUCKDB_PATH:-data/serving/tisseo/2026-07-17_160355/mobility_control_tower.duckdb}" \
      --host "${MCT_API_HOST:-0.0.0.0}" \
      --port "${MCT_API_PORT:-8000}" "$@"
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

