"""Build snapshot-level GTFS-Realtime gold indicators."""

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


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace("", pd.NA), errors="coerce")


def freshness_status(feed_age_seconds: Any) -> str:
    age = pd.to_numeric(pd.Series([feed_age_seconds]).replace("", pd.NA), errors="coerce").iloc[0]
    if pd.isna(age):
        return "UNKNOWN"
    if age <= 90:
        return "PASS"
    if age <= 300:
        return "WARN"
    return "FAIL"


def compatibility_status(match_percentage: float | None) -> str:
    if match_percentage is None:
        return "NOT_APPLICABLE"
    if match_percentage >= 95:
        return "PASS"
    if match_percentage >= 50:
        return "WARN"
    return "FAIL"


def _set_from_column(frame: pd.DataFrame, column: str) -> set[str]:
    if column not in frame.columns:
        return set()
    return set(value.strip() for value in frame[column].dropna().astype(str) if value.strip())


def _id_compatibility(identifier_type: str, rt_values: set[str], static_values: set[str]) -> dict[str, Any]:
    if not rt_values:
        return {
            "identifier_type": identifier_type,
            "rt_distinct_count": 0,
            "matched_static_count": 0,
            "unmatched_static_count": 0,
            "match_percentage": "",
            "status": "NOT_APPLICABLE",
            "sample_unmatched_values": "",
        }
    matched = rt_values & static_values
    unmatched = sorted(rt_values - static_values)
    pct = round((len(matched) / len(rt_values)) * 100, 2)
    return {
        "identifier_type": identifier_type,
        "rt_distinct_count": len(rt_values),
        "matched_static_count": len(matched),
        "unmatched_static_count": len(unmatched),
        "match_percentage": pct,
        "status": compatibility_status(pct),
        "sample_unmatched_values": "|".join(unmatched[:10]),
    }


def _delay_seconds(stop_updates: pd.DataFrame) -> pd.Series:
    arrival = _to_numeric(stop_updates.get("arrival_delay", pd.Series(dtype=str)))
    departure = _to_numeric(stop_updates.get("departure_delay", pd.Series(dtype=str)))
    return arrival.combine_first(departure)


def _route_info(routes: pd.DataFrame) -> pd.DataFrame:
    frame = routes.copy()
    for column in ("route_short_name", "route_long_name"):
        if column not in frame.columns:
            frame[column] = ""
    return frame[["route_id", "route_short_name", "route_long_name"]].drop_duplicates("route_id")


def _aggregate_route_delay(stop_updates: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "route_id",
        "route_short_name",
        "route_long_name",
        "stop_time_updates_count",
        "distinct_trip_updates_count",
        "distinct_stops_count",
        "avg_delay_seconds",
        "median_delay_seconds",
        "max_delay_seconds",
        "min_delay_seconds",
        "delayed_updates_5min_count",
        "delayed_updates_5min_pct",
        "early_updates_count",
        "no_delay_info_count",
    ]
    if stop_updates.empty or "route_id" not in stop_updates.columns:
        return pd.DataFrame(columns=columns)
    frame = stop_updates.copy()
    frame["delay_seconds"] = _delay_seconds(frame)
    rows: list[dict[str, Any]] = []
    for route_id, group in frame.groupby("route_id", dropna=False):
        total = len(group)
        delays = group["delay_seconds"].dropna()
        delayed_count = int((delays >= 300).sum())
        rows.append(
            {
                "route_id": route_id,
                "stop_time_updates_count": total,
                "distinct_trip_updates_count": group["trip_id"].replace("", pd.NA).dropna().nunique() if "trip_id" in group else 0,
                "distinct_stops_count": group["stop_id"].replace("", pd.NA).dropna().nunique() if "stop_id" in group else 0,
                "avg_delay_seconds": round(float(delays.mean()), 2) if not delays.empty else "",
                "median_delay_seconds": round(float(delays.median()), 2) if not delays.empty else "",
                "max_delay_seconds": int(delays.max()) if not delays.empty else "",
                "min_delay_seconds": int(delays.min()) if not delays.empty else "",
                "delayed_updates_5min_count": delayed_count,
                "delayed_updates_5min_pct": round((delayed_count / total) * 100, 2) if total else 0.0,
                "early_updates_count": int((delays < 0).sum()),
                "no_delay_info_count": int(group["delay_seconds"].isna().sum()),
            }
        )
    result = pd.DataFrame(rows).merge(_route_info(routes), on="route_id", how="left")
    return result[columns].sort_values(["avg_delay_seconds", "stop_time_updates_count"], ascending=[False, False], na_position="last").reset_index(drop=True)


