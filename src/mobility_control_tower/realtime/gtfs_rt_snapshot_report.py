"""Generate a teacher-facing report from real-time snapshot gold tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from mobility_control_tower.realtime.gtfs_rt_charts import RT_CHART_FILES


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f"Required real-time gold table is missing: {path.name}")
    return pd.read_csv(path)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows available."
    headers = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def _chart_refs(run_id: str, reports_dir: Path) -> str:
    figures = reports_dir / "figures" / "realtime" / run_id
    existing = [name for name in RT_CHART_FILES if (figures / name).is_file()]
    if not existing:
        return "No real-time chart PNG files were found for this run. Run `generate-rt-charts` first."
    return "\n".join(f"- `{figures / name}`" for name in existing)


def generate_rt_snapshot_report(rt_gold_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not rt_gold_run.is_dir():
        raise FileNotFoundError(f"Real-time gold run directory not found: {rt_gold_run}")
    run_id = rt_gold_run.name
    health = _read_csv(rt_gold_run / "rt_feed_health_snapshot.csv")
    compatibility = _read_csv(rt_gold_run / "rt_identifier_compatibility_snapshot.csv")
    routes = _read_csv(rt_gold_run / "rt_route_delay_snapshot.csv")
    stops = _read_csv(rt_gold_run / "rt_stop_delay_snapshot.csv")
    health_row = health.iloc[0].to_dict() if not health.empty else {}
    compat_note = ""
    trip_rows = compatibility.loc[compatibility["identifier_type"] == "trip_id"]
    if not trip_rows.empty and str(trip_rows.iloc[0]["status"]) == "WARN":
        compat_note = "Trip ID compatibility is WARN: some trip identifiers observed at fetch time were not found in the selected static silver GTFS run. Route and stop joins may still be useful when their match rates are stronger."

    top_routes = routes.dropna(subset=["avg_delay_seconds"]).sort_values("avg_delay_seconds", ascending=False).head(10)
    top_stops = stops.dropna(subset=["avg_delay_seconds"]).sort_values("avg_delay_seconds", ascending=False).head(10)
    report = f"""# Mobility Control Tower - GTFS-Realtime Snapshot Report

## 1. Dataset and snapshot information

- Feed type: `{health_row.get('feed_type', '')}`
- Snapshot run ID: `{run_id}`
- Fetched at: `{health_row.get('fetched_at', '')}`
- This report describes one GTFS-Realtime snapshot observed at fetch time.

## 2. What the real-time snapshot pipeline did

The pipeline preserved a raw protobuf snapshot, parsed Trip Updates into CSV tables, joined static GTFS identifiers where possible, computed snapshot delay indicators, and generated static evidence artifacts.

## 3. Feed freshness and health

{_markdown_table(health)}

## 4. Identifier compatibility with static GTFS

{_markdown_table(compatibility)}

{compat_note}

## 5. Observed delay indicators

Delay uses `arrival_delay` when available, otherwise `departure_delay`. These are snapshot delay indicators, not continuous route reliability metrics.

## 6. Routes with highest average observed delay

{_markdown_table(top_routes[["route_id", "route_short_name", "route_long_name", "stop_time_updates_count", "avg_delay_seconds", "delayed_updates_5min_count"]].head(10))}

## 7. Stops with highest average observed delay

{_markdown_table(top_stops[["stop_id", "stop_name", "stop_time_updates_count", "avg_delay_seconds", "delayed_updates_5min_count"]].head(10))}

## 8. Chart references if generated

{_chart_refs(run_id, reports_dir)}

## 9. What this proves

The project can turn a saved GTFS-Realtime snapshot into enriched diagnostic tables, feed health indicators, static/live compatibility evidence, delay indicators, and teacher-friendly charts.

## 10. What it does not prove yet

- It does not prove route reliability from a single snapshot.
- It does not prove stable delay patterns over time.
- It does not prove production readiness.

## 11. Why this is still not streaming

The workflow processes one saved `feed.pb` file at a time. There is no scheduler, message broker, database, API, dashboard, or continuous real-time monitoring system.

## 12. Next project step

Collect a few saved snapshots at different times and compare feed freshness, identifier compatibility, and delay behavior before considering any streaming design.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"realtime_snapshot_report_{run_id}.md"
    output.write_text(report, encoding="utf-8")
    return output
