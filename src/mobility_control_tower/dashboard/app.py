"""Streamlit local demo dashboard."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from mobility_control_tower.dashboard.api_client import fetch_dashboard_data, get_json, post_json

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


def _payload(data: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    return data.get(key, {"ok": True, "data": [], "count": 0})


def main() -> None:
    st.set_page_config(page_title="Mobility Control Tower", layout="wide")
    st.title("Mobility Control Tower")
    st.caption("Near-realtime public transport monitoring from validated schedule and GTFS-Realtime evidence.")

    api_url = st.sidebar.text_input("API URL", value=os.environ.get("MCT_API_URL", DEFAULT_API_URL))
    page = st.sidebar.radio(
        "Page",
        [
            "Control Tower",
            "Incident Queue",
            "Route Reliability",
            "Live Fleet",
            "Service Alerts",
            "Historical Reliability",
            "Data Trust",
            "City Comparison",
        ],
    )
    page = {"Operational MVP": "Control Tower", "Historical Analytics": "Historical Reliability", "Data Quality": "Data Trust"}.get(page, page)

    data = fetch_dashboard_data(api_url)

    if page == "Control Tower":
        health = _payload(data, "health")
        if not health.get("ok", True):
            st.error(health.get("error", "API unavailable."))
        ready = health.get("status") in {"ok", "ready"}
        incidents = pd.DataFrame(_rows(_payload(data, "incidents")))
        alerts = pd.DataFrame(_rows(_payload(data, "alerts_active")))
        network = pd.DataFrame(_rows(_payload(data, "network_status")))
        vehicles = pd.DataFrame(_rows(_payload(data, "vehicles")))
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Serving ready", "yes" if ready else "no")
        col2.metric("Open incidents", len(incidents[incidents["status"] != "RESOLVED"]) if not incidents.empty and "status" in incidents else len(incidents))
        col3.metric("Active alerts", len(alerts))
        col4.metric("Vehicles visible", len(vehicles))
        if not network.empty:
            st.subheader("Current Network Evidence")
            st.dataframe(network, use_container_width=True)
        evaluations = pd.DataFrame(_rows(_payload(data, "incident_evaluations")))
        if not evaluations.empty:
            st.subheader("Latest Incident Evaluation")
            st.dataframe(evaluations.head(1), use_container_width=True)
        elif not _payload(data, "incident_evaluations").get("ok", True):
            st.warning("Incident evaluator status requires operations read access.")
        _table("Critical Incidents", _payload(data, "incidents"))
        _table("Active Service Alerts", _payload(data, "alerts_active"))
        return

    if page == "Incident Queue":
        incidents = _table("Incident Queue", data["incidents"])
        token = st.text_input("Operator bearer token", type="password")
        incident_id = st.text_input("Incident ID")
        note = st.text_input("Operator note")
        suppress_until = st.text_input("Suppress until UTC")
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("Acknowledge", disabled=not incident_id):
            st.json(post_json(api_url, f"/v1/incidents/{incident_id}/acknowledge", token, {"reason": note}))
        if col2.button("Resolve", disabled=not incident_id):
            st.json(post_json(api_url, f"/v1/incidents/{incident_id}/resolve", token, {"reason": note}))
        if col3.button("Suppress", disabled=not incident_id):
            st.json(post_json(api_url, f"/v1/incidents/{incident_id}/suppress", token, {"reason": note, "expires_at": suppress_until}))
        if col4.button("Unsuppress", disabled=not incident_id):
            st.json(post_json(api_url, f"/v1/incidents/{incident_id}/unsuppress", token, {"reason": note}))
        if incident_id and token:
            events = get_json(api_url, f"/v1/incidents/{incident_id}/events", timeout=5, token=token)
            if events.get("ok", True):
                _table("Event Timeline", events)
            else:
                st.warning(events.get("error", "Event history unavailable."))
        if not incidents.empty and "evidence" in incidents.columns:
            st.subheader("Selected Evidence")
            st.json(incidents.iloc[0]["evidence"])
        return

    if page == "Route Reliability":
        routes = pd.DataFrame(_rows(data["routes_api"]))
        route_ids = sorted(routes["route_id"].dropna().astype(str).unique()) if not routes.empty and "route_id" in routes else []
        route_id = st.selectbox("Route", route_ids or ["R1"])
        reliability = get_json(api_url, f"/routes/{route_id}/reliability", {"limit": 100})
        headways = get_json(api_url, f"/routes/{route_id}/headways", {"limit": 100})
        _table("Reliability With Coverage", reliability)
        _table("Headway Evidence", headways)
        st.caption("Delay and OTP metrics are shown only with observed realtime coverage. Missing Trip Updates remain unknown.")
        return

    if page == "Live Fleet":
        vehicles = _table("Latest Vehicle Positions", data["vehicles"])
        if not vehicles.empty and {"latitude", "longitude"}.issubset(vehicles.columns):
            map_frame = vehicles.dropna(subset=["latitude", "longitude"]).head(500)
            if not map_frame.empty:
                st.map(map_frame.rename(columns={"latitude": "lat", "longitude": "lon"}), latitude="lat", longitude="lon")
        st.caption("Stale and invalid positions remain visible with flags; unavailable Vehicle Position feeds are not treated as zero vehicles.")
        return

    if page == "Service Alerts":
        _table("Active Alerts", data["alerts_active"])
        st.caption("Alerts are normalized from GTFS-Realtime Service Alerts when the source provides them.")
        return

    if page == "Historical Reliability":
        st.header("Historical Reliability")
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

    if page == "Data Trust":
        st.header("Data Trust")
        payload = data["quality_summary"]
        if not payload.get("ok", True):
            st.warning(payload.get("error", "Validation summary unavailable."))
        else:
            rows = _rows(payload)
            summary = rows[0] if rows else {}
            col1, col2, col3 = st.columns(3)
            col1.metric("Validation success rate", f"{summary.get('success_rate', 0)}%")
            col2.metric("Failed expectations", summary.get("expectations_failed", 0))
            col3.metric("Expectations evaluated", summary.get("expectations_evaluated", 0))
            failed = pd.DataFrame(summary.get("failed_expectations", []))
            st.dataframe(failed, use_container_width=True) if not failed.empty else st.success("No failed expectations in the latest validation summary.")
        _table("Source Capabilities", _payload(data, "sources"))
        _table("Lineage Status", _payload(data, "lineage_status"))
        _table("Serving Metadata", _payload(data, "metadata"))
        return

    sources = pd.DataFrame(_rows(_payload(data, "sources")))
    reliability = pd.DataFrame(_rows(_payload(data, "network_reliability")))
    if sources.empty:
        st.info("No source capability metadata available.")
        return
    _table("City Capability Comparison", _payload(data, "sources"))
    if not reliability.empty:
        st.subheader("Normalized Reliability Measures")
        st.dataframe(reliability, use_container_width=True)
    st.caption("City comparisons use capability and percentage/rate measures. Unsupported feeds are unavailable, not zero.")


if __name__ == "__main__":
    main()
