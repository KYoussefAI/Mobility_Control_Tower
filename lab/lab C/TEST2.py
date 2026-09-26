from pathlib import Path
from zipfile import ZipFile

project_root = Path(__file__).resolve().parents[2]

raw_zip = (
    project_root
    / "data/phase2_lab/raw/phase2_lab/2026-08-30_083000"
    / "phase2_lab_gtfs.zip"
)

bronze_routes = (
    project_root
    / "data/phase2_lab/bronze/phase2_lab/2026-08-30_083000"
    / "routes.txt"
)

with ZipFile(raw_zip) as archive:
    zip_bytes = archive.read("routes.txt")

bronze_bytes = bronze_routes.read_bytes()

print("same bytes:", zip_bytes == bronze_bytes)
print("ZIP bytes:", repr(zip_bytes))
print("Bronze bytes:", repr(bronze_bytes))