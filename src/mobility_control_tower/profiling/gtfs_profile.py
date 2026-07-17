"""Create simple JSON and Markdown profiles of preserved GTFS ZIP files."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


IMPORTANT_FILES = (
    "agency.txt",
    "stops.txt",
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar.txt",
    "calendar_dates.txt",
)
COUNT_FILES = {
    "routes.txt": "number_of_routes",
    "stops.txt": "number_of_stops",
    "trips.txt": "number_of_trips",
    "stop_times.txt": "number_of_stop_times",
}


def _txt_members(archive: zipfile.ZipFile) -> dict[str, str]:
    members: dict[str, str] = {}
    for name in archive.namelist():
        if not name.endswith("/") and name.lower().endswith(".txt"):
            members.setdefault(PurePosixPath(name).name.lower(), name)
    return members


def _read_rows(archive: zipfile.ZipFile, member: str) -> tuple[list[str], list[dict[str, str]]]:
    with archive.open(member) as binary:
        text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _date_range(values: Iterable[str]) -> dict[str, str | None]:
    dates = sorted(value for value in values if value and len(value) == 8 and value.isdigit())
    return {"start_date": dates[0] if dates else None, "end_date": dates[-1] if dates else None}


def build_profile(gtfs_zip: Path, run_id: str) -> dict[str, Any]:
    if not zipfile.is_zipfile(gtfs_zip):
        raise ValueError(f"Not a valid GTFS ZIP archive: {gtfs_zip}")
    with zipfile.ZipFile(gtfs_zip) as archive:
        all_files = sorted(name for name in archive.namelist() if not name.endswith("/"))
        members = _txt_members(archive)
        file_profiles: dict[str, dict[str, Any]] = {}
        rows_by_file: dict[str, list[dict[str, str]]] = {}
        for base_name, member in sorted(members.items()):
            columns, rows = _read_rows(archive, member)
            file_profiles[base_name] = {"archive_path": member, "row_count": len(rows), "columns": columns}
            rows_by_file[base_name] = rows

    presence = {name: name in members for name in IMPORTANT_FILES}
    profile: dict[str, Any] = {
        "run_id": run_id,
        "gtfs_zip": gtfs_zip.name,
        "files_in_zip": all_files,
        "important_files_present": presence,
        "missing_important_files": [name for name, present in presence.items() if not present],
        "files": file_profiles,
    }
    for filename, metric in COUNT_FILES.items():
        profile[metric] = file_profiles.get(filename, {}).get("row_count")

    date_values: list[str] = []
    for row in rows_by_file.get("calendar.txt", []):
        date_values.extend((row.get("start_date", ""), row.get("end_date", "")))
    date_values.extend(row.get("date", "") for row in rows_by_file.get("calendar_dates.txt", []))
    profile["service_date_range"] = _date_range(date_values)
    return profile


def _markdown(profile: dict[str, Any]) -> str:
    lines = [
        f"# GTFS profile: {profile['run_id']}", "",
        f"Archive: `{profile['gtfs_zip']}`", "",
        "## Summary", "",
        "| Metric | Value |", "|---|---:|",
    ]
    for metric in ("number_of_routes", "number_of_stops", "number_of_trips", "number_of_stop_times"):
        value = profile[metric] if profile[metric] is not None else "not available"
        lines.append(f"| {metric.replace('_', ' ').title()} | {value} |")
    date_range = profile["service_date_range"]
    lines.extend([
        f"| Service start date | {date_range['start_date'] or 'not available'} |",
        f"| Service end date | {date_range['end_date'] or 'not available'} |", "",
        "## Important files", "", "| File | Present | Rows | Columns |", "|---|---|---:|---|",
    ])
    for name, present in profile["important_files_present"].items():
        details = profile["files"].get(name, {})
        columns = ", ".join(details.get("columns", [])) or "—"
        rows = details.get("row_count", "—")
        lines.append(f"| `{name}` | {'yes' if present else 'no'} | {rows} | {columns} |")
    missing = profile["missing_important_files"]
    lines.extend(["", "## Missing important files", "", ", ".join(f"`{name}`" for name in missing) if missing else "None.", ""])
    return "\n".join(lines)


def profile_raw_run(raw_run: Path, reports_dir: Path = Path("data/reports")) -> tuple[Path, Path]:
    if not raw_run.is_dir():
        raise FileNotFoundError(f"Raw run directory not found: {raw_run}")
    zip_files = sorted(raw_run.glob("*.zip"))
    if len(zip_files) != 1:
        raise ValueError(f"Expected exactly one ZIP in {raw_run}, found {len(zip_files)}")
    profile = build_profile(zip_files[0], raw_run.name)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"gtfs_profile_{raw_run.name}.json"
    markdown_path = reports_dir / f"gtfs_profile_{raw_run.name}.md"
    json_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(profile), encoding="utf-8")
    return json_path, markdown_path
