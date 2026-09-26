from datetime import datetime, timezone
from pathlib import Path

from mobility_control_tower.transformations.gtfs_silver import build_silver

project_root = Path(__file__).resolve().parents[2]

bronze_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "silver_success_bronze"
    / "phase2_lab"
    / "2026-09-02_200000"
)

silver_root = (
    project_root
    / "data"
    / "phase2_lab"
    / "silver_success_output"
)

silver_run = build_silver(
    bronze_run,
    silver_root=silver_root,
    generated_at=datetime(2026, 9, 2, 20, 30, tzinfo=timezone.utc),
)

print("Silver run:", silver_run)
print("\nFiles:")

for path in sorted(silver_run.iterdir()):
    print("-", path.name)

print("\n--- stop_times.csv ---")
print((silver_run / "stop_times.csv").read_text(encoding="utf-8"))

print("--- calendar.csv ---")
print((silver_run / "calendar.csv").read_text(encoding="utf-8"))

print("--- silver_manifest.json ---")
print((silver_run / "silver_manifest.json").read_text(encoding="utf-8"))