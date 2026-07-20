"""Diagnostic reliability helpers.

Authoritative production reliability KPIs are dbt Gold models. This module is
kept only for fixture tests, local benchmarking, and migration reconciliation;
API, dashboard, serving publication, and incident inputs must not call these
helpers to calculate production KPI values.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any

import pandas as pd

CALCULATION_VERSION = "reliability_v1"


@dataclass(frozen=True)
class OnTimeThresholds:
    early_seconds: int = -60
    late_seconds: int = 300


DEFAULT_ON_TIME_THRESHOLDS = OnTimeThresholds()


def _percent(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round((numerator / denominator) * 100, 2)


def realtime_coverage(
    eligible_trips: pd.DataFrame, trip_updates: pd.DataFrame, *, source: str, service_date: str, route_id: str | None = None
) -> dict[str, Any]:
    """Coverage is observed eligible scheduled trips divided by eligible scheduled trips.

    Missing Trip Updates remain unobserved; they are not counted as on-time and not counted as canceled.
    """
    eligible = eligible_trips.copy()
    observed = trip_updates.copy()
    if route_id is not None:
        if "route_id" in eligible.columns:
            eligible = eligible[eligible["route_id"].astype(str) == route_id]
        if "route_id" in observed.columns:
            observed = observed[observed["route_id"].astype(str) == route_id]
    eligible_trip_ids = set(eligible["trip_id"].dropna().astype(str))
    observed_trip_ids = set(observed["trip_id"].dropna().astype(str)) & eligible_trip_ids
    unmatched = set(observed["trip_id"].dropna().astype(str)) - eligible_trip_ids
    return {
        "calculation_version": CALCULATION_VERSION,
        "source": source,
        "service_date": service_date,
        "route_id": route_id,
        "eligible_trips": len(eligible_trip_ids),
        "observed_trips": len(observed_trip_ids),
        "eligible_trip_count": len(eligible_trip_ids),
        "observed_trip_count": len(observed_trip_ids),
        "unobserved_scheduled_trip_count": len(eligible_trip_ids - observed_trip_ids),
        "unmatched_observations": len(unmatched),
        "coverage_percentage": _percent(len(observed_trip_ids), len(eligible_trip_ids)),
        "confidence": "HIGH" if eligible_trip_ids and len(observed_trip_ids) / len(eligible_trip_ids) >= 0.8 else "LOW",
        "missing_data_policy": "Absent Trip Updates are unknown, not on-time and not canceled.",
    }


def delay_distribution(stop_updates: pd.DataFrame, *, source: str, route_id: str | None = None) -> dict[str, Any]:
    frame = stop_updates.copy()
    if route_id is not None:
        frame = frame[frame["route_id"].astype(str) == route_id]
    delays = pd.to_numeric(frame.get("delay_seconds"), errors="coerce")
    usable = delays.dropna()
    return {
        "calculation_version": CALCULATION_VERSION,
        "source": source,
        "route_id": route_id,
        "observed_update_count": int(len(frame)),
        "usable_delay_count": int(len(usable)),
        "distinct_trip_count": int(frame.get("trip_id", pd.Series(dtype=str)).dropna().astype(str).nunique()),
        "median_delay_seconds": float(usable.median()) if not usable.empty else None,
        "average_delay_seconds": round(float(usable.mean()), 2) if not usable.empty else None,
        "p90_delay_seconds": float(usable.quantile(0.9)) if not usable.empty else None,
        "p95_delay_seconds": float(usable.quantile(0.95)) if not usable.empty else None,
        "maximum_delay_seconds": float(usable.max()) if not usable.empty else None,
        "early_observation_percentage": _percent(float((usable < 0).sum()), len(usable)),
        "severe_delay_percentage": _percent(float((usable > 900).sum()), len(usable)),
        "missing_delay_percentage": _percent(float(delays.isna().sum()), len(frame)),
    }


def on_time_performance(
    stop_updates: pd.DataFrame,
    *,
    source: str,
    thresholds: OnTimeThresholds | None = None,
    route_id: str | None = None,
) -> dict[str, Any]:
    frame = stop_updates.copy()
    thresholds = thresholds or DEFAULT_ON_TIME_THRESHOLDS
    if route_id is not None:
        frame = frame[frame["route_id"].astype(str) == route_id]
    delays = pd.to_numeric(frame.get("delay_seconds"), errors="coerce").dropna()
    on_time = delays[(delays >= thresholds.early_seconds) & (delays <= thresholds.late_seconds)]
    return {
        "calculation_version": CALCULATION_VERSION,
        "source": source,
        "route_id": route_id,
        "eligible_observations": int(len(delays)),
        "on_time_observations": int(len(on_time)),
        "on_time_percentage": _percent(len(on_time), len(delays)),
        "early_threshold_seconds": thresholds.early_seconds,
        "late_threshold_seconds": thresholds.late_seconds,
        "missing_data_policy": "Only observations with usable delay are eligible.",
    }


def explicit_cancellations(trip_updates: pd.DataFrame, *, source: str) -> pd.DataFrame:
    """Return only cancellations with explicit GTFS-Realtime schedule_relationship evidence."""
    if trip_updates.empty or "schedule_relationship" not in trip_updates.columns:
        return pd.DataFrame(columns=["source", "trip_id", "route_id", "evidence_type"])
    mask = trip_updates["schedule_relationship"].astype(str).str.upper().isin({"CANCELED", "CANCELLED"})
    result = trip_updates.loc[
        mask, [column for column in ("trip_id", "route_id", "snapshot_timestamp", "collection_time") if column in trip_updates.columns]
    ].copy()
    result.insert(0, "source", source)
    result["evidence_type"] = "GTFS_RT_TRIP_SCHEDULE_RELATIONSHIP_CANCELED"
    result["evidence_category"] = "GTFS_RT_EXPLICIT_SCHEDULE_RELATIONSHIP"
    return result


def headway_reliability(
    observed_times_seconds: list[int],
    scheduled_headways_seconds: list[int],
    *,
    source: str,
    route_id: str,
    method: str = "trip_updates",
    bunching_ratio: float = 0.5,
    gap_ratio: float = 1.5,
) -> dict[str, Any]:
    observed = sorted(observed_times_seconds)
    observed_headways = [b - a for a, b in zip(observed, observed[1:], strict=False) if b > a]
    scheduled = [value for value in scheduled_headways_seconds if value > 0]
    if len(observed_headways) < 2 or not scheduled:
        return {
            "calculation_version": CALCULATION_VERSION,
            "source": source,
            "route_id": route_id,
            "method": method,
            "eligible": False,
            "exclusion_reason": "insufficient_observed_headways",
            "sample_size": len(observed_headways),
        }
    planned = median(scheduled)
    gaps = [value for value in observed_headways if value > planned * gap_ratio]
    bunches = [value for value in observed_headways if value < planned * bunching_ratio]
    actual_wait = sum(value * value for value in observed_headways) / (2 * sum(observed_headways))
    scheduled_wait = sum(value * value for value in scheduled) / (2 * sum(scheduled))
    return {
        "calculation_version": CALCULATION_VERSION,
        "source": source,
        "route_id": route_id,
        "method": method,
        "eligible": True,
        "sample_size": len(observed_headways),
        "observed_headway_count": len(observed_headways),
        "scheduled_headway_seconds": float(planned),
        "average_observed_headway_seconds": round(sum(observed_headways) / len(observed_headways), 2),
        "service_gap_count": len(gaps),
        "bunching_count": len(bunches),
        "service_gap_event_count": len(gaps),
        "bunching_event_count": len(bunches),
        "bunching_ratio": bunching_ratio,
        "gap_ratio": gap_ratio,
        "excess_waiting_time_seconds": round(actual_wait - scheduled_wait, 2),
        "confidence": "HIGH" if len(observed_headways) >= 5 else "MEDIUM",
        "confidence_status": "HIGH" if len(observed_headways) >= 5 else "LOW_SAMPLE",
    }
