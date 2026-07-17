#!/usr/bin/env bash
set -euo pipefail

python -m mobility_control_tower.cli ingest-gtfs \
  --source tisseo \
  --local-zip data/raw/manual/Tisseo_GTFS.zip

echo "Use the printed raw run path with:"
echo "python -m mobility_control_tower.cli profile-gtfs --raw-run data/raw/tisseo/<run_id>"
