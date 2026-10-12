"""Professional read-only Streamlit dashboard over dbt-owned DuckDB marts."""

from __future__ import annotations

import html
import os
from datetime import date
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "mart" / "mobility_control_tower.duckdb"
DB_PATH = Path(os.environ.get("MCT_DBT_DATABASE_PATH", DEFAULT_DB))
REQUIRED_MARTS = {
    "data_coverage_summary",
    "feed_freshness",
    "hourly_delay_summary",
    "network_on_time_performance",
    "realtime_coverage",
    "route_daily_service",
    "route_delay_summary",
}
ACCENT, INK, MUTED = "#2563EB", "#172033", "#64748B"
SUCCESS, WARNING, DANGER, UNKNOWN = "#15803D", "#D97706", "#DC2626", "#CBD5E1"


@st.cache_data(ttl=60)
def query(sql: str, parameters: list[object] | None = None) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        return connection.execute(sql, parameters or []).fetchdf()


def missing_required_marts(database: Path = DB_PATH) -> list[str]:
    with duckdb.connect(str(database), read_only=True) as connection:
        present = {
            row[0]
            for row in connection.execute(
                "select table_name from information_schema.tables where table_schema = 'main'"
            ).fetchall()
        }
    return sorted(REQUIRED_MARTS - present)


def format_service_date(value: object) -> str:
    return pd.Timestamp(value).strftime("%d %b %Y").lstrip("0")


def format_delay(value: object) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    seconds = int(round(float(value)))
    direction = "early" if seconds < 0 else "late" if seconds > 0 else ""
    minutes, remainder = divmod(abs(seconds), 60)
    duration = f"{minutes} min {remainder} sec" if minutes else f"{remainder} sec"
    return f"{duration} {direction}".strip()


def format_feed_age(value: object) -> str:
    if value is None or pd.isna(value):
        return "Unknown"
    minutes, seconds = divmod(max(0, int(value)), 60)
    return f"{minutes} min {seconds} sec" if minutes else f"{seconds} sec"


