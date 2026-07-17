"""Compare parsed GTFS-Realtime identifiers with static silver GTFS tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _feed_type(rt_run: Path) -> str:
    manifest_path = rt_run / "realtime_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest.get("feed_type") or rt_run.parent.name
    return rt_run.parent.name


def _collect_ids(rt_run: Path, column: str) -> set[str]:
    values: set[str] = set()
    for csv_path in rt_run.glob("rt_*.csv"):
        frame = _read_csv(csv_path)
        if column in frame.columns:
            values.update(value.strip() for value in frame[column].dropna().astype(str) if value.strip())
    return values


def _static_ids(silver_run: Path, table: str, column: str) -> set[str]:
    frame = _read_csv(silver_run / f"{table}.csv")
    if column not in frame.columns:
        return set()
    return set(value.strip() for value in frame[column].dropna().astype(str) if value.strip())


def _id_check(name: str, label: str, rt_ids: set[str], static_ids: set[str], optional: bool = False) -> dict[str, Any]:
    if not rt_ids:
        status = "NOT_APPLICABLE" if optional else "WARN"
        return {
            "check_name": name,
            "status": status,
            "realtime_id_count": 0,
            "unmatched_count": 0,
            "unmatched_percentage": 0.0,
            "sample_unmatched_values": [],
            "explanation": f"No {label} values were present in the parsed real-time snapshot.",
        }
    if not static_ids:
        return {
            "check_name": name,
            "status": "FAIL",
            "realtime_id_count": len(rt_ids),
            "unmatched_count": len(rt_ids),
            "unmatched_percentage": 100.0,
            "sample_unmatched_values": sorted(rt_ids)[:10],
            "explanation": f"Static silver data does not provide {label} values for comparison.",
        }
    unmatched = sorted(rt_ids - static_ids)
    percentage = round((len(unmatched) / len(rt_ids)) * 100, 2)
    status = "PASS" if not unmatched else "WARN"
    return {
        "check_name": name,
        "status": status,
        "realtime_id_count": len(rt_ids),
        "unmatched_count": len(unmatched),
        "unmatched_percentage": percentage,
        "sample_unmatched_values": unmatched[:10],
        "explanation": f"{len(unmatched)} of {len(rt_ids)} real-time {label} values were not found in static silver data.",
    }


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def _markdown_report(report: dict[str, Any]) -> str:
    rows = []
    for check in report["checks"]:
        rows.append(
            f"| {check['check_name']} | {check['status']} | {check.get('realtime_id_count', '')} | "
            f"{check.get('unmatched_count', '')} | {check.get('unmatched_percentage', '')} | {check['explanation']} |"
        )
    table = "\n".join(["| Check | Status | RT IDs | Unmatched | Unmatched % | Explanation |", "| --- | --- | ---: | ---: | ---: | --- |", *rows])
    return f"""# GTFS-Realtime Compatibility Report

- Feed type: `{report['feed_type']}`
- Real-time run: `{report['rt_run_id']}`
- Static silver run: `{report['static_run_id']}`
- Overall status: **{report['overall_status']}**

{table}

## Interpretation

This is an exploration check. It asks whether identifiers observed in one saved GTFS-Realtime snapshot can be joined to the static silver GTFS tables. It does not require perfect matching and it is not a production real-time pipeline.
"""


def check_realtime_compatibility(silver_run: Path, rt_run: Path, reports_dir: Path = Path("data/reports")) -> tuple[Path, Path]:
    if not silver_run.is_dir():
        raise FileNotFoundError(f"Silver run directory not found: {silver_run}")
    if not rt_run.is_dir():
        raise FileNotFoundError(f"Parsed real-time run directory not found: {rt_run}")
    feed_type = _feed_type(rt_run)
    rt_route_ids = _collect_ids(rt_run, "route_id")
    rt_trip_ids = _collect_ids(rt_run, "trip_id")
    rt_stop_ids = _collect_ids(rt_run, "stop_id")
    checks = [
        {
            "check_name": "realtime_has_join_identifiers",
            "status": "PASS" if (rt_route_ids or rt_trip_ids or rt_stop_ids) else "WARN",
            "realtime_id_count": len(rt_route_ids | rt_trip_ids | rt_stop_ids),
            "unmatched_count": 0,
            "unmatched_percentage": 0.0,
            "sample_unmatched_values": [],
            "explanation": "Real-time snapshot has route_id, trip_id, or stop_id values useful for joining." if (rt_route_ids or rt_trip_ids or rt_stop_ids) else "Real-time snapshot did not expose route_id, trip_id, or stop_id values.",
        },
        _id_check("route_id_matches_static_routes", "route_id", rt_route_ids, _static_ids(silver_run, "routes", "route_id")),
        _id_check("trip_id_matches_static_trips", "trip_id", rt_trip_ids, _static_ids(silver_run, "trips", "trip_id"), optional=(feed_type == "service_alerts")),
        _id_check("stop_id_matches_static_stops", "stop_id", rt_stop_ids, _static_ids(silver_run, "stops", "stop_id")),
    ]
    report = {
        "feed_type": feed_type,
        "rt_run": str(rt_run),
        "rt_run_id": rt_run.name,
        "silver_run": str(silver_run),
        "static_run_id": silver_run.name,
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": _overall_status(checks),
        "checks": checks,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"rt_compatibility_{feed_type}_{rt_run.name}_vs_{silver_run.name}.json"
    markdown_path = reports_dir / f"rt_compatibility_{feed_type}_{rt_run.name}_vs_{silver_run.name}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown_report(report), encoding="utf-8")
    return json_path, markdown_path