def _aggregate_stop_delay(stop_updates: pd.DataFrame, stops: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "stop_id",
        "stop_name",
        "stop_time_updates_count",
        "distinct_routes_count",
        "distinct_trip_updates_count",
        "avg_delay_seconds",
        "median_delay_seconds",
        "max_delay_seconds",
        "delayed_updates_5min_count",
        "delayed_updates_5min_pct",
        "no_delay_info_count",
        "stop_id_static_match",
    ]
    if stop_updates.empty or "stop_id" not in stop_updates.columns:
        return pd.DataFrame(columns=columns)
    frame = stop_updates.copy()
    frame["delay_seconds"] = _delay_seconds(frame)
    static_stop_ids = _set_from_column(stops, "stop_id")
    stop_names = stops[["stop_id", "stop_name"]].drop_duplicates("stop_id") if {"stop_id", "stop_name"}.issubset(stops.columns) else pd.DataFrame(columns=["stop_id", "stop_name"])
    rows: list[dict[str, Any]] = []
    for stop_id, group in frame.groupby("stop_id", dropna=False):
        total = len(group)
        delays = group["delay_seconds"].dropna()
        delayed_count = int((delays >= 300).sum())
        rows.append(
            {
                "stop_id": stop_id,
                "stop_time_updates_count": total,
                "distinct_routes_count": group["route_id"].replace("", pd.NA).dropna().nunique() if "route_id" in group else 0,
                "distinct_trip_updates_count": group["trip_id"].replace("", pd.NA).dropna().nunique() if "trip_id" in group else 0,
                "avg_delay_seconds": round(float(delays.mean()), 2) if not delays.empty else "",
                "median_delay_seconds": round(float(delays.median()), 2) if not delays.empty else "",
                "max_delay_seconds": int(delays.max()) if not delays.empty else "",
                "delayed_updates_5min_count": delayed_count,
                "delayed_updates_5min_pct": round((delayed_count / total) * 100, 2) if total else 0.0,
                "no_delay_info_count": int(group["delay_seconds"].isna().sum()),
                "stop_id_static_match": stop_id in static_stop_ids if stop_id else False,
            }
        )
    result = pd.DataFrame(rows).merge(stop_names, on="stop_id", how="left")
    return result[columns].sort_values(["avg_delay_seconds", "stop_time_updates_count"], ascending=[False, False], na_position="last").reset_index(drop=True)


def _feed_health(summary: pd.DataFrame, trips: pd.DataFrame, stops: pd.DataFrame) -> pd.DataFrame:
    row = summary.iloc[0].to_dict() if not summary.empty else {}
    delay = _delay_seconds(stops) if not stops.empty else pd.Series(dtype=float)
    feed_age = row.get("feed_age_seconds", "")
    return pd.DataFrame(
        [
            {
                "feed_type": row.get("feed_type", ""),
                "fetched_at": row.get("fetched_at", ""),
                "header_timestamp": row.get("header_timestamp", ""),
                "feed_age_seconds": feed_age,
                "freshness_status": freshness_status(feed_age),
                "entity_count": row.get("entity_count", ""),
                "parsed_entity_count": row.get("parsed_entity_count", ""),
                "skipped_entity_count": row.get("skipped_entity_count", ""),
                "distinct_route_ids": len(_set_from_column(pd.concat([trips, stops], ignore_index=True), "route_id")),
                "distinct_trip_ids": len(_set_from_column(pd.concat([trips, stops], ignore_index=True), "trip_id")),
                "distinct_stop_ids": len(_set_from_column(stops, "stop_id")),
                "has_delay_information": bool(delay.notna().any()),
                "notes": "Snapshot health indicator only; not a service-level guarantee.",
            }
        ]
    )


def _enrich_trip_updates(trips: pd.DataFrame, routes: pd.DataFrame, static_trips: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "entity_id",
        "trip_id",
        "route_id",
        "route_short_name",
        "route_long_name",
        "start_date",
        "start_time",
        "schedule_relationship",
        "trip_update_timestamp",
        "stop_time_update_count",
        "route_id_static_match",
        "trip_id_static_match",
        "compatibility_note",
    ]
    if trips.empty:
        return pd.DataFrame(columns=columns)
    route_ids = _set_from_column(routes, "route_id")
    trip_ids = _set_from_column(static_trips, "trip_id")
    enriched = trips.copy().merge(_route_info(routes), on="route_id", how="left")
    enriched["route_id_static_match"] = enriched["route_id"].apply(lambda value: bool(str(value).strip()) and str(value).strip() in route_ids)
    enriched["trip_id_static_match"] = enriched["trip_id"].apply(lambda value: bool(str(value).strip()) and str(value).strip() in trip_ids)

    def note(row: pd.Series) -> str:
        if not str(row.get("trip_id", "")).strip():
            return "trip_id missing in snapshot"
        if not row["trip_id_static_match"]:
            return "trip_id not found in static silver trips"
        if not row["route_id_static_match"]:
            return "route_id not found in static silver routes"
        return "matched static identifiers"

    enriched["compatibility_note"] = enriched.apply(note, axis=1)
    return enriched[columns]


