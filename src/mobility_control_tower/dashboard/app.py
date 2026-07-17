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

    data = fetch_dashboard_data(api_url)

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

