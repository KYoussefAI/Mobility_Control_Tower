from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from mobility_control_tower.config import load_source
from mobility_control_tower.static_pipeline import gtfs_time_to_seconds, preserve_static_bytes, transform_static


def test_gtfs_time_supports_after_midnight_service() -> None:
    assert gtfs_time_to_seconds("25:05:30") == 90330
    assert gtfs_time_to_seconds("") is None


def test_static_raw_bronze_and_silver(tmp_path, gtfs_zip_bytes: bytes) -> None:
    moment = datetime(2026, 1, 1, 12, tzinfo=UTC)
    raw = preserve_static_bytes(
        gtfs_zip_bytes, load_source(), tmp_path, source_url="https://example.test/gtfs.zip", ingested_at=moment
    )
    silver = transform_static(raw, tmp_path)

    raw_metadata = json.loads((raw / "metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((silver / "manifest.json").read_text(encoding="utf-8"))
    stop_times = pd.read_parquet(silver / "stop_times.parquet")

    assert (raw / "gtfs.zip").read_bytes() == gtfs_zip_bytes
    assert raw_metadata["source_url"] == "https://example.test/gtfs.zip"
    assert len(raw_metadata["sha256"]) == 64
    assert (tmp_path / "bronze" / "static" / raw.name / "routes.txt").is_file()
    assert manifest["row_counts"]["trips"] == 3
    assert stop_times.loc[stop_times["trip_id"] == "T2", "departure_seconds"].min() == 90330


def test_transform_is_idempotent_for_one_raw_run(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    assert transform_static(raw, tmp_path) == transform_static(raw, tmp_path)
