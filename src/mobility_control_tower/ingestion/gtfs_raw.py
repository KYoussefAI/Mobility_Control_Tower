"""Preserve a GTFS archive and capture its provenance metadata."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_zip(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"GTFS ZIP not found: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Input is not a valid ZIP archive: {path}")


def preserve_gtfs_zip(
    input_zip: Path,
    source_id: str,
    source: dict[str, Any],
    raw_root: Path = Path("data/raw"),
    ingestion_method: str = "local",
    ingested_at: datetime | None = None,
) -> Path:
    """Copy an archive unchanged to a new raw run and write metadata beside it."""
    _validate_zip(input_zip)
    timestamp = ingested_at or datetime.now(timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    run_id = timestamp.strftime("%Y-%m-%d_%H%M%S")
    run_dir = raw_root / source_id / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    output_name = str(source.get("output_filename", input_zip.name))
    raw_zip = run_dir / output_name
    try:
        shutil.copyfile(input_zip, raw_zip)
        metadata = {
            "source_id": source_id,
            "source_name": source["name"],
            "source_page_url": source["source_page_url"],
            "licence": source["licence"],
            "ingestion_timestamp": timestamp.isoformat(),
            "ingestion_method": ingestion_method,
            "original_filename": input_zip.name,
            "raw_filename": raw_zip.name,
            "file_size_bytes": raw_zip.stat().st_size,
            "sha256": sha256_file(raw_zip),
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except Exception:
        shutil.rmtree(run_dir)
        raise
    return run_dir


def download_and_preserve_gtfs(
    source_id: str,
    source: dict[str, Any],
    raw_root: Path = Path("data/raw"),
) -> Path:
    """Download the configured archive to a temporary file, then preserve it."""
    download_url = source.get("download_url")
    if not download_url:
        raise ValueError(f"No download URL configured for source '{source_id}'")
    with tempfile.TemporaryDirectory() as temp_dir:
        temporary_zip = Path(temp_dir) / str(source.get("output_filename", "gtfs.zip"))
        with requests.get(str(download_url), stream=True, timeout=(10, 120)) as response:
            response.raise_for_status()
            with temporary_zip.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        return preserve_gtfs_zip(
            temporary_zip, source_id, source, raw_root, ingestion_method="download"
        )
