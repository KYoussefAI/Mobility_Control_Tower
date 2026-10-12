"""Focused checks before dbt; SQL business assertions remain in dbt."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .io import utc_now, write_json


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    problem_count: int
    detail: str


def _check(name: str, problems: int, detail: str) -> Check:
    return Check(name, "PASS" if problems == 0 else "FAIL", int(problems), detail)


def _warning_check(name: str, problems: int, detail: str) -> Check:
    return Check(name, "PASS" if problems == 0 else "WARN", int(problems), detail)


def _missing(series: pd.Series) -> int:
    """Count null and blank identifiers from string-backed GTFS columns."""
    return int((series.isna() | series.astype("string").str.strip().eq("")).sum())


def validate_static(silver_run: Path, report_path: Path | None = None) -> dict[str, Any]:
    tables = {
        name: pd.read_parquet(silver_run / f"{name}.parquet")
        for name in ("routes", "trips", "stops", "stop_times", "calendar", "calendar_dates")
    }
    routes, trips, stops, stop_times = (tables[name] for name in ("routes", "trips", "stops", "stop_times"))
    checks = [
        _check("route_id_not_null", _missing(routes["route_id"]), "Every route needs an identifier."),
        _check("route_id_unique", routes["route_id"].duplicated().sum(), "Route identifiers must be unique."),
        _check("trip_id_not_null", _missing(trips["trip_id"]), "Every trip needs an identifier."),
        _check("trip_id_unique", trips["trip_id"].duplicated().sum(), "Trip identifiers must be unique."),
        _check("stop_id_not_null", _missing(stops["stop_id"]), "Every stop needs an identifier."),
        _check("stop_id_unique", stops["stop_id"].duplicated().sum(), "Stop identifiers must be unique."),
        _check(
            "stop_time_ids_not_null",
            _missing(stop_times["trip_id"]) + _missing(stop_times["stop_id"]),
            "Every stop time needs trip and stop identifiers.",
        ),
        _check(
            "trips_reference_routes",
            (~trips["route_id"].isin(routes["route_id"])).sum(),
            "Trips must reference known routes.",
        ),
        _check(
            "stop_times_reference_trips",
            (~stop_times["trip_id"].isin(trips["trip_id"])).sum(),
            "Stop times must reference known trips.",
        ),
        _check(
            "stop_times_reference_stops",
            (~stop_times["stop_id"].isin(stops["stop_id"])).sum(),
            "Stop times must reference known stops.",
        ),
        _check(
            "stop_time_key_unique",
            stop_times.duplicated(["trip_id", "stop_sequence"]).sum(),
            "A trip can have only one row per stop sequence.",
        ),
    ]
    report = _report("static", checks)
    if report_path:
        write_json(report_path, report)
    return report


def validate_realtime(
    root: Path, report_path: Path | None = None, *, max_abs_delay_seconds: int = 7200
) -> dict[str, Any]:
    stop_files = list((root / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    trip_files = list((root / "silver" / "realtime" / "trip_updates").glob("date=*/*.parquet"))

    stop_metrics = {"missing_snapshot": 0, "duplicate_rows": 0, "out_of_range": 0}
    trip_metrics = {"missing_snapshot": 0, "missing_trip": 0, "duplicate_rows": 0}
    with duckdb.connect() as connection:
        connection.execute("set memory_limit = '512MB'")
        connection.execute("set preserve_insertion_order = false")
        if stop_files:
            stop_row = connection.execute(
                """
                with source as (
                    select snapshot_id, entity_id, stop_sequence, observed_delay
                    from read_parquet(?, union_by_name = true, hive_partitioning = false)
                ),
                metrics as (
                    select
                        count(*) filter (where snapshot_id is null) as missing_snapshot,
                        count(*) filter (
                            where abs(try_cast(observed_delay as bigint)) > ?
                        ) as out_of_range
                    from source
                ),
                duplicate_metrics as (
                    select coalesce(sum(row_count - 1), 0) as duplicate_rows
                    from (
                        select count(*) as row_count
                        from source
                        group by snapshot_id, entity_id, stop_sequence
                        having count(*) > 1
                    )
                )
                select missing_snapshot, duplicate_rows, out_of_range
                from metrics cross join duplicate_metrics
                """,
                [[path.as_posix() for path in stop_files], max_abs_delay_seconds],
            ).fetchone()
            stop_metrics = dict(zip(stop_metrics, map(int, stop_row), strict=True))
        if trip_files:
            trip_row = connection.execute(
                """
                with source as (
                    select snapshot_id, entity_id, trip_id
                    from read_parquet(?, union_by_name = true, hive_partitioning = false)
                ),
                metrics as (
                    select
                        count(*) filter (where snapshot_id is null) as missing_snapshot,
                        count(*) filter (where trip_id is null) as missing_trip
                    from source
                ),
                duplicate_metrics as (
                    select coalesce(sum(row_count - 1), 0) as duplicate_rows
                    from (
                        select count(*) as row_count
                        from source
                        group by snapshot_id, entity_id
                        having count(*) > 1
                    )
                )
                select missing_snapshot, missing_trip, duplicate_rows
                from metrics cross join duplicate_metrics
                """,
                [[path.as_posix() for path in trip_files]],
            ).fetchone()
            trip_metrics = dict(zip(trip_metrics, map(int, trip_row), strict=True))

    checks = [
        _check(
            "snapshot_id_not_null",
            stop_metrics["missing_snapshot"] + trip_metrics["missing_snapshot"],
            "Parsed rows retain snapshot lineage.",
        ),
        _check("trip_id_not_null", trip_metrics["missing_trip"], "Tisséo Trip Updates should identify trips."),
        _warning_check(
            "trip_update_key_unique",
            trip_metrics["duplicate_rows"],
            "Duplicate source trip-update keys are retained in Silver and handled before analytical KPIs.",
        ),
        _warning_check(
            "stop_update_key_unique",
            stop_metrics["duplicate_rows"],
            "Duplicate source stop-update keys are retained in Silver; ambiguous keys are excluded from analytical KPIs.",
        ),
        _warning_check(
            "delay_sanity",
            stop_metrics["out_of_range"],
            f"Published delays outside ±{max_abs_delay_seconds} seconds are retained but excluded from reliability KPIs.",
        ),
    ]
    report = _report("realtime", checks)
    if report_path:
        write_json(report_path, report)
    return report


def _report(layer: str, checks: list[Check]) -> dict[str, Any]:
    statuses = {check.status for check in checks}
    return {
        "layer": layer,
        "checked_at": utc_now().isoformat(),
        "status": "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS",
        "checks": [asdict(check) for check in checks],
    }


def require_pass(report: dict[str, Any]) -> None:
    if report["status"] == "FAIL":
        failed = [check["name"] for check in report["checks"] if check["status"] == "FAIL"]
        raise ValueError(f"Quality checks failed: {', '.join(failed)}")
