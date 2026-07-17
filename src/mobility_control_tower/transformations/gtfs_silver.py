"""Create cleaned, canonical CSV tables from bronze GTFS files."""

from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SILVER_TABLES = (
    "agency",
    "stops",
    "routes",
    "trips",
    "stop_times",
    "calendar",
    "calendar_dates",
)
TIME_PATTERN = re.compile(r"^(\d{1,3}):([0-5]\d):([0-5]\d)$")


def parse_gtfs_time(value: str | None) -> int | None:
    """Return service-day seconds; GTFS hours may exceed 23."""
    if value is None:
        return None
    match = TIME_PATTERN.fullmatch(value.strip())
    if not match:
        return None
    hours, minutes, seconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def parse_gtfs_date(value: str | None) -> str | None:
    """Convert a valid GTFS YYYYMMDD date to ISO text without changing the source field."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def read_csv_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            original_columns = list(reader.fieldnames or [])
            columns = [column.strip() for column in original_columns]
            if not columns:
                raise ValueError("header is empty")
            if len(columns) != len(set(columns)):
                raise ValueError("column names are duplicated after trimming")
            rows = [
                {clean: (row.get(original) or "").strip() for original, clean in zip(original_columns, columns)}
                for row in reader
            ]
            return columns, rows
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(f"Cannot read bronze table {path}: {exc}") from exc


def write_csv_table(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_silver(
    bronze_run: Path,
    silver_root: Path = Path("data/silver"),
    generated_at: datetime | None = None,
) -> Path:
    if not bronze_run.is_dir():
        raise FileNotFoundError(f"Bronze run directory not found: {bronze_run}")
    source_id = bronze_run.parent.name
    output_dir = silver_root / source_id / bronze_run.name
    output_dir.mkdir(parents=True, exist_ok=False)
    tables: dict[str, dict[str, Any]] = {}
    try:
        for table in SILVER_TABLES:
            source_path = bronze_run / f"{table}.txt"
            if not source_path.is_file():
                continue
            columns, rows = read_csv_table(source_path)
            if table == "stop_times":
                columns.extend(["arrival_time_seconds", "departure_time_seconds"])
                for row in rows:
                    row["arrival_time_seconds"] = parse_gtfs_time(row.get("arrival_time"))
                    row["departure_time_seconds"] = parse_gtfs_time(row.get("departure_time"))
            for date_column in ("start_date", "end_date", "date"):
                if date_column in columns:
                    iso_column = f"{date_column}_iso"
                    columns.append(iso_column)
                    for row in rows:
                        row[iso_column] = parse_gtfs_date(row.get(date_column))
            output_path = output_dir / f"{table}.csv"
            write_csv_table(output_path, columns, rows)
            tables[table] = {"file": output_path.name, "row_count": len(rows), "columns": columns}

        timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        manifest = {
            "source_bronze_run": str(bronze_run),
            "generated_timestamp": timestamp.isoformat(),
            "tables_created": tables,
            "cleaning_notes": [
                "Column names and surrounding string whitespace were trimmed.",
                "Source identifiers were preserved; no identifiers were invented.",
                "Original GTFS dates and times remain strings.",
                "Valid YYYYMMDD dates also have non-destructive ISO date companion columns.",
                "Valid stop_times values also have service-day seconds columns; hours above 23 are supported.",
            ],
        }
        (output_dir / "silver_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except Exception:
        shutil.rmtree(output_dir)
        raise
    return output_dir
