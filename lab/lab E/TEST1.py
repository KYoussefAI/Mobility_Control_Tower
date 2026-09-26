from pathlib import Path

project_root = Path(__file__).resolve().parents[2]

bronze_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "silver_failure_bronze"
    / "phase2_lab"
    / "2026-09-02_190000"
)

bronze_run.mkdir(parents=True, exist_ok=True)

(bronze_run / "routes.txt").write_text(
    "route_id,route_short_name\n"
    "R1,1\n",
    encoding="utf-8",
)

(bronze_run / "trips.txt").write_text(
    "trip_id, trip_id,route_id\n"
    "T1,T999,R1\n",
    encoding="utf-8",
)

print(bronze_run)