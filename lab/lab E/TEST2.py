from pathlib import Path

from mobility_control_tower.transformations.gtfs_silver import build_silver

project_root = Path(__file__).resolve().parents[2]

bronze_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "silver_failure_bronze"
    / "phase2_lab"
    / "2026-09-02_190000"
)

silver_root = (
    project_root
    / "data"
    / "phase2_lab"
    / "silver_failure_output"
)

build_silver(
    bronze_run,
    silver_root=silver_root,
)

# (youssef) youssef@DESKTOP-C452R6V:/mnt/d/wsl/projects/Mobility_Control_Tower/lab/lab E$ test -d /mnt/d/wsl/projects/Mobility_Control_Tower/data/phase2_lab/silver_failure_output/phase2_lab/2026-09-02_190000 \
#   && echo "SILVER RUN EXISTS" \
#   || echo "SILVER RUN ABSENT"
# SILVER RUN ABSENT
# (youssef) youssef@DESKTOP-C452R6V:/mnt/d/wsl/projects/Mobility_Control_Tower/lab/lab E$ 