def compute_rt_gold_tables(silver_tables: dict[str, pd.DataFrame], rt_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    summary = rt_tables.get("rt_feed_summary", pd.DataFrame())
    trips = rt_tables.get("rt_trip_updates", pd.DataFrame())
    stop_updates = rt_tables.get("rt_stop_time_updates", pd.DataFrame())
    routes = silver_tables.get("routes", pd.DataFrame())
    static_trips = silver_tables.get("trips", pd.DataFrame())
    stops = silver_tables.get("stops", pd.DataFrame())

    if not summary.empty and str(summary.iloc[0].get("feed_type", "")) != "trip_updates":
        raise ValueError("Real-time gold currently supports Trip Updates snapshots only")
    compatibility = pd.DataFrame(
        [
            _id_compatibility("route_id", _set_from_column(pd.concat([trips, stop_updates], ignore_index=True), "route_id"), _set_from_column(routes, "route_id")),
            _id_compatibility("trip_id", _set_from_column(pd.concat([trips, stop_updates], ignore_index=True), "trip_id"), _set_from_column(static_trips, "trip_id")),
            _id_compatibility("stop_id", _set_from_column(stop_updates, "stop_id"), _set_from_column(stops, "stop_id")),
        ]
    )
    return {
        "rt_feed_health_snapshot": _feed_health(summary, trips, stop_updates),
        "rt_trip_update_enriched": _enrich_trip_updates(trips, routes, static_trips),
        "rt_route_delay_snapshot": _aggregate_route_delay(stop_updates, routes),
        "rt_stop_delay_snapshot": _aggregate_stop_delay(stop_updates, stops),
        "rt_identifier_compatibility_snapshot": compatibility,
    }


def build_rt_gold(silver_run: Path, rt_run: Path, output_root: Path = Path("data/realtime_gold")) -> Path:
    if not silver_run.is_dir():
        raise FileNotFoundError(f"Silver run directory not found: {silver_run}")
    if not rt_run.is_dir():
        raise FileNotFoundError(f"Parsed real-time run directory not found: {rt_run}")
    silver_tables = {name: _read_csv(silver_run / f"{name}.csv") for name in ("routes", "trips", "stops")}
    rt_tables = {path.stem: _read_csv(path) for path in rt_run.glob("rt_*.csv")}
    manifest_path = rt_run / "realtime_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    feed_type = manifest.get("feed_type") or rt_run.parent.name
    source_id = rt_run.parents[1].name
    output_dir = output_root / source_id / feed_type / rt_run.name
    output_dir.mkdir(parents=True, exist_ok=False)
    outputs = compute_rt_gold_tables(silver_tables, rt_tables)
    manifest_tables: dict[str, dict[str, Any]] = {}
    for name, frame in outputs.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)
        manifest_tables[name] = {"file": f"{name}.csv", "row_count": len(frame), "columns": list(frame.columns)}
    health = outputs["rt_feed_health_snapshot"].iloc[0].to_dict()
    compatibility = outputs["rt_identifier_compatibility_snapshot"].set_index("identifier_type")["status"].to_dict()
    rt_manifest = {
        "static_silver_run": str(silver_run),
        "realtime_parsed_run": str(rt_run),
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "tables_created": manifest_tables,
        "kpi_definitions": {
            "rt_feed_health_snapshot": "Freshness, entity counts, identifier counts, and delay availability for one GTFS-Realtime snapshot.",
            "rt_trip_update_enriched": "Trip updates joined with static route/trip identifiers where possible.",
            "rt_route_delay_snapshot": "Observed delay indicators by route in one snapshot.",
            "rt_stop_delay_snapshot": "Observed delay indicators by stop in one snapshot.",
            "rt_identifier_compatibility_snapshot": "Identifier match rates between parsed snapshot and static silver GTFS.",
        },
        "assumptions": [
            "Arrival delay is preferred over departure delay when both are available.",
            "Delay metrics describe only the saved GTFS-Realtime snapshot.",
            "Identifier matching uses exact string equality against silver routes, trips, and stops.",
        ],
        "limitations": [
            "This is not continuous streaming and not route reliability.",
            "A single snapshot cannot prove recurring delay patterns.",
            "Trip IDs may be unmatched even when route and stop IDs match.",
        ],
        "compatibility_summary": compatibility,
        "feed_health_summary": health,
    }
    (output_dir / "rt_gold_manifest.json").write_text(json.dumps(rt_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_dir
