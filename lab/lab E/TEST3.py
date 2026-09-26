from pathlib import Path

project_root = Path(__file__).resolve().parents[2]

bronze_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "silver_success_bronze"
    / "phase2_lab"
    / "2026-09-02_200000"
)

bronze_run.mkdir(parents=True, exist_ok=True)

(bronze_run / "routes.txt").write_text(
    " route_id , route_short_name \n"
    " R1 , 1 \n",
    encoding="utf-8",
)

(bronze_run / "trips.txt").write_text(
    " route_id , service_id , trip_id \n"
    " R1 , WK , T1 \n",
    encoding="utf-8",
)

(bronze_run / "stop_times.txt").write_text(
    " trip_id , arrival_time , departure_time , stop_id , stop_sequence \n"
    " T1 , 25:10:00 , 25:12:00 , S1 , 1 \n"
    " T2 , invalid , 24:00:00 , S2 , 2 \n",
    encoding="utf-8",
)

(bronze_run / "calendar.txt").write_text(
    " service_id , start_date , end_date \n"
    " WK , 20260101 , 20260231 \n",
    encoding="utf-8",
)

print(bronze_run)