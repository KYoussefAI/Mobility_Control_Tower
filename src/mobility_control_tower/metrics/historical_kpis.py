"""Build historical GTFS-Realtime KPI tables from partitioned Parquet."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _read_history(history_run: Path, file_name: str) -> pd.DataFrame:
    files = sorted(history_run.glob(f"date=*/hour=*/snapshot_timestamp=*/{file_name}"))
    if not files:
        return pd.DataFrame()
    return pd.concat((pd.read_parquet(path, engine="pyarrow") for path in files), ignore_index=True)


def _delay_seconds(stop_updates: pd.DataFrame) -> pd.Series:
    arrival = pd.to_numeric(stop_updates.get("arrival_delay", pd.Series(dtype=str)).replace("", pd.NA), errors="coerce")
    departure = pd.to_numeric(stop_updates.get("departure_delay", pd.Series(dtype=str)).replace("", pd.NA), errors="coerce")
    return arrival.combine_first(departure)


def _write_parquet_outputs(output_dir: Path, tables: dict[str, pd.DataFrame]) -> dict[str, dict[str, Any]]:
    manifest_tables: dict[str, dict[str, Any]] = {}
    for name, frame in tables.items():
        path = output_dir / f"{name}.parquet"
        frame.to_parquet(path, index=False, engine="pyarrow")
        manifest_tables[name] = {"file": path.name, "row_count": int(len(frame)), "columns": list(frame.columns)}
    return manifest_tables


def compute_historical_kpis(stop_updates: pd.DataFrame, feed_summary: pd.DataFrame) -> dict[str, pd.DataFrame]:
    stops = stop_updates.copy()
    summary = feed_summary.copy()
    if stops.empty:
        stops["delay_seconds"] = pd.Series(dtype=float)
    else:
        stops["delay_seconds"] = _delay_seconds(stops)
    for frame in (stops, summary):
        if "collection_time" in frame.columns:
            frame["collection_time"] = pd.to_datetime(frame["collection_time"], errors="coerce", utc=True)
        if "collection_hour" not in frame.columns and "collection_time" in frame.columns:
            frame["collection_hour"] = frame["collection_time"].dt.strftime("%H")
        if "collection_date" not in frame.columns and "collection_time" in frame.columns:
            frame["collection_date"] = frame["collection_time"].dt.strftime("%Y-%m-%d")

    route_delay = (
        stops.groupby("route_id", dropna=False)
        .agg(
            updates_collected=("delay_seconds", "size"),
            average_delay_seconds=("delay_seconds", "mean"),
            maximum_observed_delay_seconds=("delay_seconds", "max"),
            minimum_observed_delay_seconds=("delay_seconds", "min"),
            p95_delay_seconds=("delay_seconds", lambda values: values.dropna().quantile(0.95) if values.notna().any() else pd.NA),
            snapshots_observed=("snapshot_timestamp", "nunique"),
        )
        .reset_index()
        if not stops.empty and "route_id" in stops.columns
        else pd.DataFrame(
            columns=[
                "route_id",
                "updates_collected",
                "average_delay_seconds",
                "maximum_observed_delay_seconds",
                "minimum_observed_delay_seconds",
                "p95_delay_seconds",
                "snapshots_observed",
            ]
        )
    )
    stop_delay = (
        stops.groupby("stop_id", dropna=False)
        .agg(
            updates_collected=("delay_seconds", "size"),
            average_delay_seconds=("delay_seconds", "mean"),
            maximum_observed_delay_seconds=("delay_seconds", "max"),
            minimum_observed_delay_seconds=("delay_seconds", "min"),
            p95_delay_seconds=("delay_seconds", lambda values: values.dropna().quantile(0.95) if values.notna().any() else pd.NA),
            snapshots_observed=("snapshot_timestamp", "nunique"),
        )
        .reset_index()
        if not stops.empty and "stop_id" in stops.columns
        else pd.DataFrame(
            columns=[
                "stop_id",
                "updates_collected",
                "average_delay_seconds",
                "maximum_observed_delay_seconds",
                "minimum_observed_delay_seconds",
                "p95_delay_seconds",
                "snapshots_observed",
            ]
        )
    )
    delay_hour = (
        stops.groupby(["collection_date", "collection_hour"], dropna=False)
        .agg(
            updates_collected=("delay_seconds", "size"),
            average_delay_seconds=("delay_seconds", "mean"),
            maximum_observed_delay_seconds=("delay_seconds", "max"),
            minimum_observed_delay_seconds=("delay_seconds", "min"),
            p95_delay_seconds=("delay_seconds", lambda values: values.dropna().quantile(0.95) if values.notna().any() else pd.NA),
            snapshots_observed=("snapshot_timestamp", "nunique"),
        )
        .reset_index()
        if not stops.empty and {"collection_date", "collection_hour"}.issubset(stops.columns)
        else pd.DataFrame(
            columns=[
                "collection_date",
                "collection_hour",
                "updates_collected",
                "average_delay_seconds",
                "maximum_observed_delay_seconds",
                "minimum_observed_delay_seconds",
                "p95_delay_seconds",
                "snapshots_observed",
            ]
        )
    )
    feed_freshness = (
        summary.groupby(["collection_date", "collection_hour"], dropna=False)
        .agg(
            snapshots_collected=("snapshot_timestamp", "nunique"),
            average_feed_age_seconds=("feed_age_seconds", "mean"),
            maximum_feed_age_seconds=("feed_age_seconds", "max"),
            minimum_feed_age_seconds=("feed_age_seconds", "min"),
            parsed_entities=("parsed_entity_count", "sum"),
            skipped_entities=("skipped_entity_count", "sum"),
        )
        .reset_index()
        if not summary.empty and {"collection_date", "collection_hour"}.issubset(summary.columns)
        else pd.DataFrame(
            columns=[
                "collection_date",
                "collection_hour",
                "snapshots_collected",
                "average_feed_age_seconds",
                "maximum_feed_age_seconds",
                "minimum_feed_age_seconds",
                "parsed_entities",
                "skipped_entities",
            ]
        )
    )
    trip_match = (
        stops.groupby(["collection_date", "collection_hour"], dropna=False)
        .agg(
            updates_collected=("delay_seconds", "size"),
            distinct_trips_observed=("trip_id", pd.Series.nunique),
            distinct_routes_observed=("route_id", pd.Series.nunique),
            distinct_stops_observed=("stop_id", pd.Series.nunique),
            snapshots_observed=("snapshot_timestamp", "nunique"),
        )
        .reset_index()
        if not stops.empty and {"collection_date", "collection_hour"}.issubset(stops.columns)
        else pd.DataFrame(
            columns=[
                "collection_date",
                "collection_hour",
                "updates_collected",
                "distinct_trips_observed",
                "distinct_routes_observed",
                "distinct_stops_observed",
                "snapshots_observed",
            ]
        )
    )
    daily_summary = (
        stops.groupby("collection_date", dropna=False)
        .agg(
            updates_collected=("delay_seconds", "size"),
            average_delay_seconds=("delay_seconds", "mean"),
            maximum_observed_delay_seconds=("delay_seconds", "max"),
            minimum_observed_delay_seconds=("delay_seconds", "min"),
            p95_delay_seconds=("delay_seconds", lambda values: values.dropna().quantile(0.95) if values.notna().any() else pd.NA),
            snapshots_observed=("snapshot_timestamp", "nunique"),
            distinct_routes_observed=("route_id", pd.Series.nunique),
            distinct_stops_observed=("stop_id", pd.Series.nunique),
        )
        .reset_index()
        if not stops.empty and "collection_date" in stops.columns
        else pd.DataFrame(
            columns=[
                "collection_date",
                "updates_collected",
                "average_delay_seconds",
                "maximum_observed_delay_seconds",
                "minimum_observed_delay_seconds",
                "p95_delay_seconds",
                "snapshots_observed",
                "distinct_routes_observed",
                "distinct_stops_observed",
            ]
        )
    )
    for frame in (route_delay, stop_delay, delay_hour, feed_freshness, trip_match, daily_summary):
        for column in frame.select_dtypes(include=["float"]).columns:
            frame[column] = frame[column].round(2)
    return {
        "route_delay_history": route_delay.sort_values("average_delay_seconds", ascending=False, na_position="last").reset_index(drop=True),
        "stop_delay_history": stop_delay.sort_values("average_delay_seconds", ascending=False, na_position="last").reset_index(drop=True),
        "delay_evolution_by_hour": delay_hour.sort_values(["collection_date", "collection_hour"]).reset_index(drop=True),
        "feed_freshness_trend": feed_freshness.sort_values(["collection_date", "collection_hour"]).reset_index(drop=True),
        "trip_match_trend": trip_match.sort_values(["collection_date", "collection_hour"]).reset_index(drop=True),
        "daily_summary": daily_summary.sort_values("collection_date").reset_index(drop=True),
    }


def build_historical_kpis(history_run: Path, output_root: Path = Path("data/history_gold")) -> Path:
    if not history_run.is_dir():
        raise FileNotFoundError(f"Historical realtime directory not found: {history_run}")
    stop_updates = _read_history(history_run, "stop_time_updates.parquet")
    feed_summary = _read_history(history_run, "feed_summary.parquet")
    if stop_updates.empty and feed_summary.empty:
        raise ValueError(f"No historical Parquet files found under {history_run}")
    source_id = history_run.parent.name
    feed_type = history_run.name
    output_dir = output_root / source_id / feed_type / datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    tables = compute_historical_kpis(stop_updates, feed_summary)
    manifest_tables = _write_parquet_outputs(output_dir, tables)
    manifest = {
        "source_history_run": str(history_run),
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "tables_created": manifest_tables,
        "kpi_definitions": {
            "route_delay_history": "Average, minimum, maximum, and p95 observed delay by route over collected snapshots.",
            "stop_delay_history": "Average, minimum, maximum, and p95 observed delay by stop over collected snapshots.",
            "delay_evolution_by_hour": "Hourly delay trend from preserved snapshots.",
            "feed_freshness_trend": "Hourly feed age and parse volume trend.",
            "trip_match_trend": "Observed trip, route, and stop volume trend by hour.",
            "daily_summary": "Daily historical summary across all observed stop-time updates.",
        },
    }
    (output_dir / "history_gold_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_dir
