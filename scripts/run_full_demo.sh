#!/usr/bin/env bash
set -euo pipefail

echo "Mobility Control Tower full demo guide"
echo
echo "Run these commands step by step. Replace <static_run_id> and <rt_run_id> with printed run IDs."
echo
echo "1. pytest"
echo "2. python -m mobility_control_tower.cli ingest-gtfs --source tisseo --download"
echo "3. python -m mobility_control_tower.cli profile-gtfs --raw-run data/raw/tisseo/<static_run_id>"
echo "4. python -m mobility_control_tower.cli build-bronze --raw-run data/raw/tisseo/<static_run_id>"
echo "5. python -m mobility_control_tower.cli build-silver --bronze-run data/bronze/tisseo/<static_run_id>"
echo "6. python -m mobility_control_tower.cli validate-gtfs --silver-run data/silver/tisseo/<static_run_id>"
echo "7. python -m mobility_control_tower.cli build-gold --silver-run data/silver/tisseo/<static_run_id>"
echo "8. python -m mobility_control_tower.cli fetch-gtfs-rt --source tisseo --feed-type trip_updates"
echo "9. python -m mobility_control_tower.cli parse-gtfs-rt --raw-rt-run data/raw_realtime/tisseo/trip_updates/<rt_run_id>"
echo "10. python -m mobility_control_tower.cli build-rt-gold --silver-run data/silver/tisseo/<static_run_id> --rt-run data/realtime/tisseo/trip_updates/<rt_run_id>"
echo "11. python -m mobility_control_tower.cli build-serving-db --gold-run data/gold/tisseo/<static_run_id> --rt-gold-run data/realtime_gold/tisseo/trip_updates/<rt_run_id>"
echo "12. python -m mobility_control_tower.cli serve-api --db data/serving/tisseo/<static_run_id>/mobility_control_tower.duckdb"
echo "13. streamlit run src/mobility_control_tower/dashboard/app.py"
echo "14. python -m mobility_control_tower.cli generate-final-report --serving-run data/serving/tisseo/<static_run_id>"
