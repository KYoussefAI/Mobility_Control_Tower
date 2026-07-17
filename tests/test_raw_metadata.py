import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from mobility_control_tower.ingestion.gtfs_raw import preserve_gtfs_zip


SOURCE = {
    "name": "Test Tisséo",
    "source_page_url": "https://example.test/dataset",
    "licence": "ODbL",
    "output_filename": "Tisseo_GTFS.zip",
}


def test_metadata_and_checksum_are_created(tmp_path: Path) -> None:
    input_zip = tmp_path / "input.zip"
    with zipfile.ZipFile(input_zip, "w") as archive:
        archive.writestr("agency.txt", "agency_id,agency_name\n1,Tisseo\n")
    original = input_zip.read_bytes()

    run_dir = preserve_gtfs_zip(
        input_zip,
        "tisseo",
        SOURCE,
        tmp_path / "raw",
        ingested_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )

    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    copied = run_dir / "Tisseo_GTFS.zip"
    assert metadata_path.is_file()
    assert copied.read_bytes() == original
    assert metadata["sha256"] == hashlib.sha256(original).hexdigest()
    assert metadata["file_size_bytes"] == len(original)
    assert metadata["source_name"] == "Test Tisséo"
    assert metadata["ingestion_timestamp"] == "2026-01-02T03:04:05+00:00"
