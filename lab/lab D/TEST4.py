from pathlib import Path

from mobility_control_tower.transformations.gtfs_silver import read_csv_table

project_root = Path(__file__).resolve().parents[2]
lab = project_root / "data" / "phase2_lab" / "silver_reader"
lab.mkdir(parents=True, exist_ok=True)

normal = lab / "normal.txt"
normal.write_text(
    " trip_id , stop_name , arrival_time \n"
    " T1 , Central Station , 25:10:00 \n"
    " T2 ,, invalid\n",
    encoding="utf-8",
)

columns, rows = read_csv_table(normal)

print("columns:", columns)
print("row 0:", rows[0])
print("row 1:", rows[1])



