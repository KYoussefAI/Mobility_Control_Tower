from pathlib import Path
from zipfile import ZipFile

project_root = Path(__file__).resolve().parents[2]

raw_run = (
    project_root
    / "data"
    / "phase2_lab"
    / "bronze_failure_raw"
    / "phase2_lab"
    / "2026-08-30_110000"
)

raw_run.mkdir(parents=True, exist_ok=True)

zip_path = raw_run / "bad_csv_gtfs.zip"

with ZipFile(zip_path, "w") as archive:
    archive.writestr(
        "routes.txt",
        b"route_id,route_short_name\nR1,1\n",
    )

    # Valid ZIP member, deliberately invalid UTF-8 CSV bytes.
    archive.writestr(
        "trips.txt",
        b"route_id,service_id,trip_id\nR1,WEEKDAY,\xff\xfe\n",
    )

print(zip_path)