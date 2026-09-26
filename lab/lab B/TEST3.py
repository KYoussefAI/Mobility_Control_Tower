from datetime import datetime, timezone
from pathlib import Path

from mobility_control_tower.ingestion.gtfs_raw import preserve_gtfs_zip

source = {
    # deliberately omit "name"
    "source_page_url": "https://example.invalid/phase2-lab",
    "licence": "Lab only",
    "output_filename": "phase2_lab_gtfs.zip",
}

project_root = Path(__file__).resolve().parents[2]
run = preserve_gtfs_zip(
    project_root / "data" / "phase2_lab" / "tiny_gtfs.zip",
    source_id="phase2_lab",
    source=source,
    raw_root=Path("data/phase2_lab/raw"),
    ingestion_method="local_lab",
    ingested_at=datetime(2026, 8, 30, 9, 15, tzinfo=timezone.utc),
)

print(run)