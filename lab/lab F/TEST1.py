from datetime import datetime, timezone
from pathlib import Path
import json
import shutil

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

root_a = project_root / "data" / "phase2_lab" / "determinism_a"
root_b = project_root / "data" / "phase2_lab" / "determinism_b"

# Disposable lab outputs only.
for root in (root_a, root_b):
    if root.exists():
        shutil.rmtree(root)

run_a = build_silver(
    bronze_run,
    silver_root=root_a,
    generated_at=datetime(
        2026, 9, 2, 21, 0,
        tzinfo=timezone.utc,
    ),
)

run_b = build_silver(
    bronze_run,
    silver_root=root_b,
    generated_at=datetime(
        2026, 9, 3, 8, 0,
        tzinfo=timezone.utc,
    ),
)

print("run A:", run_a)
print("run B:", run_b)

for filename in (
    "routes.csv",
    "trips.csv",
    "stop_times.csv",
    "calendar.csv",
):
    same = (
        (run_a / filename).read_bytes()
        == (run_b / filename).read_bytes()
    )
    print(f"{filename} identical:", same)

manifest_a_bytes = (run_a / "silver_manifest.json").read_bytes()
manifest_b_bytes = (run_b / "silver_manifest.json").read_bytes()

print(
    "manifest byte-identical:",
    manifest_a_bytes == manifest_b_bytes,
)

manifest_a = json.loads(
    (run_a / "silver_manifest.json").read_text(encoding="utf-8")
)
manifest_b = json.loads(
    (run_b / "silver_manifest.json").read_text(encoding="utf-8")
)

print(
    "A generated_timestamp:",
    manifest_a["generated_timestamp"],
)
print(
    "B generated_timestamp:",
    manifest_b["generated_timestamp"],
)

# Remove execution-specific timestamp and compare remaining manifest content.
manifest_a.pop("generated_timestamp")
manifest_b.pop("generated_timestamp")

print(
    "manifest identical without timestamp:",
    manifest_a == manifest_b,
)