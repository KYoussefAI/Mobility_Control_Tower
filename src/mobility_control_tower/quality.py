"""Focused checks before dbt; SQL business assertions remain in dbt."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
    stops = (
        pd.concat([pd.read_parquet(path) for path in stop_files], ignore_index=True)
        if stop_files
        else pd.DataFrame(columns=["snapshot_id", "entity_id", "stop_sequence", "observed_delay"])
    )
    trips = (
        pd.concat([pd.read_parquet(path) for path in trip_files], ignore_index=True)
        if trip_files
        else pd.DataFrame(columns=["snapshot_id", "entity_id", "trip_id"])
    )
    delay = pd.to_numeric(stops["observed_delay"], errors="coerce")
    checks = [
        _check(
            "snapshot_id_not_null",
            stops["snapshot_id"].isna().sum() + trips["snapshot_id"].isna().sum(),
            "Parsed rows retain snapshot lineage.",
        ),
        _check("trip_id_not_null", trips["trip_id"].isna().sum(), "Tisséo Trip Updates should identify trips."),
        _check(
            "trip_update_key_unique",
            trips.duplicated(["snapshot_id", "entity_id"]).sum(),
            "A snapshot/entity pair must be unique.",
        ),
        _check(
            "stop_update_key_unique",
            stops.duplicated(["snapshot_id", "entity_id", "stop_sequence"]).sum(),
            "A snapshot/entity/stop-sequence observation must be unique.",
        ),
        _warning_check(
            "delay_sanity",
            delay.abs().gt(max_abs_delay_seconds).sum(),
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
