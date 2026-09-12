"""Generate Markdown reports for parsed GTFS-Realtime snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _manifest(rt_run: Path) -> dict:
    path = rt_run / "realtime_manifest.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _count_distinct(rt_run: Path, column: str) -> int:
    values: set[str] = set()
    for csv_path in rt_run.glob("rt_*.csv"):
        frame = _read_csv(csv_path)
        if column in frame.columns:
            values.update(value.strip() for value in frame[column].astype(str) if value.strip())
    return len(values)


def _table_counts(rt_run: Path) -> str:
    rows = []
    for csv_path in sorted(rt_run.glob("rt_*.csv")):
        frame = _read_csv(csv_path)
        rows.append(f"| {csv_path.name} | {len(frame)} |")
    if not rows:
        return "No parsed CSV tables found."
    return "\n".join(["| Table | Rows |", "| --- | ---: |", *rows])


def _observations(summary: pd.Series, route_count: int, trip_count: int, stop_count: int) -> str:
    observations = []
    age = summary.get("feed_age_seconds", "")
    try:
        age_value = float(age)
    except (TypeError, ValueError):
        age_value = None
    if age_value is None:
        observations.append("- Feed age could not be computed from this snapshot.")
    elif age_value <= 300:
        observations.append("- Feed age was under five minutes at fetch time, so it looks fresh enough for later exploration.")
    else:
        observations.append("- Feed age was over five minutes at fetch time; freshness should be checked again before later phases.")
    if route_count or trip_count or stop_count:
        observations.append("- The snapshot exposes identifiers that may be useful for joining with static GTFS.")
    else:
        observations.append("- The snapshot did not expose route_id, trip_id, or stop_id values in parsed tables.")
    return "\n".join(observations)


def generate_realtime_report(rt_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not rt_run.is_dir():
        raise FileNotFoundError(f"Parsed real-time run directory not found: {rt_run}")
    manifest = _manifest(rt_run)
    feed_type = manifest.get("feed_type") or rt_run.parent.name
    summary = _read_csv(rt_run / "rt_feed_summary.csv")
    if summary.empty:
        raise ValueError(f"Parsed real-time run is missing rt_feed_summary.csv: {rt_run}")
    row = summary.iloc[0]
    route_count = _count_distinct(rt_run, "route_id")
    trip_count = _count_distinct(rt_run, "trip_id")
    stop_count = _count_distinct(rt_run, "stop_id")
    feed_age = row.get("feed_age_seconds", "")
    usable = "candidate for later real-time phase" if (route_count or trip_count or stop_count) else "limited candidate until identifiers are available"
    report = f"""# GTFS-Realtime Snapshot Report

## 1. Feed type

`{feed_type}`

## 2. Snapshot time

Fetched at: `{row.get('fetched_at', '')}`

## 3. Header timestamp

- Raw timestamp: `{row.get('header_timestamp', '')}`
- ISO timestamp: `{row.get('header_timestamp_iso', '')}`

## 4. Feed age

`{feed_age}` seconds, if computable from the header timestamp and fetch timestamp.

## 5. Number of entities

- Entities in protobuf snapshot: `{row.get('entity_count', '')}`
- Parsed entities: `{row.get('parsed_entity_count', '')}`
- Skipped entities: `{row.get('skipped_entity_count', '')}`

## 6. Parsed table row counts

{_table_counts(rt_run)}

## 7. Main available identifiers

- Distinct route_id values: `{route_count}`
- Distinct trip_id values: `{trip_count}`
- Distinct stop_id values: `{stop_count}`

## 8. Observations

{_observations(row, route_count, trip_count, stop_count)}

## 9. Limitations

- This report describes one saved GTFS-Realtime snapshot, not a stream.
- Values are observed at fetch time and may change seconds later.
- It is not a production real-time pipeline.

## 10. Later-phase usability

This feed is a `{usable}`. Compatibility with static GTFS should be checked before building any real-time metrics.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"gtfs_rt_report_{feed_type}_{rt_run.name}.md"
    output.write_text(report, encoding="utf-8")
    return output
