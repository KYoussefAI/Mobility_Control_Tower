from pathlib import Path

from mobility_control_tower.transformations.gtfs_silver import read_csv_table

project_root = Path(__file__).resolve().parents[2]

lab = project_root / "data" / "phase2_lab" / "silver_reader"
lab.mkdir(parents=True, exist_ok=True)

duplicate = lab / "duplicate.txt"
duplicate.write_text(
    "trip_id, trip_id\n"
    "T1,T999\n",
    encoding="utf-8",
)

print(read_csv_table(duplicate))