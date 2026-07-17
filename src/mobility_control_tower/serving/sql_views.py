"""SQL view definitions for the local DuckDB serving layer."""

from __future__ import annotations

import duckdb


STATIC_VIEW_SQL = {
    "v_network_overview": """
        CREATE OR REPLACE VIEW v_network_overview AS
        SELECT
            service_date,
            active_routes_count,
            scheduled_trips_count,
            scheduled_stop_departures_count,
            active_stops_count
        FROM network_daily_summary
        ORDER BY service_date
    """,
    "v_top_routes_static": """
        CREATE OR REPLACE VIEW v_top_routes_static AS
        SELECT
            route_id,
            route_short_name,
            route_long_name,
            route_type,
            active_service_days,
            total_scheduled_trips,
            average_trips_per_active_day,
            max_daily_trips
        FROM route_period_summary
        ORDER BY total_scheduled_trips DESC
    """,
    "v_route_hourly_headway": """
        CREATE OR REPLACE VIEW v_route_hourly_headway AS
        SELECT
            service_date,
            route_id,
            route_short_name,
            route_long_name,
            departure_hour,
            scheduled_departures_count,
            planned_headway_minutes
        FROM route_hourly_headway
    """,
    "v_route_type_daily_summary": """
        CREATE OR REPLACE VIEW v_route_type_daily_summary AS
        SELECT *
        FROM route_type_daily_summary
        ORDER BY service_date, route_type
    """,
}

STATIC_VIEW_REQUIREMENTS = {
    "v_network_overview": "network_daily_summary",
    "v_top_routes_static": "route_period_summary",
    "v_route_hourly_headway": "route_hourly_headway",
    "v_route_type_daily_summary": "route_type_daily_summary",
}


OPTIONAL_RT_VIEW_SQL = {
    "v_rt_feed_health": """
        CREATE OR REPLACE VIEW v_rt_feed_health AS
        SELECT *
        FROM rt_feed_health_snapshot
    """,
    "v_rt_identifier_compatibility": """
        CREATE OR REPLACE VIEW v_rt_identifier_compatibility AS
        SELECT *
        FROM rt_identifier_compatibility_snapshot
        ORDER BY identifier_type
    """,
    "v_rt_top_delayed_routes_snapshot": """
        CREATE OR REPLACE VIEW v_rt_top_delayed_routes_snapshot AS
        SELECT
            route_id,
            route_short_name,
            route_long_name,
            stop_time_updates_count,
            distinct_trip_updates_count,
            avg_delay_seconds,
            median_delay_seconds,
            max_delay_seconds,
            delayed_updates_5min_count,
            delayed_updates_5min_pct
        FROM rt_route_delay_snapshot
        ORDER BY avg_delay_seconds DESC NULLS LAST
    """,
    "v_rt_top_delayed_stops_snapshot": """
        CREATE OR REPLACE VIEW v_rt_top_delayed_stops_snapshot AS
        SELECT *
        FROM rt_stop_delay_snapshot
        ORDER BY avg_delay_seconds DESC NULLS LAST
    """,
}


RT_VIEW_REQUIREMENTS = {
    "v_rt_feed_health": "rt_feed_health_snapshot",
    "v_rt_identifier_compatibility": "rt_identifier_compatibility_snapshot",
    "v_rt_top_delayed_routes_snapshot": "rt_route_delay_snapshot",
    "v_rt_top_delayed_stops_snapshot": "rt_stop_delay_snapshot",
}


def create_views(connection: duckdb.DuckDBPyConnection, loaded_tables: set[str]) -> list[str]:
    created: list[str] = []
    for view_name, sql in STATIC_VIEW_SQL.items():
        required_table = STATIC_VIEW_REQUIREMENTS[view_name]
        if required_table in loaded_tables:
            connection.execute(sql)
            created.append(view_name)
    for view_name, sql in OPTIONAL_RT_VIEW_SQL.items():
        required_table = RT_VIEW_REQUIREMENTS[view_name]
        if required_table in loaded_tables:
            connection.execute(sql)
            created.append(view_name)
    return created


QUERY_SQL = {
    "network-overview": "SELECT * FROM v_network_overview ORDER BY service_date LIMIT {limit}",
    "top-routes": "SELECT * FROM v_top_routes_static LIMIT {limit}",
    "hourly-headway": "SELECT * FROM v_route_hourly_headway ORDER BY service_date, route_id, departure_hour LIMIT {limit}",
    "route-types": "SELECT * FROM v_route_type_daily_summary LIMIT {limit}",
    "rt-feed-health": "SELECT * FROM v_rt_feed_health LIMIT {limit}",
    "rt-compatibility": "SELECT * FROM v_rt_identifier_compatibility LIMIT {limit}",
    "rt-top-delayed-routes": "SELECT * FROM v_rt_top_delayed_routes_snapshot LIMIT {limit}",
    "rt-top-delayed-stops": "SELECT * FROM v_rt_top_delayed_stops_snapshot LIMIT {limit}",
}
