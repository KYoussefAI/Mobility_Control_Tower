"""Read-only Streamlit dashboard over dbt-owned DuckDB marts."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "mart" / "mobility_control_tower.duckdb"
DB_PATH = Path(os.environ.get("MCT_DBT_DATABASE_PATH", DEFAULT_DB))


@st.cache_data(ttl=60)
def query(sql: str, parameters: list[object] | None = None) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        return connection.execute(sql, parameters or []).fetchdf()


def network_overview() -> None:
    st.header("Network Overview")
    latest = query(
        """
        select * from network_on_time_performance
        order by service_date desc limit 1
        """
    )
    scheduled = query(
        """
        select service_date, sum(scheduled_trips) as scheduled_trips,
               sum(scheduled_departures) as scheduled_departures
        from route_daily_service group by 1 order by 1 desc limit 1
        """
    )
    columns = st.columns(4)
    columns[0].metric(
        "Latest service date", str(latest.iloc[0]["service_date"]) if not latest.empty else "No observations"
    )
    columns[1].metric("Scheduled trips", f"{scheduled.iloc[0]['scheduled_trips']:,.0f}" if not scheduled.empty else "—")
    columns[2].metric(
        "Known delay observations", f"{latest.iloc[0]['observed_stop_updates']:,.0f}" if not latest.empty else "—"
    )
    columns[3].metric("On-time", f"{latest.iloc[0]['on_time_percentage']:.1f}%" if not latest.empty else "—")

    hourly = query(
        """
        select service_date, service_hour, average_delay_seconds, on_time_percentage,
               observed_stop_updates, sample_size_status
        from hourly_delay_summary order by service_date, service_hour
        """
    )
    st.subheader("Delay by scheduled service hour")
    if hourly.empty:
        st.info("Collect Trip Updates and rebuild dbt to populate observed reliability charts.")
    else:
        date = st.selectbox("Service date", sorted(hourly["service_date"].unique(), reverse=True))
        selected = hourly[hourly["service_date"] == date].set_index("service_hour")
        low_sample_count = int((selected["sample_size_status"] == "LOW_SAMPLE").sum())
        if low_sample_count:
            st.warning(
                f"{low_sample_count} hourly row(s) are flagged LOW_SAMPLE because they are below the configured "
                "reliability threshold."
            )
        st.line_chart(selected[["average_delay_seconds", "on_time_percentage"]])
        st.caption(
            "The two series use different units: seconds and percent. Hover for exact values and sample sizes below."
        )
        st.dataframe(selected.reset_index(), use_container_width=True, hide_index=True)


def route_reliability() -> None:
    st.header("Route Reliability")
    routes = query(
        """
        select distinct route_id, coalesce(route_short_name, route_id) as route_label
        from route_delay_summary order by route_label
        """
    )
    if routes.empty:
        st.info("No matched delay observations are available yet.")
        return
    labels = dict(zip(routes["route_label"], routes["route_id"], strict=True))
    label = st.selectbox("Route", list(labels))
    summary = query(
        """
        select service_date, route_short_name, route_long_name, observed_trips,
               observed_stop_updates, average_delay_seconds, median_delay_seconds,
               p90_delay_seconds, on_time_percentage, sample_size_status
        from route_delay_summary where route_id = ? order by service_date
        """,
        [labels[label]],
    )
    latest = summary.iloc[-1]
    low_sample_count = int((summary["sample_size_status"] == "LOW_SAMPLE").sum())
    if low_sample_count:
        st.warning(
            f"{low_sample_count} route-day row(s) are flagged LOW_SAMPLE because they are below the configured "
            "reliability threshold."
        )
    columns = st.columns(5)
    columns[0].metric("Observed trips", f"{latest['observed_trips']:,.0f}")
    columns[1].metric("On-time", f"{latest['on_time_percentage']:.1f}%")
    columns[2].metric("Median delay", f"{latest['median_delay_seconds']:.0f} s")
    columns[3].metric("P90 delay", f"{latest['p90_delay_seconds']:.0f} s")
    columns[4].metric("Sample confidence", latest["sample_size_status"])
    st.line_chart(
        summary.set_index("service_date")[["average_delay_seconds", "median_delay_seconds", "p90_delay_seconds"]]
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption("Statistics cover matched stop-time updates with a known delay; they are not passenger-weighted.")


def feed_health() -> None:
    st.header("Data Quality / Feed Health")
    freshness = query(
        """
        select collected_at, feed_age_seconds, freshness_status, entity_count,
               trip_update_count, stop_time_update_count
        from feed_freshness order by collected_at
        """
    )
    coverage = query("select * from realtime_coverage order by service_date")
    if freshness.empty:
        st.warning("No realtime snapshots have been collected.")
    else:
        latest = freshness.iloc[-1]
        columns = st.columns(3)
        columns[0].metric("Latest feed status", latest["freshness_status"])
        columns[1].metric(
            "Feed age", f"{latest['feed_age_seconds']} s" if pd.notna(latest["feed_age_seconds"]) else "Unknown"
        )
        columns[2].metric("Trip updates", f"{latest['trip_update_count']:,.0f}")
        st.line_chart(freshness.set_index("collected_at")[["feed_age_seconds"]])
        st.dataframe(
            freshness.tail(20).sort_values("collected_at", ascending=False), use_container_width=True, hide_index=True
        )

    st.subheader("Realtime/static match coverage")
    if coverage.empty:
        st.info("Coverage is calculated only for service dates on which at least one feed snapshot was collected.")
    else:
        st.bar_chart(coverage.set_index("service_date")[["coverage_percentage"]])
        st.dataframe(coverage, use_container_width=True, hide_index=True)
    st.warning(
        "Trips without a matching realtime observation remain UNKNOWN. They are not counted as cancelled or on-time."
    )


def main() -> None:
    st.set_page_config(page_title="Mobility Control Tower", page_icon="🚇", layout="wide")
    st.title("Mobility Control Tower — Toulouse")
    st.caption("Tisséo GTFS Schedule compared with scheduled GTFS-Realtime Trip Updates polling")
    if not DB_PATH.is_file():
        st.error(f"DuckDB file not found at {DB_PATH}. Run a pipeline before opening the dashboard.")
        st.stop()
    page = st.sidebar.radio("Page", ("Network Overview", "Route Reliability", "Data Quality / Feed Health"))
    if page == "Network Overview":
        network_overview()
    elif page == "Route Reliability":
        route_reliability()
    else:
        feed_health()


if __name__ == "__main__":
    main()
