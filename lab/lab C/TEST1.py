from datetime import datetime, timezone
from pathlib import Path

from mobility_control_tower.transformations.gtfs_bronze import build_bronze

project_root = Path(__file__).resolve().parents[2]

raw_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "raw"
    / "phase2_lab"
    / "2026-08-30_083000"
)

bronze_run = build_bronze(
    raw_run,
    bronze_root=project_root / "data" / "phase2_lab" / "bronze",
    generated_at=datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
)

print(bronze_run)

for path in sorted(bronze_run.iterdir()):
    print(path.name)