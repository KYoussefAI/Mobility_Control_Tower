"""Extract preserved GTFS files into a faithful bronze layer."""

from __future__ import annotations

import csv
import io
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

GTFS_FILES = (
    "agency.txt",
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "shapes.txt",
    "frequencies.txt",
)


def _members_by_basename(archive: zipfile.ZipFile) -> dict[str, str]:
    members: dict[str, str] = {}
    for name in archive.namelist():
        if not name.endswith("/"):
            members.setdefault(PurePosixPath(name).name.lower(), name)
    return members


def _inspect_csv(content: bytes, filename: str) -> tuple[list[str], int]:
    try:
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""))
        columns = next(reader, [])
        return columns, sum(1 for row in reader if row)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(f"Cannot read GTFS file '{filename}' as UTF-8 CSV: {exc}") from exc


def build_bronze(
    raw_run: Path,
    bronze_root: Path = Path("data/bronze"),
    generated_at: datetime | None = None,
) -> Path:
    """Extract selected files byte-for-byte and create a bronze manifest."""
    if not raw_run.is_dir():
        raise FileNotFoundError(f"Raw run directory not found: {raw_run}")
    zip_files = sorted(raw_run.glob("*.zip"))
    if len(zip_files) != 1:
        raise ValueError(f"Expected exactly one ZIP in {raw_run}, found {len(zip_files)}")
    if not zipfile.is_zipfile(zip_files[0]):
        raise ValueError(f"Raw archive is not a readable ZIP: {zip_files[0]}")

    source_id = raw_run.parent.name
    output_dir = bronze_root / source_id / raw_run.name
    output_dir.mkdir(parents=True, exist_ok=False)
    extracted: dict[str, dict[str, Any]] = {}
    try:
        with zipfile.ZipFile(zip_files[0]) as archive:
            members = _members_by_basename(archive)
            for filename in GTFS_FILES:
                member = members.get(filename)
                if member is None:
                    continue
                content = archive.read(member)
                columns, row_count = _inspect_csv(content, filename)
                (output_dir / filename).write_bytes(content)
                extracted[filename] = {"row_count": row_count, "columns": columns}

        raw_metadata_path = raw_run / "metadata.json"
        raw_metadata = json.loads(raw_metadata_path.read_text(encoding="utf-8")) if raw_metadata_path.is_file() else {}
        timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        manifest = {
            "source_raw_run": str(raw_run),
            "source_zip": zip_files[0].name,
            "source_zip_sha256": raw_metadata.get("sha256"),
            "generated_timestamp": timestamp.isoformat(),
            "extracted_files": extracted,
            "missing_important_files": [name for name in GTFS_FILES if name not in extracted],
        }
        (output_dir / "bronze_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(output_dir)
        raise
    return output_dir
