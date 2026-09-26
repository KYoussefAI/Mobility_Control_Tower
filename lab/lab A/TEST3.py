from pathlib import Path
import hashlib

project_root = Path(__file__).resolve().parents[2]

original = project_root / "data" / "phase2_lab" / "tiny_gtfs.zip"

preserved = (
    project_root
    / "data"
    / "phase2_lab"
    / "raw"
    / "phase2_lab"
    / "2026-08-30_083000"
    / "phase2_lab_gtfs.zip"
)

print("same bytes:", original.read_bytes() == preserved.read_bytes())

print(
    "same hash:",
    hashlib.sha256(original.read_bytes()).hexdigest()
    == hashlib.sha256(preserved.read_bytes()).hexdigest(),
)