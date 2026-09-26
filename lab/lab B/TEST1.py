import hashlib
import json
from pathlib import Path

run = Path("data/phase2_lab/raw/phase2_lab/2026-08-30_083000")
raw_zip = run / "phase2_lab_gtfs.zip"

digest = hashlib.sha256(raw_zip.read_bytes()).hexdigest()
metadata = json.loads((run / "metadata.json").read_text())

print("independent :", digest)
print("metadata    :", metadata["sha256"])
print("match       :", digest == metadata["sha256"])