def load_network_snapshot(service_date: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load every headline network value for exactly the selected service date."""
    performance = query("select * from network_on_time_performance where service_date = ?", [service_date])
    coverage = query("select * from realtime_coverage where service_date = ?", [service_date])
    schedule = query(
        """
        select sum(scheduled_trips) as scheduled_trips,
               sum(scheduled_departures) as scheduled_departures
        from route_daily_service where service_date = ?
        """,
        [service_date],
    )
    return performance, coverage, schedule


def _style() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --blue:#2563eb; }
        .stApp { background: #f7f9fc; color: var(--ink); }
        [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
        [data-testid="stSidebar"] * { color: #374151; }
        [data-testid="stSidebar"] .stCaptionContainer p { color: #6b7280 !important; opacity: 1; }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .25rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border-left: 3px solid transparent; border-radius: 7px; padding: .45rem .55rem;
            transition: background-color .15s ease, border-color .15s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #f8fafc; }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: #eff6ff; border-left-color: #2563eb;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
            color: #1d4ed8 !important; font-weight: 700;
        }
        [data-baseweb="select"] > div {
            background: #ffffff !important; border-color: #d1d5db !important; color: #111827 !important;
        }
        [data-baseweb="select"] span, [data-baseweb="select"] input { color: #111827 !important; }
        [data-baseweb="select"] > div:focus-within {
            border-color: #2563eb !important; box-shadow: 0 0 0 1px #2563eb !important;
        }
        [data-baseweb="popover"] { color-scheme: light; }
        .block-container { max-width: 1350px; padding: 1.35rem 2rem 4rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -.025em; }
        [data-testid="stMarkdownContainer"] h2 { font-size:1.55rem !important; line-height:1.22 !important;
            margin:1.45rem 0 .25rem !important; overflow-wrap:anywhere; }
        h3 { font-size: 1rem; }
        p { line-height: 1.55; }
        .mct-header { display:flex; justify-content:space-between; gap:2rem; align-items:flex-start;
            padding-bottom:1rem; border-bottom:1px solid var(--line); margin-bottom:.9rem; }
        .mct-eyebrow { color:var(--blue); font-size:.72rem; font-weight:750; letter-spacing:.12em;
            text-transform:uppercase; margin-bottom:.35rem; }
        .mct-title { color:var(--ink); font-size:1.9rem; font-weight:720; letter-spacing:-.04em; line-height:1.1; }
        .mct-subtitle { color:#4b5563; font-size:.94rem; margin-top:.35rem; }
        .mct-source { color:#6b7280; font-size:.76rem; margin-top:.18rem; }
        .mct-date { position:relative; top:.75rem; white-space:nowrap; background:#eff6ff; color:#1d4ed8;
            border:1px solid #bfdbfe; border-radius:999px; padding:.42rem .72rem; font-size:.8rem;
            font-weight:650; }
        .mct-section-copy { color:var(--muted); margin:.1rem 0 .85rem; font-size:.9rem; }
        .kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem; margin:.75rem 0 .7rem; }
        .kpi-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.15rem 1.2rem;
            min-height:126px; box-shadow:0 1px 3px rgba(15,23,42,.05); }
        .kpi-label { color:#6b7280; font-size:.75rem; font-weight:700; letter-spacing:.035em;
            text-transform:uppercase; }
        .kpi-value { color:var(--ink); font-size:1.75rem; font-weight:700; letter-spacing:-.04em;
            line-height:1.12; margin:.42rem 0 .38rem; overflow-wrap:anywhere; }
        .kpi-help { color:#6b7280; font-size:.76rem; line-height:1.35; }
        .meta-row { display:flex; flex-wrap:wrap; gap:.35rem 1.2rem; color:#64748b; font-size:.8rem;
            padding:.25rem .1rem .75rem; }
        .meta-row strong { color:#334155; font-weight:650; }
        .insight { background:#fff; border:1px solid var(--line); border-left:3px solid var(--blue);
            border-radius:9px; padding:.72rem .9rem; color:#475569; font-size:.88rem; margin:.2rem 0 1rem; }
        .sample-chip { display:inline-block; background:#f1f5f9; color:#475569; border:1px solid #dbe3ec;
            border-radius:999px; padding:.28rem .62rem; font-size:.76rem; font-weight:650; margin:.05rem 0 .65rem; }
        .mct-note { color:#64748b; font-size:.82rem; }
        div[data-testid="stDataFrame"] { background:#fff; border:1px solid var(--line); border-radius:10px;
            overflow:hidden; color-scheme:light; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background:#fff; border-color:var(--line) !important; border-radius:12px !important;
            box-shadow:0 1px 3px rgba(15,23,42,.04); padding:.35rem .45rem .2rem;
        }
        .route-table { background:#fff; border:1px solid var(--line); border-radius:11px; overflow:hidden;
            box-shadow:0 1px 3px rgba(15,23,42,.035); }
        .route-table table { width:100%; border-collapse:collapse; table-layout:fixed; }
        .route-table th { background:#f8fafc; color:#4b5563; font-size:.72rem; font-weight:700;
            letter-spacing:.035em; text-transform:uppercase; padding:.7rem .8rem; text-align:left;
            border-bottom:1px solid var(--line); }
        .route-table td { color:#374151; font-size:.81rem; padding:.65rem .8rem; border-bottom:1px solid #eef2f7;
            vertical-align:middle; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .route-table tbody tr:last-child td { border-bottom:0; }
        .route-table tbody tr:hover { background:#f8fbff; }
        .route-table .route-code { color:#111827; font-weight:700; width:8%; }
        .route-table .route-name { width:34%; }
        .route-table .metric { width:13%; }
        .route-table .otp-cell { width:19%; }
        .otp-value { display:flex; align-items:center; gap:.55rem; }
        .otp-track { flex:1; height:6px; background:#e5e7eb; border-radius:99px; overflow:hidden; min-width:52px; }
        .otp-fill { height:100%; background:#2563eb; border-radius:99px; }
        .otp-number { color:#1d4ed8; font-weight:700; min-width:3.4rem; }
        [data-testid="stExpander"] { background:#fff; border-color:var(--line); border-radius:10px; }
        [data-testid="stAlert"] { border-radius:10px; }
        footer { visibility:hidden; }
        @media (max-width: 900px) {
            .block-container { padding:1.2rem 1rem 3rem; }
            .kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            .mct-header { flex-direction:column; gap:.6rem; }
            .mct-title { font-size:1.7rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _header(period_label: str) -> None:
    st.markdown(
        f"""
        <div class="mct-header">
          <div>
            <div class="mct-eyebrow">Operations analytics</div>
            <div class="mct-title">Toulouse Mobility Control Tower</div>
            <div class="mct-subtitle">Network reliability from static GTFS and GTFS-Realtime</div>
            <div class="mct-source">Source: Tisséo open mobility feeds · latest published update per trip-stop</div>
          </div>
          <div class="mct-date">{html.escape(period_label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_grid(cards: list[tuple[str, str, str]]) -> None:
    content = "".join(
        "<div class='kpi-card'>"
        f"<div class='kpi-label'>{html.escape(label)}</div>"
        f"<div class='kpi-value'>{html.escape(value)}</div>"
        f"<div class='kpi-help'>{html.escape(help_text)}</div>"
        "</div>"
        for label, value, help_text in cards
    )
    st.markdown(f"<div class='kpi-grid'>{content}</div>", unsafe_allow_html=True)


def _metadata(items: list[tuple[str, str]]) -> None:
    content = "".join(
        f"<span><strong>{html.escape(label)}:</strong> {html.escape(value)}</span>" for label, value in items
    )
    st.markdown(f"<div class='meta-row'>{content}</div>", unsafe_allow_html=True)


def _chart_style(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    return (
        chart.properties(background="#FFFFFF", padding={"left": 10, "right": 12, "top": 12, "bottom": 8})
        .configure(background="#FFFFFF", font="system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif")
        .configure_view(stroke="transparent", fill="#FFFFFF")
        .configure_axis(
            labelColor="#4B5563",
            titleColor="#374151",
            gridColor="#E5E7EB",
            gridOpacity=0.7,
            domainColor="#D1D5DB",
            tickColor="#D1D5DB",
            labelFontSize=11,
            titleFontSize=11,
            labelFont="system-ui",
            titleFont="system-ui",
        )
        .configure_legend(
            labelColor="#4B5563", titleColor="#374151", orient="top", labelFont="system-ui", titleFont="system-ui"
        )
        .configure_title(color="#111827", font="system-ui", fontSize=13, fontWeight=600, anchor="start")
    )


def _render_chart(chart: alt.TopLevelMixin) -> None:
    with st.container(border=True):
        st.altair_chart(_chart_style(chart), width="stretch", theme=None)


def _route_table(rows: pd.DataFrame) -> None:
    body = []
    for row in rows.itertuples():
        on_time = float(row.on_time_percentage)
        body.append(
            "<tr>"
            f"<td class='route-code'>{html.escape(str(row.route))}</td>"
            f"<td class='route-name' title='{html.escape(str(row.route_name))}'>{html.escape(str(row.route_name))}</td>"
            "<td class='otp-cell'><div class='otp-value'>"
            f"<span class='otp-number'>{on_time:.1f}%</span>"
            f"<span class='otp-track'><span class='otp-fill' style='display:block;width:{max(0, min(100, on_time)):.1f}%'></span></span>"
            "</div></td>"
            f"<td class='metric'>{format_delay(row.median_delay_seconds)}</td>"
            f"<td class='metric'>{format_delay(row.p90_delay_seconds)}</td>"
            f"<td class='metric'>{int(row.observed_trips):,}</td>"
            "</tr>"
        )
    st.markdown(
        "<div class='route-table'><table><thead><tr>"
        "<th class='route-code'>Route</th><th class='route-name'>Name</th><th class='otp-cell'>On-time</th>"
        "<th class='metric'>Median</th><th class='metric'>P90</th><th class='metric'>Trips</th>"
        f"</tr></thead><tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _selected_rule(selected: date) -> alt.Chart:
    return (
        alt.Chart(pd.DataFrame({"service_date": [pd.Timestamp(selected)]}))
        .mark_rule(color="#94A3B8", opacity=0.65, strokeDash=[4, 4])
        .encode(x="service_date:T")
    )


def _methodology() -> None:
    with st.expander("How these metrics work"):
        st.markdown(
            """
**On time** uses the latest matched published delay for each canonical trip-stop and counts values from
1 minute early through 5 minutes late. **Median delay** is the middle value; **P90 delay** means 90% of
matched values are at or below it. **Coverage** is the share of scheduled trips with at least one valid
realtime match. Unmatched trips remain **unknown** and are never inferred to be cancelled, late, or on time.

A sample is marked **low sample** below 30 canonical trip-stop records. GTFS-Realtime values are published
updates or predictions, not verified physical arrivals, and the metrics are not passenger-weighted.
            """
        )


def network_overview(selected_date: date) -> None:
    performance, coverage, schedule = load_network_snapshot(selected_date)
    if performance.empty or coverage.empty:
        st.info("No schedule-matched performance is available for this date.")
        return
    current, current_coverage = performance.iloc[0], coverage.iloc[0]
    scheduled = int(schedule.iloc[0]["scheduled_trips"]) if not schedule.empty else 0
    st.markdown("## Network snapshot")
    st.markdown(
        "<div class='mct-section-copy'>The latest schedule-aligned view of punctuality, delay, and representation.</div>",
        unsafe_allow_html=True,
    )
    _kpi_grid(
        [
            ("On-time performance", f"{current['on_time_percentage']:.1f}%", "Within 1 min early to 5 min late"),
            ("Typical delay", format_delay(current["median_delay_seconds"]), "Median canonical trip-stop delay"),
            ("P90 delay", format_delay(current["p90_delay_seconds"]), "90% of matched values are no worse"),
            (
                "Realtime coverage",
                f"{current_coverage['coverage_percentage']:.1f}%",
                f"{int(current_coverage['matched_realtime_trips']):,} of {int(current_coverage['scheduled_trips']):,} trips",
            ),
        ]
    )
    _metadata(
        [
            ("Observed trips", f"{int(current['observed_trips']):,}"),
            ("Canonical trip-stops", f"{int(current['observed_trip_stops']):,}"),
            ("Scheduled trips", f"{scheduled:,}"),
            ("Sample", str(current["sample_size_status"]).replace("_", " ").title()),
        ]
    )
    st.markdown(
        f"<div class='insight'><strong>{current['on_time_percentage']:.1f}%</strong> of matched canonical "
        f"trip-stop updates on {format_service_date(selected_date)} fell inside the configured on-time window.</div>",
        unsafe_allow_html=True,
    )

    trend = query("select * from network_on_time_performance order by service_date")
    st.markdown("## Network performance")
    left, right = st.columns([1.9, 1], gap="large")
    punctuality = (
        alt.Chart(trend)
        .mark_line(point=alt.OverlayMarkDef(size=58), color=ACCENT, strokeWidth=2.5)
        .encode(
            x=alt.X(
                "service_date:T",
                title=None,
                axis=alt.Axis(format="%d %b", tickCount="day", labelAngle=0, grid=False),
            ),
            y=alt.Y("on_time_percentage:Q", title="On-time (%)", scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("service_date:T", title="Service date", format="%d %b %Y"),
                alt.Tooltip("on_time_percentage:Q", title="On-time", format=".1f"),
                alt.Tooltip("observed_trips:Q", title="Observed trips", format=","),
                alt.Tooltip("observed_trip_stops:Q", title="Canonical trip-stops", format=","),
            ],
        )
        .properties(height=270, title="On-time performance by date")
    )
    with left:
        _render_chart(punctuality + _selected_rule(selected_date))

    delay_trend = trend.melt(
        id_vars=["service_date", "observed_trip_stops"],
        value_vars=["median_delay_seconds", "p90_delay_seconds"],
        var_name="measure",
        value_name="delay_seconds",
    )
    delay_trend["measure"] = delay_trend["measure"].map(
        {"median_delay_seconds": "Median", "p90_delay_seconds": "P90"}
    )
    delay_chart = (
        alt.Chart(delay_trend)
        .mark_line(point=True, strokeWidth=2.1)
        .encode(
            x=alt.X("service_date:T", title=None, axis=alt.Axis(format="%d %b", tickCount="day", labelAngle=0)),
            y=alt.Y("delay_seconds:Q", title="Delay (sec)"),
            color=alt.Color("measure:N", title=None, scale=alt.Scale(range=[SUCCESS, WARNING])),
            tooltip=[
                alt.Tooltip("service_date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("measure:N", title="Measure"),
                alt.Tooltip("delay_seconds:Q", title="Delay (sec)", format=".0f"),
                alt.Tooltip("observed_trip_stops:Q", title="Canonical trip-stops", format=","),
            ],
        )
        .properties(height=270, title="Delay profile")
    )
    with right:
        _render_chart(delay_chart + _selected_rule(selected_date))

    st.markdown("## Time of day")
    hourly = query("select * from hourly_delay_summary where service_date = ? order by service_hour", [selected_date])
    if hourly.empty:
        st.info("No hourly performance is available for this date.")
        return
    hourly["hour_label"] = hourly["service_hour"].map(lambda hour: f"{int(hour):02d}:00")
    hourly["sample_label"] = hourly["sample_size_status"].str.replace("_", " ").str.title()
    sufficient = hourly[hourly["sample_size_status"] == "SUFFICIENT_SAMPLE"].copy()
    excluded = len(hourly) - len(sufficient)
    if sufficient.empty:
        st.info("No hourly interval meets the minimum sample threshold for this date.")
    else:
        hour_chart = (
            alt.Chart(sufficient)
            .mark_bar(color=ACCENT, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("hour_label:O", title="Scheduled hour", sort=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("on_time_percentage:Q", title="On-time (%)", scale=alt.Scale(domain=[0, 100])),
                tooltip=[
                    alt.Tooltip("hour_label:O", title="Scheduled hour"),
                    alt.Tooltip("on_time_percentage:Q", title="On-time", format=".1f"),
                    alt.Tooltip("p90_delay_seconds:Q", title="P90 delay (sec)", format=".0f"),
                    alt.Tooltip("observed_trips:Q", title="Observed trips", format=","),
                    alt.Tooltip("observed_trip_stops:Q", title="Canonical trip-stops", format=","),
                ],
            )
            .properties(height=255)
        )
        _render_chart(hour_chart)
        if excluded:
            st.caption(f"{excluded} low-sample hour(s) are excluded from the headline chart and retained below.")
    with st.expander("View all hourly detail"):
        details = hourly[
            [
                "hour_label",
                "on_time_percentage",
                "median_delay_seconds",
                "p90_delay_seconds",
                "observed_trips",
                "observed_trip_stops",
                "sample_label",
            ]
        ].rename(
            columns={
                "hour_label": "Scheduled hour",
                "on_time_percentage": "On-time (%)",
                "median_delay_seconds": "Median delay (sec)",
                "p90_delay_seconds": "P90 delay (sec)",
                "observed_trips": "Observed trips",
                "observed_trip_stops": "Canonical trip-stops",
                "sample_label": "Sample status",
            }
        )
        st.dataframe(details, width="stretch", hide_index=True)


def route_reliability(selected_date: date) -> None:
    routes = query(
        """select distinct route_id, route_short_name, route_long_name from route_delay_summary
           order by coalesce(route_short_name, route_id), route_long_name"""
    )
    if routes.empty:
        st.info("No schedule-matched route performance is available.")
        return
    route_labels = {
        row.route_id: f"Route {row.route_short_name or row.route_id} — {row.route_long_name or 'Name unavailable'}"
        for row in routes.itertuples()
    }
    route_short_labels = {
        row.route_id: f"Route {row.route_short_name or row.route_id}" for row in routes.itertuples()
    }
    selected_route = st.sidebar.selectbox(
        "Route", list(route_labels), format_func=lambda route_id: route_short_labels[route_id]
    )
    selected_label = route_labels[selected_route]
    trend = query("select * from route_delay_summary where route_id = ? order by service_date", [selected_route])
    current_rows = trend[pd.to_datetime(trend["service_date"]).dt.date == selected_date]

    st.markdown(f"## {html.escape(selected_label)}")
    st.markdown(
        "<div class='mct-section-copy'>Punctuality and delay distribution for the selected route and service date.</div>",
        unsafe_allow_html=True,
    )
    if current_rows.empty:
        st.warning(f"This route has no canonical sample on {format_service_date(selected_date)}.")
    else:
        current = current_rows.iloc[0]
        _kpi_grid(
            [
                ("On-time performance", f"{current['on_time_percentage']:.1f}%", "Within the configured window"),
                ("Median delay", format_delay(current["median_delay_seconds"]), "Typical matched trip-stop"),
                ("P90 delay", format_delay(current["p90_delay_seconds"]), "High-end published delay"),
                ("Observed trips", f"{int(current['observed_trips']):,}", "Trips with canonical observations"),
            ]
        )
        sample_label = str(current["sample_size_status"]).replace("_", " ").title()
        st.markdown(
            f"<div class='sample-chip'>{int(current['sample_size']):,} canonical trip-stops · {sample_label}</div>",
            unsafe_allow_html=True,
        )
        if current["sample_size_status"] == "LOW_SAMPLE":
            st.warning("This route-date has a low sample. Treat the percentages and delay distribution cautiously.")

    st.markdown("## Route trend")
    trend_left, trend_right = st.columns(2, gap="large")
    route_otp = (
        alt.Chart(trend)
        .mark_line(point=True, color=ACCENT, strokeWidth=2.4)
        .encode(
            x=alt.X("service_date:T", title=None, axis=alt.Axis(format="%d %b", tickCount="day", labelAngle=0)),
            y=alt.Y("on_time_percentage:Q", title="On-time (%)", scale=alt.Scale(domain=[0, 100])),
            opacity=alt.condition("datum.sample_size_status == 'LOW_SAMPLE'", alt.value(0.32), alt.value(1)),
            tooltip=[
                alt.Tooltip("service_date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("on_time_percentage:Q", title="On-time", format=".1f"),
                alt.Tooltip("sample_size:Q", title="Canonical trip-stops", format=","),
                alt.Tooltip("sample_size_status:N", title="Sample status"),
            ],
        )
        .properties(height=245, title="On-time performance")
    )
    with trend_left:
        _render_chart(route_otp + _selected_rule(selected_date))

    route_delay = trend.melt(
        id_vars=["service_date", "sample_size", "sample_size_status"],
        value_vars=["median_delay_seconds", "p90_delay_seconds"],
        var_name="measure",
        value_name="delay_seconds",
    )
    route_delay["measure"] = route_delay["measure"].map(
        {"median_delay_seconds": "Median", "p90_delay_seconds": "P90"}
    )
    route_delay_chart = (
        alt.Chart(route_delay)
        .mark_line(point=True, strokeWidth=2.2)
        .encode(
            x=alt.X("service_date:T", title=None, axis=alt.Axis(format="%d %b", tickCount="day", labelAngle=0)),
            y=alt.Y("delay_seconds:Q", title="Published delay (sec)"),
            color=alt.Color("measure:N", title=None, scale=alt.Scale(range=[SUCCESS, WARNING])),
            opacity=alt.condition("datum.sample_size_status == 'LOW_SAMPLE'", alt.value(0.3), alt.value(1)),
            tooltip=[
                alt.Tooltip("service_date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("measure:N", title="Measure"),
                alt.Tooltip("delay_seconds:Q", title="Delay (sec)", format=".0f"),
                alt.Tooltip("sample_size:Q", title="Canonical trip-stops", format=","),
            ],
        )
        .properties(height=245, title="Median and P90 delay")
    )
    with trend_right:
        _render_chart(route_delay_chart + _selected_rule(selected_date))

    st.markdown("## Routes at a glance")
    st.markdown(
        "<div class='mct-section-copy'>Ten routes with sufficient samples, ordered descriptively by on-time performance.</div>",
        unsafe_allow_html=True,
    )
    ranking = query(
        """select coalesce(route_short_name, route_id) as route,
                  coalesce(route_long_name, 'Name unavailable') as route_name,
                  on_time_percentage, median_delay_seconds, p90_delay_seconds, observed_trips, sample_size
           from route_delay_summary where service_date = ? and sample_size_status = 'SUFFICIENT_SAMPLE'
           order by on_time_percentage desc, sample_size desc limit 10""",
        [selected_date],
    )
    if ranking.empty:
        st.info("No routes meet the sufficient-sample threshold on this date.")
    else:
        _route_table(ranking)
    with st.expander("View selected route daily detail"):
        details = trend.copy()
        details["service_date"] = details["service_date"].map(format_service_date)
        details = details[
            [
                "service_date",
                "on_time_percentage",
                "median_delay_seconds",
                "p90_delay_seconds",
                "observed_trips",
                "observed_trip_stops",
                "sample_size_status",
            ]
        ].rename(
            columns={
                "service_date": "Service date",
                "on_time_percentage": "On-time (%)",
                "median_delay_seconds": "Median delay (sec)",
                "p90_delay_seconds": "P90 delay (sec)",
                "observed_trips": "Observed trips",
                "observed_trip_stops": "Canonical trip-stops",
                "sample_size_status": "Sample status",
            }
        )
        st.dataframe(details, width="stretch", hide_index=True)


def feed_health(window_hours: int) -> None:
    summary = query("select * from data_coverage_summary").iloc[0]
    latest = query("select * from feed_freshness order by collected_at desc limit 1").iloc[0]
    recent_health = query(
        """with latest as (select max(collected_at) as latest_at from feed_freshness)
           select count(*) as snapshots,
                  round(100.0 * count(*) filter (where freshness_status = 'FRESH') / count(*), 1) as fresh_percentage
           from feed_freshness, latest where collected_at >= latest_at - (? * interval '1 hour')""",
        [window_hours],
    ).iloc[0]
    st.markdown("## Feed health")
    st.markdown(
        "<div class='mct-section-copy'>Collection freshness, schedule matchability, and the limits of current coverage.</div>",
        unsafe_allow_html=True,
    )
    window_value = window_hours // 24 if window_hours >= 24 else window_hours
    window_unit = "d" if window_hours >= 24 else "h"
    _kpi_grid(
        [
            ("Latest feed", str(latest["freshness_status"]).title(), "Status of the newest collected snapshot"),
            ("Feed age", format_feed_age(latest["feed_age_seconds"]), "At the latest collection time"),
            (
                f"Fresh snapshots · {window_value}{window_unit}",
                f"{recent_health['fresh_percentage']:.1f}%",
                f"Across {int(recent_health['snapshots']):,} snapshots in the selected window",
            ),
            (
                "Matchable days",
                f"{int(summary['schedule_matchable_days'])} of {int(summary['realtime_history_days'])}",
                "Realtime history inside the current static schedule window",
            ),
        ]
    )
    _metadata(
        [
            ("Snapshots collected", f"{int(summary['realtime_snapshots']):,}"),
            ("Canonical trip-stops", f"{int(summary['canonical_trip_stops']):,}"),
            ("Static schedule", f"{format_service_date(summary['schedule_start_date'])}–{format_service_date(summary['schedule_end_date'])}"),
            ("Latest rebuild", pd.Timestamp(summary["rebuilt_at"]).strftime("%d %b %Y, %H:%M UTC")),
        ]
    )

    st.markdown("## Feed freshness")
    st.markdown(
        "<div class='mct-section-copy'>Fresh ≤ 90 sec · delayed ≤ 300 sec · stale &gt; 300 sec. "
        "Values above 10 minutes are capped in the chart for legibility, but tooltips retain the actual age.</div>",
        unsafe_allow_html=True,
    )
    freshness = query(
        """with latest as (select max(collected_at) as latest_at from feed_freshness)
           select * from feed_freshness, latest
           where collected_at >= latest_at - (? * interval '1 hour') order by collected_at""",
        [window_hours],
    )
    freshness["display_age_seconds"] = freshness["feed_age_seconds"].clip(upper=600)
    freshness_chart = (
        alt.Chart(freshness)
        .mark_area(line={"color": ACCENT, "strokeWidth": 1.7}, color="#DBEAFE", opacity=0.55)
        .encode(
            x=alt.X("collected_at:T", title=None),
            y=alt.Y("display_age_seconds:Q", title="Feed age (sec)", scale=alt.Scale(domain=[0, 600])),
            tooltip=[
                alt.Tooltip("collected_at:T", title="Collected", format="%d %b %Y %H:%M"),
                alt.Tooltip("feed_age_seconds:Q", title="Actual feed age (sec)"),
                alt.Tooltip("freshness_status:N", title="Status"),
            ],
        )
        .properties(height=250)
    )
    thresholds = pd.DataFrame({"seconds": [90, 300], "threshold": ["Fresh limit", "Delayed limit"]})
    rules = alt.Chart(thresholds).mark_rule(strokeDash=[5, 4], strokeWidth=1.4).encode(
        y="seconds:Q",
        color=alt.Color(
            "threshold:N", title=None, scale=alt.Scale(domain=["Fresh limit", "Delayed limit"], range=[SUCCESS, WARNING])
        ),
    )
    _render_chart(freshness_chart + rules)

    daily = query(
        """select collection_date, freshness_status, count(*) as snapshots from feed_freshness
           group by 1, 2 order by 1, 2"""
    )
    st.markdown("## Daily feed-health mix")
    daily_chart = (
        alt.Chart(daily)
        .mark_bar()
        .encode(
            x=alt.X(
                "collection_date:T",
                title=None,
                axis=alt.Axis(format="%d %b", tickCount="day", labelAngle=0, grid=False),
            ),
            y=alt.Y("snapshots:Q", stack="normalize", title="Share of snapshots", axis=alt.Axis(format="%")),
            color=alt.Color(
                "freshness_status:N",
                title=None,
                scale=alt.Scale(
                    domain=["FRESH", "DELAYED", "STALE", "UNKNOWN"],
                    range=[SUCCESS, WARNING, DANGER, UNKNOWN],
                ),
            ),
            tooltip=[
                alt.Tooltip("collection_date:T", title="Collection date", format="%d %b %Y"),
                alt.Tooltip("freshness_status:N", title="Status"),
                alt.Tooltip("snapshots:Q", title="Snapshots", format=","),
            ],
        )
        .properties(height=225)
    )
    _render_chart(daily_chart)

    st.markdown("## Schedule representation")
    st.markdown(
        "<div class='mct-section-copy'>Trips without a matching realtime observation remain unknown; they are not "
        "treated as cancelled, late, or on time.</div>",
        unsafe_allow_html=True,
    )
    coverage = query("select * from realtime_coverage order by service_date")
    coverage["date_label"] = coverage["service_date"].map(lambda value: pd.Timestamp(value).strftime("%d %b"))
    coverage["coverage_label"] = coverage["coverage_percentage"].map(lambda value: f"{value:.1f}% matched")
    coverage_long = coverage.melt(
        id_vars=["service_date", "date_label", "coverage_percentage", "coverage_label", "scheduled_trips"],
        value_vars=["matched_realtime_trips", "unknown_trips"],
        var_name="coverage_type",
        value_name="trips",
    )
    coverage_long["coverage_type"] = coverage_long["coverage_type"].map(
        {"matched_realtime_trips": "Matched realtime", "unknown_trips": "Unknown / unmatched"}
    )
    coverage_long["share"] = 100 * coverage_long["trips"] / coverage_long["scheduled_trips"]
    y_encoding = alt.Y(
        "date_label:N",
        title=None,
        sort=alt.SortField(field="service_date", order="descending"),
        axis=alt.Axis(labelPadding=8),
    )
    coverage_bars = alt.Chart(coverage_long).mark_bar(size=22).encode(
        x=alt.X("share:Q", stack="zero", title="Share of scheduled trips", scale=alt.Scale(domain=[0, 112])),
        y=y_encoding,
        color=alt.Color(
            "coverage_type:N",
            title=None,
            scale=alt.Scale(domain=["Matched realtime", "Unknown / unmatched"], range=[ACCENT, UNKNOWN]),
        ),
        tooltip=[
            alt.Tooltip("service_date:T", title="Service date", format="%d %b %Y"),
            alt.Tooltip("coverage_type:N", title="Coverage type"),
            alt.Tooltip("trips:Q", title="Trips", format=","),
            alt.Tooltip("share:Q", title="Share", format=".1f"),
            alt.Tooltip("scheduled_trips:Q", title="Scheduled trips", format=","),
        ],
    )
    coverage_labels = alt.Chart(coverage).mark_text(align="left", dx=7, color="#475569", fontSize=11).encode(
        x=alt.datum(100), y=y_encoding, text="coverage_label:N"
    )
    _render_chart((coverage_bars + coverage_labels).properties(height=210))

    with st.expander("Source-data quality diagnostics"):
        source_total = int(query("select count(*) as source_keys from int_delay_observations").iloc[0]["source_keys"])
        quality = pd.DataFrame(
            [
                {
                    "Check": "Ambiguous source keys",
                    "Count": int(summary["ambiguous_source_keys"]),
                    "Percent of source keys": 100 * int(summary["ambiguous_source_keys"]) / source_total,
                    "Meaning": "A poll-grain key resolves to more than one conflicting value.",
                    "Handling": "Excluded before canonical KPI aggregation.",
                },
                {
                    "Check": "Out-of-range source keys",
                    "Count": int(summary["out_of_range_source_keys"]),
                    "Percent of source keys": 100 * int(summary["out_of_range_source_keys"]) / source_total,
                    "Meaning": "Published delays fall outside the accepted validation range.",
                    "Handling": "Excluded before canonical KPI aggregation.",
                },
                {
                    "Check": "Missing-delay source keys",
                    "Count": int(summary["missing_delay_source_keys"]),
                    "Percent of source keys": 100 * int(summary["missing_delay_source_keys"]) / source_total,
                    "Meaning": "No usable delay value was published for the source key.",
                    "Handling": "Retained as unknown; not scored for punctuality.",
                },
            ]
        )
        st.caption(f"Denominator: {source_total:,} poll-grain source keys in int_delay_observations.")
        st.dataframe(
            quality,
            width="stretch",
            hide_index=True,
            column_config={
                "Count": st.column_config.NumberColumn(format="%d"),
                "Percent of source keys": st.column_config.NumberColumn(format="%.3f%%"),
            },
        )
    with st.expander("View recent feed snapshots"):
        recent = query(
            """select collected_at, feed_age_seconds, freshness_status, entity_count, trip_update_count,
                      stop_time_update_count from feed_freshness order by collected_at desc limit 20"""
        ).rename(
            columns={
                "collected_at": "Collected at",
                "feed_age_seconds": "Feed age (seconds)",
                "freshness_status": "Status",
                "entity_count": "Entities",
                "trip_update_count": "Trip updates",
                "stop_time_update_count": "Stop updates",
            }
        )
        recent["Collected at"] = pd.to_datetime(recent["Collected at"]).dt.strftime("%d %b %Y, %H:%M")
        st.dataframe(recent, width="stretch", hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Toulouse Mobility Control Tower", page_icon="🚇", layout="wide")
    _style()
    if not DB_PATH.is_file():
        st.error(f"DuckDB file not found at {DB_PATH}. Run a pipeline before opening the dashboard.")
        st.stop()
    try:
        missing = missing_required_marts()
    except duckdb.Error as error:
        st.error(f"DuckDB could not be opened at {DB_PATH}: {error}")
        st.stop()
    if missing:
        st.error(
            "The analytics database is only partially built. Missing required marts: "
            f"{', '.join(missing)}. Rebuild it with "
            "`python -m mobility_control_tower.cli --data-root .\\data dbt-build`."
        )
        st.stop()

    st.sidebar.markdown("### Mobility Control Tower")
    st.sidebar.caption("Toulouse network operations")
    pages = ("Overview", "Routes", "Data quality")
    requested_page = st.query_params.get("page", "Overview")
    requested_page = requested_page if requested_page in pages else "Overview"
    page = st.sidebar.radio("Navigation", pages, index=pages.index(requested_page), label_visibility="collapsed")
    compatible_dates = query(
        """select performance.service_date from network_on_time_performance performance
           inner join realtime_coverage coverage using (service_date) order by service_date desc"""
    )["service_date"].dt.date.tolist()
    if not compatible_dates:
        st.warning("No service dates are currently matchable between realtime history and the static schedule.")
        st.stop()

    if page in ("Overview", "Routes"):
        selected_date = st.sidebar.selectbox("Service date", compatible_dates, format_func=format_service_date)
        period_label = format_service_date(selected_date)
        window_hours = 48
    else:
        selected_date = compatible_dates[0]
        windows = {"Last 24 hours": 24, "Last 48 hours": 48, "Last 7 days": 168}
        window_label = st.sidebar.selectbox("Freshness window", list(windows))
        window_hours = windows[window_label]
        period_label = window_label
    st.sidebar.markdown("---")
    st.sidebar.caption("Read-only analytics · dbt-owned marts")

    _header(period_label)
    if page == "Overview":
        network_overview(selected_date)
    elif page == "Routes":
        route_reliability(selected_date)
    else:
        feed_health(window_hours)
    _methodology()


if __name__ == "__main__":
    main()
