"""Streamlit local demo dashboard."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from mobility_control_tower.dashboard.api_client import fetch_dashboard_data


DEFAULT_API_URL = "http://127.0.0.1:8000"


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", [])
    return data if isinstance(data, list) else []


def _table(title: str, payload: dict[str, Any]) -> pd.DataFrame:
    st.subheader(title)
    if not payload.get("ok", True):
        st.warning(payload.get("error", "Data unavailable."))
        return pd.DataFrame()
    frame = pd.DataFrame(_rows(payload))
    if frame.empty:
        st.info("No rows available.")
    else:
        st.dataframe(frame, use_container_width=True)
    return frame


def main() -> None:
    st.set_page_config(page_title="Mobility Control Tower", layout="wide")
    st.title("Mobility Control Tower - Local Demo")
    st.caption("Local academic MVP: static planning KPIs, GTFS-Realtime snapshot indicators, DuckDB serving, and read-only API.")

    api_url = st.sidebar.text_input("API URL", value=os.environ.get("MCT_API_URL", DEFAULT_API_URL))
    st.sidebar.markdown("Start the API before using the dashboard.")
    page = st.sidebar.radio("Page", ["Operational MVP", "Historical Analytics", "Data Quality"])

    data = fetch_dashboard_data(api_url)

    if page == "Historical Analytics":
        st.header("Historical Analytics")
        summary = _table("Collection summary", data["history_summary"])
        trend = _table("Delay evolution by hour", data["history_delay_trend"])
        feed = _table("Feed freshness history", data["history_feed_health"])
        routes = _table("Top delayed routes", data["history_routes"])

        if not trend.empty and {"collection_date", "collection_hour", "average_delay_seconds"}.issubset(trend.columns):
            trend = trend.copy()
            trend["period"] = trend["collection_date"].astype(str) + " " + trend["collection_hour"].astype(str) + ":00"
            st.line_chart(trend.set_index("period")["average_delay_seconds"])
        if not feed.empty and {"collection_time", "feed_age_seconds"}.issubset(feed.columns):
            st.line_chart(feed.set_index("collection_time")["feed_age_seconds"])
        if not summary.empty and {"collection_date", "updates_collected"}.issubset(summary.columns):
            st.bar_chart(summary.set_index("collection_date")["updates_collected"])
        if not routes.empty and {"route_id", "average_delay_seconds"}.issubset(routes.columns):
            label = "route_short_name" if "route_short_name" in routes.columns else "route_id"
            st.bar_chart(routes.set_index(label)["average_delay_seconds"])

        stops = _table("Top delayed stops", data["history_stops"])
        if not stops.empty and {"stop_id", "average_delay_seconds"}.issubset(stops.columns):
            st.bar_chart(stops.set_index("stop_id")["average_delay_seconds"])
        return

    if page == "Data Quality":
        st.header("Data Quality")
        payload = data["quality_summary"]
        if not payload.get("ok", True):
            st.warning(payload.get("error", "Validation summary unavailable."))
            return
        rows = _rows(payload)
        if not rows:
            st.info("No validation summary available.")
            return
        summary = rows[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Validation success rate", f"{summary.get('success_rate', 0)}%")
        col2.metric("Failed expectations", summary.get("expectations_failed", 0))
        col3.metric("Expectations evaluated", summary.get("expectations_evaluated", 0))
        st.subheader("Freshness")
        st.json(summary.get("freshness", {}))
        failed = pd.DataFrame(summary.get("failed_expectations", []))
        if failed.empty:
            st.success("No failed expectations in the latest validation summary.")
        else:
            st.dataframe(failed, use_container_width=True)
        st.subheader("Latest dbt run")
        st.write(summary.get("latest_dbt_run", "See dbt target/run_results.json and dbt target/manifest.json."))
        st.subheader("Model count")
        st.write(summary.get("model_count", "Available after `test-dbt` or `generate-dbt-docs`."))
        return

    st.header("1. Project overview")
    st.write(
        "This dashboard consumes the local FastAPI API and shows queryable data products from the Mobility Control Tower. "
        "It is a local academic MVP, not a production monitoring system."
    )

    st.header("2. API health")
    health = data["health"]
    if health.get("ok", True):
        st.json(health)
    else:
        st.error(health["error"])

    st.header("3. Static network overview")
    network = _table("Network daily summary", data["network_overview"])
    if not network.empty and "scheduled_trips_count" in network.columns:
        st.line_chart(network.set_index("service_date")["scheduled_trips_count"])

    st.header("4. Top routes by scheduled trips")
    top_routes = _table("Top routes over the static GTFS service period", data["top_routes"])
    if not top_routes.empty and {"route_short_name", "total_scheduled_trips"}.issubset(top_routes.columns):
        st.bar_chart(top_routes.set_index("route_short_name")["total_scheduled_trips"])

    st.header("5. Route type summary")
    _table("Route type daily summary sample", data["route_types"])

    st.header("6. Planned hourly headway sample")
    _table("Planned headway approximation by route/hour", data["hourly_headway"])

    st.header("7. Realtime snapshot feed health")
    st.write("These GTFS-Realtime snapshot values were observed at fetch time.")
    _table("Feed health", data["rt_feed_health"])

    st.header("8. Realtime identifier compatibility")
    compatibility = _table("Static/live identifier compatibility", data["rt_compatibility"])
    if not compatibility.empty and {"identifier_type", "match_percentage"}.issubset(compatibility.columns):
        st.bar_chart(compatibility.set_index("identifier_type")["match_percentage"])

    st.header("9. Top delayed routes snapshot")
    delayed_routes = _table("Routes with highest average observed delay in one snapshot", data["rt_top_delayed_routes"])
    if not delayed_routes.empty and {"route_short_name", "avg_delay_seconds"}.issubset(delayed_routes.columns):
        st.bar_chart(delayed_routes.set_index("route_short_name")["avg_delay_seconds"])

    st.header("10. Limitations and next steps")
    st.write(
        "- These are static planning KPIs and GTFS-Realtime snapshot indicators.\n"
        "- The dashboard is read-only and local.\n"
        "- It is not a production monitoring system and does not implement streaming.\n"
        "- A future phase could add a richer dashboard or repeated snapshot collection."
    )


if __name__ == "__main__":
    main()
