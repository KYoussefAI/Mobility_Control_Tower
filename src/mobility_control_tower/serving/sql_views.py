"""SQL views for the available serving capabilities."""

import duckdb

VIEW_DEFINITIONS = {
    "v_network_overview": ("network_daily_summary", "SELECT * FROM network_daily_summary ORDER BY service_date"),
    "v_top_routes_static": ("route_period_summary", "SELECT * FROM route_period_summary ORDER BY total_scheduled_trips DESC"),
    "v_route_hourly_headway": ("route_hourly_headway", "SELECT * FROM route_hourly_headway"),
    "v_route_type_daily_summary": ("route_type_daily_summary", "SELECT * FROM route_type_daily_summary"),
    "v_rt_feed_health": ("rt_feed_health_snapshot", "SELECT * FROM rt_feed_health_snapshot"),
    "v_rt_identifier_compatibility": ("rt_identifier_compatibility_snapshot", "SELECT * FROM rt_identifier_compatibility_snapshot"),
    "v_rt_top_delayed_routes_snapshot": ("rt_route_delay_snapshot", "SELECT * FROM rt_route_delay_snapshot ORDER BY avg_delay_seconds DESC NULLS LAST"),
    "v_rt_top_delayed_stops_snapshot": ("rt_stop_delay_snapshot", "SELECT * FROM rt_stop_delay_snapshot ORDER BY avg_delay_seconds DESC NULLS LAST"),
}
QUERY_SQL = {
    "network-overview": "SELECT * FROM v_network_overview LIMIT {limit}",
    "top-routes": "SELECT * FROM v_top_routes_static LIMIT {limit}",
    "hourly-headway": "SELECT * FROM v_route_hourly_headway LIMIT {limit}",
    "route-types": "SELECT * FROM v_route_type_daily_summary LIMIT {limit}",
    "rt-feed-health": "SELECT * FROM v_rt_feed_health LIMIT {limit}",
    "rt-compatibility": "SELECT * FROM v_rt_identifier_compatibility LIMIT {limit}",
    "rt-routes": "SELECT * FROM v_rt_top_delayed_routes_snapshot LIMIT {limit}",
    "rt-stops": "SELECT * FROM v_rt_top_delayed_stops_snapshot LIMIT {limit}",
}


def create_views(connection: duckdb.DuckDBPyConnection, loaded_tables: set[str]) -> list[str]:
    created: list[str] = []
    for view, (required_table, select_sql) in VIEW_DEFINITIONS.items():
        if required_table in loaded_tables:
            connection.execute(f"CREATE OR REPLACE VIEW {view} AS {select_sql}")
            created.append(view)
    return created
