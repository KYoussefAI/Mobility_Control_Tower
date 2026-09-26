from pathlib import Path

from mobility_control_tower.transformations.gtfs_bronze import build_bronze

project_root = Path(__file__).resolve().parents[2]

raw_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "bronze_failure_raw"
    / "phase2_lab"
    / "2026-08-30_110000"
)

bronze_root = (
    project_root
    / "data"
    / "phase2_lab"
    / "bronze_failure_output"
)

build_bronze(
    raw_run,
    bronze_root=bronze_root,
)