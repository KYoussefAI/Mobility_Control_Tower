"""Generate a compact Markdown demonstration report from gold KPI tables."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from mobility_control_tower.reporting.charts import CHART_FILES


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows available."
    headers = [str(column) for column in frame.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def _read_csv(gold_run: Path, name: str) -> pd.DataFrame:
    path = gold_run / f"{name}.csv"
    if not path.is_file():
        raise ValueError(f"Report requires missing gold file: {path.name}")
    return pd.read_csv(path)


def _quality_summary(run_id: str, reports_dir: Path) -> tuple[str, dict[str, int] | None]:
    quality_path = reports_dir / f"gtfs_quality_{run_id}.json"
    if not quality_path.is_file():
        return "Quality summary unavailable for this run.", None
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    counts = {status: sum(check["status"] == status for check in quality.get("checks", [])) for status in ("PASS", "WARN", "FAIL")}
    text = f"Overall status: **{quality.get('overall_status', 'unknown')}**. Checks: {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL."
    return text, counts


def _chart_references(run_id: str, reports_dir: Path) -> str:
    figures_dir = reports_dir / "figures" / run_id
    if not figures_dir.is_dir():
        return "No chart PNG files were found for this run. Run `generate-static-charts` to create them."
    existing = [name for name in CHART_FILES if (figures_dir / name).is_file()]
    if not existing:
        return "No chart PNG files were found for this run. Run `generate-static-charts` to create them."
    return "\n".join(f"- `{figures_dir / name}`" for name in existing)


def generate_demo_report(gold_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not gold_run.is_dir():
        raise FileNotFoundError(f"Gold run directory not found: {gold_run}")
    required = (
        "route_daily_trips",
        "route_period_summary",
        "route_hourly_headway",
        "stop_daily_departures",
        "network_daily_summary",
        "busiest_route_day",
        "busiest_stop_day",
    )
    missing = [f"{name}.csv" for name in required if not (gold_run / f"{name}.csv").is_file()]
    if missing:
        raise ValueError(f"Demo report requires missing gold files: {', '.join(missing)}")
    route_daily = _read_csv(gold_run, "route_daily_trips")
    route_period = _read_csv(gold_run, "route_period_summary")
    headway = _read_csv(gold_run, "route_hourly_headway")
    stop_daily = _read_csv(gold_run, "stop_daily_departures")
    network = _read_csv(gold_run, "network_daily_summary")
    busiest_route_day = _read_csv(gold_run, "busiest_route_day")
    run_id = gold_run.name

    top_routes = route_period[
        ["route_id", "route_short_name", "route_long_name", "active_service_days", "total_scheduled_trips", "average_trips_per_active_day", "max_daily_trips"]
    ].head(10)
    top_stops = (
        stop_daily.groupby(["stop_id", "stop_name"], as_index=False, dropna=False)["scheduled_departures_count"]
        .sum()
        .sort_values("scheduled_departures_count", ascending=False)
        .head(10)
    )
    main_sample = route_daily.sort_values(["service_date", "scheduled_trips_count"], ascending=[True, False]).head(10)
    service_period = {
        "first_service_date": network["service_date"].min() if not network.empty else None,
        "last_service_date": network["service_date"].max() if not network.empty else None,
        "service_days": int(network["service_date"].nunique()) if not network.empty else 0,
        "total_scheduled_trips": int(network["scheduled_trips_count"].sum()) if not network.empty else 0,
        "total_scheduled_stop_departures": int(network["scheduled_stop_departures_count"].sum()) if not network.empty else 0,
    }
    headway_sample = headway.sort_values(["service_date", "route_id", "departure_hour"]).head(10)
    chart_refs = _chart_references(run_id, reports_dir)

    quality_text, _ = _quality_summary(run_id, reports_dir)

    report = f"""# Mobility Control Tower — Static GTFS Demo Report

## 1. Dataset and run information

- Dataset: Tisséo static GTFS schedule
- Run ID: `{run_id}`
- Gold directory: `{gold_run}`

## 2. What the pipeline did

The local pipeline preserved the source ZIP, profiled it, extracted bronze files, cleaned canonical silver tables, validated them, expanded GTFS service dates, and aggregated static planning KPIs.

## 3. Quality summary

{quality_text}

## 4. Service period summary

- First service date: `{service_period['first_service_date']}`
- Last service date: `{service_period['last_service_date']}`
- Service days represented: `{service_period['service_days']}`
- Scheduled trips over the GTFS service period: `{service_period['total_scheduled_trips']}`
- Scheduled stop departures over the GTFS service period: `{service_period['total_scheduled_stop_departures']}`

## 5. Main KPI: scheduled trips by route and day

This KPI counts scheduled trips at the service-date and route grain. Sample:

