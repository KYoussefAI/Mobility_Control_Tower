from pathlib import Path
from zipfile import ZipFile

project_root = Path(__file__).resolve().parents[2]
root = project_root / "data" / "phase2_lab"
root.mkdir(parents=True, exist_ok=True)

with ZipFile(root / "tiny_gtfs.zip", "w") as z:
    z.writestr(
        "routes.txt",
        "route_id,route_short_name\nR1,1\n"
    )
    z.writestr(
        "trips.txt",
        "route_id,service_id,trip_id\nR1,WEEKDAY,T1\n"
    )

print(root / "tiny_gtfs.zip")