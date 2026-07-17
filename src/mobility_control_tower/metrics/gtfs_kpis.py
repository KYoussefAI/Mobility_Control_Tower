"""Build explainable planning KPIs from silver GTFS CSV tables."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from mobility_control_tower.transformations.gtfs_silver import parse_gtfs_time


WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
OUTPUT_COLUMNS = {
    "route_daily_trips": ["service_date", "route_id", "route_short_name", "route_long_name", "route_type", "scheduled_trips_count"],
    "route_hourly_departures": ["service_date", "route_id", "route_short_name", "route_long_name", "departure_hour", "scheduled_departures_count"],
    "stop_daily_departures": ["service_date", "stop_id", "stop_name", "scheduled_departures_count"],
    "network_daily_summary": ["service_date", "active_routes_count", "scheduled_trips_count", "scheduled_stop_departures_count", "active_stops_count"],
    "route_period_summary": ["route_id", "route_short_name", "route_long_name", "route_type", "active_service_days", "total_scheduled_trips", "average_trips_per_active_day", "max_daily_trips", "first_service_date", "last_service_date"],
    "route_hourly_headway": ["service_date", "route_id", "route_short_name", "route_long_name", "departure_hour", "scheduled_departures_count", "planned_headway_minutes"],
    "route_type_daily_summary": ["service_date", "route_type", "route_type_label", "active_routes_count", "scheduled_trips_count", "scheduled_stop_departures_count"],
    "busiest_route_day": ["service_date", "route_id", "route_short_name", "route_long_name", "scheduled_trips_count", "rank"],
    "busiest_stop_day": ["service_date", "stop_id", "stop_name", "scheduled_departures_count", "rank"],
}

ROUTE_TYPE_LABELS = {
    "0": "Tram",
    "1": "Subway/Metro",
    "2": "Rail",
    "3": "Bus",
    "4": "Ferry",
    "5": "Cable tram",
    "6": "Aerial lift",
    "7": "Funicular",
}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _parse_date_series(values: pd.Series) -> pd.Series:
    compact = values.astype(str).str.strip()
    parsed = pd.to_datetime(compact, format="%Y%m%d", errors="coerce")
    iso_parsed = pd.to_datetime(compact.where(parsed.isna()), format="%Y-%m-%d", errors="coerce")
    return parsed.fillna(iso_parsed)


def expand_service_dates(
    calendar: pd.DataFrame | None,
    calendar_dates: pd.DataFrame | None,
) -> pd.DataFrame:
    """Expand regular service and apply additions/removals, returning unique service dates."""
    services: set[tuple[str, str]] = set()
    if calendar is not None and not calendar.empty:
        required = {"service_id", "start_date", "end_date", *WEEKDAYS}
        missing = sorted(required - set(calendar.columns))
        if missing:
            raise ValueError(f"calendar.csv is missing columns required for date expansion: {', '.join(missing)}")
        for row in calendar.to_dict("records"):
            start = pd.to_datetime(str(row["start_date"]), format="%Y%m%d", errors="coerce")
            end = pd.to_datetime(str(row["end_date"]), format="%Y%m%d", errors="coerce")
            if pd.isna(start) or pd.isna(end) or end < start:
                continue
            active = {index for index, weekday in enumerate(WEEKDAYS) if str(row.get(weekday, "0")) == "1"}
            for date in pd.date_range(start, end, freq="D"):
                if date.weekday() in active:
                    services.add((str(row["service_id"]), date.date().isoformat()))

    if calendar_dates is not None and not calendar_dates.empty:
        required = {"service_id", "date", "exception_type"}
        missing = sorted(required - set(calendar_dates.columns))
        if missing:
            raise ValueError(f"calendar_dates.csv is missing columns required for date expansion: {', '.join(missing)}")
        dates = _parse_date_series(calendar_dates["date"])
        for row, parsed_date in zip(calendar_dates.to_dict("records"), dates):
            if pd.isna(parsed_date):
                continue
            key = (str(row["service_id"]), parsed_date.date().isoformat())
            if str(row["exception_type"]) == "1":
                services.add(key)
            elif str(row["exception_type"]) == "2":
                services.discard(key)

    return pd.DataFrame(sorted(services), columns=["service_id", "service_date"])


def _require_columns(table: str, frame: pd.DataFrame, columns: set[str]) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"Silver table {table}.csv is missing required columns: {', '.join(missing)}")


def _route_details(routes: pd.DataFrame) -> pd.DataFrame:
    details = routes.copy()
    for column in ("route_short_name", "route_long_name", "route_type"):
        if column not in details.columns:
            details[column] = ""
    return details[["route_id", "route_short_name", "route_long_name", "route_type"]]


def compute_gold_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Compute KPI tables from already loaded silver tables."""
    calendar = tables.get("calendar")
    calendar_dates = tables.get("calendar_dates")
    if calendar is None and calendar_dates is None:
        raise ValueError("Gold KPIs require calendar.csv or calendar_dates.csv")
    for table in ("routes", "trips", "stop_times", "stops"):
        if table not in tables:
            raise ValueError(f"Gold KPIs require missing silver table: {table}.csv")

    routes, trips, stop_times, stops = (tables[name].copy() for name in ("routes", "trips", "stop_times", "stops"))
    _require_columns("routes", routes, {"route_id"})
    _require_columns("trips", trips, {"trip_id", "route_id", "service_id"})
    _require_columns("stop_times", stop_times, {"trip_id", "stop_id", "departure_time", "stop_sequence"})
    _require_columns("stops", stops, {"stop_id", "stop_name"})
    service_dates = expand_service_dates(calendar, calendar_dates)
    if service_dates.empty and (len(trips) or len(stop_times)):
        raise ValueError("Service-date expansion produced no dates for non-empty trip data")

    route_info = _route_details(routes)
    trip_base = trips[["trip_id", "route_id", "service_id"]]

    trips_by_service = trip_base.groupby(["service_id", "route_id"], as_index=False).size().rename(columns={"size": "scheduled_trips_count"})
    route_daily = service_dates.merge(trips_by_service, on="service_id", how="inner").merge(route_info, on="route_id", how="left")
    route_daily = route_daily.groupby(["service_date", "route_id", "route_short_name", "route_long_name", "route_type"], as_index=False, dropna=False)["scheduled_trips_count"].sum()
    route_daily = route_daily[OUTPUT_COLUMNS["route_daily_trips"]].sort_values(["service_date", "route_id"]).reset_index(drop=True)

    stop_times["_stop_sequence"] = pd.to_numeric(stop_times["stop_sequence"], errors="coerce")
    first_stops = stop_times.sort_values(["trip_id", "_stop_sequence"], na_position="last").drop_duplicates("trip_id", keep="first")
    if "departure_time_seconds" in first_stops.columns:
        seconds = pd.to_numeric(first_stops["departure_time_seconds"], errors="coerce")
    else:
        seconds = first_stops["departure_time"].map(parse_gtfs_time)
    first_stops = first_stops.assign(departure_hour=(seconds // 3600).astype("Int64"))
    first_stops = first_stops.dropna(subset=["departure_hour"])
    hourly_base = first_stops[["trip_id", "departure_hour"]].merge(trip_base, on="trip_id", how="inner")
    hourly_service = hourly_base.groupby(["service_id", "route_id", "departure_hour"], as_index=False).size().rename(columns={"size": "scheduled_departures_count"})
    route_hourly = service_dates.merge(hourly_service, on="service_id", how="inner").merge(route_info, on="route_id", how="left")
    route_hourly["departure_hour"] = route_hourly["departure_hour"].astype(int)
    route_hourly = route_hourly.groupby(["service_date", "route_id", "route_short_name", "route_long_name", "departure_hour"], as_index=False, dropna=False)["scheduled_departures_count"].sum()
    route_hourly = route_hourly[OUTPUT_COLUMNS["route_hourly_departures"]].sort_values(["service_date", "route_id", "departure_hour"]).reset_index(drop=True)

    departures = stop_times.loc[stop_times["departure_time"].str.strip().ne(""), ["trip_id", "stop_id"]]
    stop_service = departures.merge(trip_base[["trip_id", "service_id"]], on="trip_id", how="inner").groupby(["service_id", "stop_id"], as_index=False).size().rename(columns={"size": "scheduled_departures_count"})
    stop_names = stops[["stop_id", "stop_name"]].drop_duplicates("stop_id")
    stop_daily = service_dates.merge(stop_service, on="service_id", how="inner").merge(stop_names, on="stop_id", how="left")
    stop_daily = stop_daily.groupby(["service_date", "stop_id", "stop_name"], as_index=False, dropna=False)["scheduled_departures_count"].sum()
    stop_daily = stop_daily[OUTPUT_COLUMNS["stop_daily_departures"]].sort_values(["service_date", "stop_id"]).reset_index(drop=True)

    route_summary = route_daily.groupby("service_date", as_index=False).agg(active_routes_count=("route_id", "nunique"), scheduled_trips_count=("scheduled_trips_count", "sum"))
    stop_summary = stop_daily.groupby("service_date", as_index=False).agg(scheduled_stop_departures_count=("scheduled_departures_count", "sum"), active_stops_count=("stop_id", "nunique"))
    network_daily = route_summary.merge(stop_summary, on="service_date", how="outer").fillna(0)
    for column in OUTPUT_COLUMNS["network_daily_summary"][1:]:
        network_daily[column] = network_daily[column].astype(int)
    network_daily = network_daily[OUTPUT_COLUMNS["network_daily_summary"]].sort_values("service_date").reset_index(drop=True)

    route_period = route_daily.groupby(["route_id", "route_short_name", "route_long_name", "route_type"], as_index=False, dropna=False).agg(
        active_service_days=("service_date", "nunique"),
        total_scheduled_trips=("scheduled_trips_count", "sum"),
        average_trips_per_active_day=("scheduled_trips_count", "mean"),
        max_daily_trips=("scheduled_trips_count", "max"),
        first_service_date=("service_date", "min"),
        last_service_date=("service_date", "max"),
    )
    route_period["average_trips_per_active_day"] = route_period["average_trips_per_active_day"].round(2)
    for column in ("active_service_days", "total_scheduled_trips", "max_daily_trips"):
        route_period[column] = route_period[column].astype(int)
    route_period = route_period[OUTPUT_COLUMNS["route_period_summary"]].sort_values(["total_scheduled_trips", "route_id"], ascending=[False, True]).reset_index(drop=True)

    route_hourly_headway = route_hourly.copy()
    route_hourly_headway["planned_headway_minutes"] = 60 / route_hourly_headway["scheduled_departures_count"].where(route_hourly_headway["scheduled_departures_count"] > 0)
    route_hourly_headway["planned_headway_minutes"] = route_hourly_headway["planned_headway_minutes"].round(2)
    route_hourly_headway = route_hourly_headway[OUTPUT_COLUMNS["route_hourly_headway"]].sort_values(["service_date", "route_id", "departure_hour"]).reset_index(drop=True)

    trip_departures = departures.merge(trip_base, on="trip_id", how="inner").merge(route_info[["route_id", "route_type"]], on="route_id", how="left")
    route_type_stop_service = trip_departures.groupby(["service_id", "route_type"], as_index=False, dropna=False).size().rename(columns={"size": "scheduled_stop_departures_count"})
    route_type_stop_daily = service_dates.merge(route_type_stop_service, on="service_id", how="inner")
    route_type_stop_daily = route_type_stop_daily.groupby(["service_date", "route_type"], as_index=False, dropna=False)["scheduled_stop_departures_count"].sum()
    route_type_route_daily = route_daily.groupby(["service_date", "route_type"], as_index=False, dropna=False).agg(
        active_routes_count=("route_id", "nunique"),
        scheduled_trips_count=("scheduled_trips_count", "sum"),
    )
    route_type_daily = route_type_route_daily.merge(route_type_stop_daily, on=["service_date", "route_type"], how="left").fillna({"scheduled_stop_departures_count": 0})
    route_type_daily["route_type_label"] = route_type_daily["route_type"].astype(str).map(ROUTE_TYPE_LABELS).fillna("Unknown")
    for column in ("active_routes_count", "scheduled_trips_count", "scheduled_stop_departures_count"):
        route_type_daily[column] = route_type_daily[column].astype(int)
    route_type_daily = route_type_daily[OUTPUT_COLUMNS["route_type_daily_summary"]].sort_values(["service_date", "route_type"]).reset_index(drop=True)

    busiest_route_day = route_daily.sort_values(["scheduled_trips_count", "service_date", "route_id"], ascending=[False, True, True]).head(50).copy()
    busiest_route_day["rank"] = range(1, len(busiest_route_day) + 1)
    busiest_route_day = busiest_route_day[OUTPUT_COLUMNS["busiest_route_day"]].reset_index(drop=True)

    busiest_stop_day = stop_daily.sort_values(["scheduled_departures_count", "service_date", "stop_id"], ascending=[False, True, True]).head(50).copy()
    busiest_stop_day["rank"] = range(1, len(busiest_stop_day) + 1)
    busiest_stop_day = busiest_stop_day[OUTPUT_COLUMNS["busiest_stop_day"]].reset_index(drop=True)

    return {
        "route_daily_trips": route_daily,
        "route_hourly_departures": route_hourly,
        "stop_daily_departures": stop_daily,
        "network_daily_summary": network_daily,
        "route_period_summary": route_period,
        "route_hourly_headway": route_hourly_headway,
        "route_type_daily_summary": route_type_daily,
        "busiest_route_day": busiest_route_day,
        "busiest_stop_day": busiest_stop_day,
    }


def build_gold(silver_run: Path, gold_root: Path = Path("data/gold")) -> Path:
    if not silver_run.is_dir():
        raise FileNotFoundError(f"Silver run directory not found: {silver_run}")
    table_names = ("routes", "trips", "stop_times", "stops", "calendar", "calendar_dates")
    tables = {name: _read_csv(silver_run / f"{name}.csv") for name in table_names if (silver_run / f"{name}.csv").is_file()}
    source_id = silver_run.parent.name
    output_dir = gold_root / source_id / silver_run.name
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        outputs = compute_gold_tables(tables)
        manifest_tables: dict[str, dict[str, Any]] = {}
        for name, frame in outputs.items():
            path = output_dir / f"{name}.csv"
            frame.to_csv(path, index=False)
            manifest_tables[name] = {"file": path.name, "row_count": len(frame), "columns": list(frame.columns)}
        manifest = {
            "source_silver_run": str(silver_run),
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            "tables_created": manifest_tables,
            "kpi_definitions": {
                "route_daily_trips": {"description": "Scheduled trips per service date and route.", "static_planning_only": True},
                "route_hourly_departures": {"description": "Scheduled trip starts per service date, route, and service-day hour.", "static_planning_only": True},
                "stop_daily_departures": {"description": "Scheduled departures per service date and stop.", "static_planning_only": True},
                "network_daily_summary": {"description": "Daily active routes, scheduled trips, scheduled stop departures, and active stops.", "static_planning_only": True},
                "route_period_summary": {"description": "Route totals and averages over the GTFS service period.", "static_planning_only": True},
                "route_hourly_headway": {"description": "Approximate planned headway in minutes from scheduled trip starts per route/hour.", "static_planning_only": True},
                "route_type_daily_summary": {"description": "Daily scheduled activity summarized by GTFS route type.", "static_planning_only": True},
                "busiest_route_day": {"description": "Top 50 route/day combinations by scheduled trips.", "static_planning_only": True},
                "busiest_stop_day": {"description": "Top 50 stop/day combinations by scheduled departures.", "static_planning_only": True},
            },
            "important_assumptions": [
                "calendar weekday service is adjusted by calendar_dates additions and removals.",
                "A trip start is the row with the minimum numeric stop_sequence for that trip.",
                "Hours above 23 remain service-day hours rather than wrapping to the next date.",
                "planned_headway_minutes is 60 divided by scheduled departures in that route/hour.",
            ],
            "limitations": [
                "Metrics describe the published static schedule, not actual operations or real-time reliability.",
                "Frequency-based service is not expanded into synthetic trips.",
                "Missing or invalid departure times are excluded from departure counts.",
                "Planned headway is an hourly approximation, not real passenger waiting time.",
            ],
        }
        (output_dir / "gold_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(output_dir)
        raise
    return output_dir