{_markdown_table(main_sample)}

## 6. Top routes over the full service period

The totals below are aggregated over available GTFS service dates, not per day.

{_markdown_table(top_routes)}

## 7. Busiest route/day combinations

These are the highest individual route/day combinations by scheduled trips.

{_markdown_table(busiest_route_day.head(10))}

## 8. Planned hourly departures and approximate headway

Hourly departures count scheduled trip starts, using the first stop of each trip. `planned_headway_minutes` is a planned headway approximation: `60 / scheduled_departures_count`. It is not real passenger waiting time.

{_markdown_table(headway_sample)}

## 9. Busiest stops

The totals below are scheduled departures aggregated over the GTFS service period.

{_markdown_table(top_stops)}

## 10. Network daily summary

First seven service dates:

{_markdown_table(network.sort_values('service_date').head(7))}

## 11. Chart references if generated

{chart_refs}

## 12. What this proves technically

The project can reproducibly transform a published transport archive into validated, explainable analytical tables with service-calendar logic, after-midnight GTFS semantics, manifests, reports, and static PNG evidence.

## 13. What it does not prove yet

- These are static planning KPIs, not real-time reliability KPIs.
- They count scheduled trips and scheduled departures, not actual trips.
- Planned headway approximation is not real passenger waiting time.
- Frequency-based service is not expanded.
- There is intentionally no API, database, dashboard, streaming system, or orchestration layer yet.

## 14. Next project step

Use these static planning KPIs as the baseline for the next bounded project phase. Real-time data can later compare observed service against this planned schedule.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"mobility_demo_{run_id}.md"
    output.write_text(report, encoding="utf-8")
    return output


def generate_static_mvp_report(gold_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not gold_run.is_dir():
        raise FileNotFoundError(f"Gold run directory not found: {gold_run}")
    run_id = gold_run.name
    route_period = _read_csv(gold_run, "route_period_summary")
    network = _read_csv(gold_run, "network_daily_summary")
    stop_daily = _read_csv(gold_run, "stop_daily_departures")
    manifest_path = gold_run / "gold_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"tables_created": {}}
    quality_text, quality_counts = _quality_summary(run_id, reports_dir)

    top_routes = route_period[["route_short_name", "route_long_name", "total_scheduled_trips", "active_service_days", "average_trips_per_active_day"]].head(5)
    busiest_day = network.sort_values("scheduled_trips_count", ascending=False).head(1)
    busiest_stop = (
        stop_daily.groupby(["stop_id", "stop_name"], as_index=False, dropna=False)["scheduled_departures_count"]
        .sum()
        .sort_values("scheduled_departures_count", ascending=False)
        .head(1)
    )
    table_names = (
        pd.DataFrame([{"table": name, "rows": details.get("row_count", 0)} for name, details in manifest.get("tables_created", {}).items()]).sort_values(
            "table"
        )
        if manifest.get("tables_created")
        else pd.DataFrame()
    )
    checks_sentence = quality_text
    if quality_counts:
        checks_sentence = f"{quality_counts['PASS']} checks passed, {quality_counts['WARN']} warnings, {quality_counts['FAIL']} failures."

    report = f"""# Mobility Control Tower — Static MVP Evidence

## Dataset used

Tisséo static GTFS for run `{run_id}`. The dataset describes the scheduled public-transport offer, not observed real-time operations.

## What the pipeline did

The pipeline preserved the raw ZIP, captured metadata, profiled GTFS files, extracted bronze files, created cleaned silver tables, validated data quality, and built gold static planning KPIs.

## Data-quality evidence

{checks_sentence}

## Clean tables and KPI tables produced

{_markdown_table(table_names)}

## Main numerical results

- Service period: `{network['service_date'].min()}` to `{network['service_date'].max()}`
- Scheduled trips over the GTFS service period: `{int(network['scheduled_trips_count'].sum())}`
- Scheduled stop departures over the GTFS service period: `{int(network['scheduled_stop_departures_count'].sum())}`
- Active routes in gold route summary: `{int(route_period['route_id'].nunique())}`

Top routes over the GTFS service period:

{_markdown_table(top_routes)}

Busiest service day by scheduled trips:

{_markdown_table(busiest_day)}

Busiest stop over the GTFS service period:

{_markdown_table(busiest_stop)}

## Why this is Data Engineering

The work is not only a visualization. It implements repeatable ingestion, immutable raw preservation, layered transformations, schema-aware validation, reproducible KPI tables, manifests, tests, and generated evidence from source data.

## Next logical phase

Keep the static GTFS layer as the planned-service baseline. The next phase can add another bounded capability while preserving the same raw-to-report discipline.
"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"static_mvp_evidence_{run_id}.md"
    output.write_text(report, encoding="utf-8")
    return output
