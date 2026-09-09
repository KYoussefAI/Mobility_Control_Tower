"""Streamlit dashboard for currently available analytical features."""

import os
from typing import Any

import pandas as pd
import streamlit as st

from mobility_control_tower.dashboard.api_client import fetch_dashboard_data


def show(title: str, payload: dict[str, Any]) -> None:
    st.subheader(title)
    if not payload.get("ok", True):
        st.warning(payload.get("error", "Data unavailable"))
        return
    rows = payload.get("data", [])
    st.dataframe(pd.DataFrame(rows), use_container_width=True) if rows else st.info("No rows available.")


def main() -> None:
    st.set_page_config(page_title="Mobility Control Tower", layout="wide")
    st.title("Mobility Control Tower")
    api_url = st.sidebar.text_input("API URL", value=os.environ.get("MCT_API_URL", "http://127.0.0.1:8000"))
    token = None
    page = st.sidebar.radio("Page", ["Static Network"])
    data = fetch_dashboard_data(api_url, token)
    if page == "Static Network":
        show("Network overview", data["network_overview"])
        show("Top routes", data["top_routes"])
        show("Planned hourly headway", data["hourly_headway"])
        show("Route types", data["route_types"])


if __name__ == "__main__":
    main()
