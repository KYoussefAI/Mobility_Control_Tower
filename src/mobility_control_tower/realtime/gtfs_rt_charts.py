"""Generate static charts for GTFS-Realtime snapshot gold tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

RT_CHART_FILES = (
    "rt_top_routes_by_avg_delay.png",
    "rt_delay_distribution.png",
    "rt_top_stops_by_avg_delay.png",
    "rt_identifier_match_rates.png",
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f"Required real-time gold table is missing: {path.name}")
    return pd.read_csv(path)


def _barh(frame: pd.DataFrame, label: str, value: str, title: str, xlabel: str, output: Path) -> None:
    data = frame.sort_values(value, ascending=True)
    fig, ax = plt.subplots(figsize=(10, max(4, min(8, 0.45 * len(data) + 1.5))))
    ax.barh(data[label], data[value], color="#7a4f9f")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def generate_rt_charts(rt_gold_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not rt_gold_run.is_dir():
        raise FileNotFoundError(f"Real-time gold run directory not found: {rt_gold_run}")
    figures_dir = reports_dir / "figures" / "realtime" / rt_gold_run.name
    figures_dir.mkdir(parents=True, exist_ok=True)

    routes = _read_csv(rt_gold_run / "rt_route_delay_snapshot.csv")
    route_plot = routes.dropna(subset=["avg_delay_seconds"]).copy()
    route_plot["route_label"] = route_plot["route_short_name"].fillna("").astype(str)
    route_plot.loc[route_plot["route_label"].str.strip().eq(""), "route_label"] = route_plot["route_id"]
    _barh(
        route_plot.sort_values("avg_delay_seconds", ascending=False).head(10),
        "route_label",
        "avg_delay_seconds",
        "Top routes by average observed delay in one snapshot",
        "Average delay seconds",
        figures_dir / "rt_top_routes_by_avg_delay.png",
    )

    fig, ax = plt.subplots(figsize=(10, 4.8))
    route_plot["avg_delay_seconds"].dropna().plot(kind="hist", bins=20, ax=ax, color="#4f8a5b")
    ax.set_title("Distribution of route average observed delays")
    ax.set_xlabel("Average delay seconds")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "rt_delay_distribution.png", dpi=150)
    plt.close(fig)

    stops = _read_csv(rt_gold_run / "rt_stop_delay_snapshot.csv")
    stop_plot = stops.dropna(subset=["avg_delay_seconds"]).copy()
    stop_plot["stop_label"] = stop_plot["stop_name"].fillna("").astype(str)
    stop_plot.loc[stop_plot["stop_label"].str.strip().eq(""), "stop_label"] = stop_plot["stop_id"]
    _barh(
        stop_plot.sort_values("avg_delay_seconds", ascending=False).head(10),
        "stop_label",
        "avg_delay_seconds",
        "Top stops by average observed delay in one snapshot",
        "Average delay seconds",
        figures_dir / "rt_top_stops_by_avg_delay.png",
    )

    compatibility = _read_csv(rt_gold_run / "rt_identifier_compatibility_snapshot.csv")
    compat_plot = compatibility.copy()
    compat_plot["match_percentage"] = pd.to_numeric(compat_plot["match_percentage"], errors="coerce").fillna(0)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(compat_plot["identifier_type"], compat_plot["match_percentage"], color="#2f6f9f")
    ax.set_ylim(0, 100)
    ax.set_title("Static/live identifier match rates")
    ax.set_ylabel("Match percentage")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "rt_identifier_match_rates.png", dpi=150)
    plt.close(fig)
    return figures_dir
