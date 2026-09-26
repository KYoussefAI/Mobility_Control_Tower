"""Generate simple static PNG charts from gold KPI CSV files."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

CHART_FILES = (
    "top_routes_by_total_scheduled_trips.png",
    "network_daily_scheduled_trips.png",
    "departures_by_hour_all_routes.png",
    "top_stops_by_total_departures.png",
)


def _read_gold(gold_run: Path, name: str) -> pd.DataFrame:
    path = gold_run / f"{name}.csv"
    if not path.is_file():
        raise ValueError(f"Chart generation requires missing gold file: {path.name}")
    return pd.read_csv(path)


def _route_label(row: pd.Series) -> str:
    short_name = str(row.get("route_short_name", "")).strip()
    long_name = str(row.get("route_long_name", "")).strip()
    return short_name or long_name or str(row.get("route_id", "unknown"))


def _save_barh(frame: pd.DataFrame, label_column: str, value_column: str, title: str, xlabel: str, path: Path) -> None:
    plot_frame = frame.sort_values(value_column, ascending=True)
    height = max(4.0, min(8.0, 0.45 * len(plot_frame) + 1.5))
    fig, ax = plt.subplots(figsize=(10, height))
    ax.barh(plot_frame[label_column], plot_frame[value_column], color="#2f6f9f")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def generate_static_charts(gold_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    """Create teacher-friendly static PNG charts for a gold run."""
    if not gold_run.is_dir():
        raise FileNotFoundError(f"Gold run directory not found: {gold_run}")
    run_id = gold_run.name
    figures_dir = reports_dir / "figures" / run_id
    figures_dir.mkdir(parents=True, exist_ok=True)

    route_period = _read_gold(gold_run, "route_period_summary")
    top_routes = route_period.sort_values("total_scheduled_trips", ascending=False).head(10).copy()
    top_routes["route_label"] = top_routes.apply(_route_label, axis=1)
    _save_barh(
        top_routes,
        "route_label",
        "total_scheduled_trips",
        "Top routes by scheduled trips over the GTFS service period",
        "Scheduled trips",
        figures_dir / "top_routes_by_total_scheduled_trips.png",
    )

    network = _read_gold(gold_run, "network_daily_summary").sort_values("service_date")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(network["service_date"], network["scheduled_trips_count"], marker="o", linewidth=1.8, color="#2f6f9f")
    ax.set_title("Network scheduled trips by service date")
    ax.set_xlabel("Service date")
    ax.set_ylabel("Scheduled trips")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "network_daily_scheduled_trips.png", dpi=150)
    plt.close(fig)

    hourly = _read_gold(gold_run, "route_hourly_departures")
    hourly_total = hourly.groupby("departure_hour", as_index=False)["scheduled_departures_count"].sum().sort_values("departure_hour")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(hourly_total["departure_hour"].astype(str), hourly_total["scheduled_departures_count"], color="#4f8a5b")
    ax.set_title("Scheduled trip starts by service-day hour")
    ax.set_xlabel("Service-day hour")
    ax.set_ylabel("Scheduled departures")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "departures_by_hour_all_routes.png", dpi=150)
    plt.close(fig)

    stop_daily = _read_gold(gold_run, "stop_daily_departures")
    top_stops = stop_daily.groupby(["stop_id", "stop_name"], as_index=False, dropna=False)["scheduled_departures_count"].sum()
    top_stops = top_stops.sort_values("scheduled_departures_count", ascending=False).head(10)
    _save_barh(
        top_stops,
        "stop_name",
        "scheduled_departures_count",
        "Top stops by scheduled departures over the GTFS service period",
        "Scheduled departures",
        figures_dir / "top_stops_by_total_departures.png",
    )

    return figures_dir
