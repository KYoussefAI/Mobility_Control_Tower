"""Understandable, intentionally limited validation of silver GTFS CSV tables."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mobility_control_tower.transformations.gtfs_silver import parse_gtfs_time, read_csv_table

TABLES = ("agency", "stops", "routes", "trips", "stop_times", "calendar", "calendar_dates")
REQUIRED_COLUMNS = {
    "agency": ("agency_name", "agency_url", "agency_timezone"),
    "stops": ("stop_id", "stop_name", "stop_lat", "stop_lon"),
    "routes": ("route_id", "route_type"),
    "trips": ("route_id", "service_id", "trip_id"),
    "stop_times": ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"),
    "calendar": ("service_id", "start_date", "end_date"),
    "calendar_dates": ("service_id", "date", "exception_type"),
}
KEY_COLUMNS = {
    "agency": ("agency_name", "agency_url", "agency_timezone"),
    "stops": ("stop_id", "stop_name", "stop_lat", "stop_lon"),
    "routes": ("route_id", "route_type"),
    "trips": ("route_id", "service_id", "trip_id"),
    "stop_times": ("trip_id", "stop_id", "stop_sequence"),
    "calendar": ("service_id", "start_date", "end_date"),
    "calendar_dates": ("service_id", "date", "exception_type"),
}
PRIMARY_IDS = {"stops": "stop_id", "routes": "route_id", "trips": "trip_id"}
VALID_ROUTE_TYPES = {str(value) for value in range(8)} | {"11", "12"}


def _check(name: str, status: str, table: str, count: int, explanation: str) -> dict[str, Any]:
    return {"check_name": name, "status": status, "table": table, "problem_count": count, "explanation": explanation}


def _status(count: int, problem_status: str = "FAIL") -> str:
    return problem_status if count else "PASS"


def _duplicate_count(rows: list[dict[str, str]], column: str) -> int:
    values = [row.get(column, "") for row in rows if row.get(column, "")]
    return len(values) - len(set(values))


def _missing_count(rows: list[dict[str, str]], columns: Iterable[str]) -> int:
    return sum(1 for row in rows for column in columns if not row.get(column, ""))


def _invalid_number(value: str, minimum: float, maximum: float) -> bool:
    try:
        number = float(value)
        return not minimum <= number <= maximum
    except (TypeError, ValueError):
        return bool(value)


def validate_tables(tables: dict[str, tuple[list[str], list[dict[str, str]]]]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for table in ("agency", "stops", "routes", "trips", "stop_times"):
        missing = int(table not in tables)
        checks.append(_check(f"{table}_table_present", _status(missing), table, missing, f"Silver {table} table must exist."))
    schedules_missing = int("calendar" not in tables and "calendar_dates" not in tables)
    checks.append(
        _check(
            "service_calendar_present",
            _status(schedules_missing),
            "calendar/calendar_dates",
            schedules_missing,
            "At least one service calendar table must exist.",
        )
    )

    row_counts = {table: len(rows) for table, (_, rows) in tables.items()}
    for table, (columns, rows) in tables.items():
        expected = REQUIRED_COLUMNS.get(table, ())
        missing_columns = [column for column in expected if column not in columns]
        if table == "routes" and "route_short_name" not in columns and "route_long_name" not in columns:
            missing_columns.append("route_short_name or route_long_name")
        checks.append(
            _check(
                f"{table}_required_columns",
                _status(len(missing_columns)),
                table,
                len(missing_columns),
                "Missing: " + ", ".join(missing_columns) if missing_columns else "All required columns are present.",
            )
        )
        available_keys = [column for column in KEY_COLUMNS.get(table, ()) if column in columns]
        missing_values = _missing_count(rows, available_keys)
        checks.append(_check(f"{table}_missing_key_values", _status(missing_values), table, missing_values, "Counts empty values in available key columns."))

    for table, column in PRIMARY_IDS.items():
        if table in tables and column in tables[table][0]:
            count = _duplicate_count(tables[table][1], column)
            checks.append(_check(f"duplicate_{column}", _status(count), table, count, f"Duplicate non-empty {column} values."))

    if "stops" in tables:
        columns, rows = tables["stops"]
        for column, minimum, maximum in (("stop_lat", -90, 90), ("stop_lon", -180, 180)):
            if column in columns:
                count = sum(_invalid_number(row.get(column, ""), minimum, maximum) for row in rows)
                checks.append(_check(f"invalid_{column}", _status(count), "stops", count, f"Values must be numeric and between {minimum} and {maximum}."))

    if "routes" in tables and "route_type" in tables["routes"][0]:
        count = sum(bool(row.get("route_type")) and row["route_type"] not in VALID_ROUTE_TYPES for row in tables["routes"][1])
        checks.append(_check("invalid_route_type", _status(count, "WARN"), "routes", count, "Expected common GTFS route_type values 0-7, 11, or 12."))

    if "stop_times" in tables:
        columns, rows = tables["stop_times"]
        for column in ("arrival_time", "departure_time"):
            if column in columns:
                count = sum(bool(row.get(column)) and parse_gtfs_time(row[column]) is None for row in rows)
                checks.append(
                    _check(f"invalid_{column}_format", _status(count), "stop_times", count, "Expected H+:MM:SS with minutes and seconds from 00 to 59.")
                )

    def references(child: str, child_column: str, parent: str, parent_column: str) -> None:
        if child not in tables or parent not in tables or child_column not in tables[child][0] or parent_column not in tables[parent][0]:
            return
        parent_ids = {row.get(parent_column, "") for row in tables[parent][1] if row.get(parent_column, "")}
        count = sum(bool(row.get(child_column)) and row[child_column] not in parent_ids for row in tables[child][1])
        checks.append(_check(f"{child}_unknown_{child_column}", _status(count), child, count, f"Values must reference {parent}.{parent_column}."))

    references("stop_times", "trip_id", "trips", "trip_id")
    references("stop_times", "stop_id", "stops", "stop_id")
    references("trips", "route_id", "routes", "route_id")

    if "trips" in tables and "service_id" in tables["trips"][0]:
        service_ids: set[str] = set()
        for table in ("calendar", "calendar_dates"):
            if table in tables and "service_id" in tables[table][0]:
                service_ids.update(row.get("service_id", "") for row in tables[table][1] if row.get("service_id", ""))
        count = sum(bool(row.get("service_id")) and row["service_id"] not in service_ids for row in tables["trips"][1])
        checks.append(_check("trips_unknown_service_id", _status(count), "trips", count, "service_id must appear in calendar or calendar_dates."))

    overall = "FAIL" if any(check["status"] == "FAIL" for check in checks) else "WARN" if any(check["status"] == "WARN" for check in checks) else "PASS"
    return {"overall_status": overall, "row_counts": row_counts, "checks": checks}


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# GTFS quality report: {report['run_id']}",
        "",
        f"Overall status: **{report['overall_status']}**",
        "",
        "## Row counts",
        "",
        "| Table | Rows |",
        "|---|---:|",
    ]
    lines.extend(f"| `{table}` | {count} |" for table, count in sorted(report["row_counts"].items()))
    lines.extend(["", "## Checks", "", "| Status | Check | Table | Problems | Explanation |", "|---|---|---|---:|---|"])
    for check in report["checks"]:
        explanation = check["explanation"].replace("|", "\\|")
        lines.append(f"| {check['status']} | `{check['check_name']}` | `{check['table']}` | {check['problem_count']} | {explanation} |")
    return "\n".join(lines) + "\n"


def validate_silver_run(silver_run: Path, reports_dir: Path = Path("data/reports")) -> tuple[Path, Path]:
    if not silver_run.is_dir():
        raise FileNotFoundError(f"Silver run directory not found: {silver_run}")
    tables = {table: read_csv_table(silver_run / f"{table}.csv") for table in TABLES if (silver_run / f"{table}.csv").is_file()}
    report = validate_tables(tables)
    report.update({"run_id": silver_run.name, "silver_run": str(silver_run), "generated_timestamp": datetime.now(timezone.utc).isoformat()})
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"gtfs_quality_{silver_run.name}.json"
    markdown_path = reports_dir / f"gtfs_quality_{silver_run.name}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    return json_path, markdown_path
