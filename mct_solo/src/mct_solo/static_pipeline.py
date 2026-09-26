"""Download, preserve, extract, and normalize Tisséo GTFS Schedule data."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
import requests

from .config import SourceConfig
from .io import run_id, sha256_bytes, utc_now, write_json, write_parquet_atomic

GTFS_FILES = ("routes.txt", "trips.txt", "stops.txt", "stop_times.txt", "calendar.txt", "calendar_dates.txt")
REQUIRED_FILES = {"routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}


def _validate_archive(content: bytes) -> list[str]:
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise ValueError("Downloaded static source is not a valid ZIP archive")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
    missing = REQUIRED_FILES - set(names)
    if missing:
        raise ValueError(f"GTFS archive is missing required files: {sorted(missing)}")
    return names


def preserve_static_bytes(
    content: bytes,
    source: SourceConfig,
    root: Path,
    *,
    source_url: str | None = None,
    ingested_at: datetime | None = None,
    http_metadata: dict[str, Any] | None = None,
) -> Path:
    names = _validate_archive(content)
    moment = ingested_at or utc_now()
    destination = root / "raw" / "static" / run_id(moment)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        archive_path = destination / "gtfs.zip"
        archive_path.write_bytes(content)
        metadata = {
            "source_id": source.id,
            "source_name": source.name,
            "source_page": source.source_page,
            "source_url": source_url or source.gtfs_url,
            "licence": source.licence,
            "ingested_at": moment.isoformat(),
            "sha256": sha256_bytes(content),
            "size_bytes": len(content),
            "archive_members": names,
            "http": http_metadata or {},
        }
        write_json(destination / "metadata.json", metadata)
        (destination / "_SUCCESS").write_text("ok\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination


def download_static(source: SourceConfig, root: Path, *, timeout_seconds: int = 60) -> Path:
    response = requests.get(source.gtfs_url, timeout=timeout_seconds)
    response.raise_for_status()
    return preserve_static_bytes(
        response.content,
        source,
        root,
        source_url=response.url,
        http_metadata={
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "etag": response.headers.get("etag"),
            "last_modified": response.headers.get("last-modified"),
        },
    )


def extract_bronze(raw_run: Path, root: Path) -> Path:
    archive_path = raw_run / "gtfs.zip"
    if not archive_path.is_file():
        raise FileNotFoundError(f"Raw GTFS archive not found: {archive_path}")
    destination = root / "bronze" / "static" / raw_run.name
    if (destination / "manifest.json").is_file():
        return destination
    temporary = destination.parent / f".{destination.name}.tmp"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            available = set(archive.namelist())
            for filename in GTFS_FILES:
                if filename not in available:
                    continue
                member = PurePosixPath(filename)
                if member.name != filename:
                    raise ValueError(f"Unsafe GTFS member path: {filename}")
                (temporary / filename).write_bytes(archive.read(filename))
        metadata = json.loads((raw_run / "metadata.json").read_text(encoding="utf-8"))
        write_json(
            temporary / "manifest.json",
            {"run_id": raw_run.name, "raw_run": str(raw_run.resolve()), "source_sha256": metadata["sha256"]},
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def _read_gtfs(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype="string", keep_default_na=False)


def _columns(frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for name in names:
        if name not in result:
            result[name] = pd.NA
    return result[names]


def gtfs_time_to_seconds(value: object) -> int | None:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    parts = str(value).split(":")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid GTFS time: {value}")
    hour, minute, second = (int(part) for part in parts)
    if hour > 47 or minute > 59 or second > 59:
        raise ValueError(f"Invalid GTFS time: {value}")
    return hour * 3600 + minute * 60 + second


def _date_column(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series.replace("", pd.NA), format="%Y%m%d", errors="raise")
    return parsed.dt.date


def _normalise_tables(bronze_run: Path) -> dict[str, pd.DataFrame]:
    routes = _columns(
        _read_gtfs(bronze_run / "routes.txt"),
        ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
    )
    routes["route_type"] = pd.to_numeric(routes["route_type"], errors="coerce").astype("Int64")

    trips = _columns(
        _read_gtfs(bronze_run / "trips.txt"),
        ["trip_id", "route_id", "service_id", "trip_headsign", "direction_id"],
    )
    trips["direction_id"] = pd.to_numeric(trips["direction_id"], errors="coerce").astype("Int64")

    stops = _columns(_read_gtfs(bronze_run / "stops.txt"), ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")

    stop_times = _columns(
        _read_gtfs(bronze_run / "stop_times.txt"),
        ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"],
    )
    stop_times["stop_sequence"] = pd.to_numeric(stop_times["stop_sequence"], errors="raise").astype("int64")
    stop_times["arrival_seconds"] = stop_times["arrival_time"].map(gtfs_time_to_seconds).astype("Int64")
    stop_times["departure_seconds"] = stop_times["departure_time"].map(gtfs_time_to_seconds).astype("Int64")

    if (bronze_run / "calendar.txt").is_file():
        calendar = _columns(
            _read_gtfs(bronze_run / "calendar.txt"),
            [
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ],
        )
        for weekday in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            calendar[weekday] = pd.to_numeric(calendar[weekday], errors="raise").astype("int8")
        calendar["start_date"] = _date_column(calendar["start_date"])
        calendar["end_date"] = _date_column(calendar["end_date"])
    else:
        calendar = pd.DataFrame(
            columns=[
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ]
        )

    if (bronze_run / "calendar_dates.txt").is_file():
        calendar_dates = _columns(
            _read_gtfs(bronze_run / "calendar_dates.txt"), ["service_id", "date", "exception_type"]
        )
        calendar_dates["date"] = _date_column(calendar_dates["date"])
        calendar_dates["exception_type"] = pd.to_numeric(calendar_dates["exception_type"], errors="raise").astype(
            "int8"
        )
    else:
        calendar_dates = pd.DataFrame(columns=["service_id", "date", "exception_type"])

    return {
        "routes": routes,
        "trips": trips,
        "stops": stops,
        "stop_times": stop_times,
        "calendar": calendar,
        "calendar_dates": calendar_dates,
    }


def transform_static(raw_run: Path, root: Path) -> Path:
    bronze_run = extract_bronze(raw_run, root)
    destination = root / "silver" / "static" / raw_run.name
    if (destination / "manifest.json").is_file():
        return destination
    temporary = destination.parent / f".{destination.name}.tmp"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    try:
        tables = _normalise_tables(bronze_run)
        for name, frame in tables.items():
            write_parquet_atomic(frame, temporary / f"{name}.parquet")
        raw_metadata = json.loads((raw_run / "metadata.json").read_text(encoding="utf-8"))
        write_json(
            temporary / "manifest.json",
            {
                "run_id": raw_run.name,
                "source_id": raw_metadata["source_id"],
                "source_url": raw_metadata["source_url"],
                "source_sha256": raw_metadata["sha256"],
                "transformed_at": utc_now().isoformat(),
                "row_counts": {name: len(frame) for name, frame in tables.items()},
            },
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination
