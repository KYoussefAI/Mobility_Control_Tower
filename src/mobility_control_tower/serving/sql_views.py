"""SQL views for the available serving capabilities."""

from pathlib import Path

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
    "v_network_reliability": ("network_reliability_summary", "SELECT * FROM network_reliability_summary"),
    "v_route_reliability": ("route_delay_distribution", "SELECT * FROM route_delay_distribution"),
    "v_headway_reliability": ("fct_observed_headways", "SELECT * FROM fct_observed_headways"),
    "v_reliability_incident_snapshot": ("reliability_incident_snapshot", "SELECT * FROM reliability_incident_snapshot"),
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
    "network-reliability": "SELECT * FROM v_network_reliability LIMIT {limit}",
    "route-reliability": "SELECT * FROM v_route_reliability LIMIT {limit}",
    "observed-headways": "SELECT * FROM v_headway_reliability LIMIT {limit}",
    "history-routes": "SELECT * FROM v_route_delay_history LIMIT {limit}",
    "history-stops": "SELECT * FROM v_stop_delay_history LIMIT {limit}",
    "history-feed-health": "SELECT * FROM v_feed_health_history LIMIT {limit}",
    "history-summary": "SELECT * FROM v_collection_summary LIMIT {limit}",
}


QUERY_SQL["history-delay-trend"] = "SELECT * FROM v_collection_summary LIMIT {limit}"


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def create_views(connection: duckdb.DuckDBPyConnection, loaded_tables: set[str]) -> list[str]:
    created: list[str] = []
    for view, (required_table, select_sql) in VIEW_DEFINITIONS.items():
        if required_table in loaded_tables:
            connection.execute(f"CREATE OR REPLACE VIEW {view} AS {select_sql}")
            created.append(view)
    return created


def create_history_views(connection: duckdb.DuckDBPyConnection, history_run: Path | None = None, history_gold_run: Path | None = None) -> list[str]:
    created: list[str] = []
    if history_run is not None:
        updates = history_run / "date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet"
        feeds = history_run / "date=*/hour=*/snapshot_timestamp=*/feed_summary.parquet"
        if list(history_run.glob("date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet")):
            connection.execute(f"CREATE OR REPLACE VIEW v_delay_history AS SELECT * FROM read_parquet({_sql_string(str(updates.resolve()))})")
            connection.execute(
                """
                CREATE OR REPLACE VIEW v_collection_summary AS
                SELECT
                    source,
                    collection_date,
                    collection_hour,
                    COUNT(DISTINCT snapshot_timestamp) AS snapshots_collected,
                    COUNT(*) AS updates_collected,
                    AVG(COALESCE(TRY_CAST(arrival_delay AS DOUBLE), TRY_CAST(departure_delay AS DOUBLE))) AS average_delay_seconds
                FROM v_delay_history
                GROUP BY source, collection_date, collection_hour
                ORDER BY collection_date, collection_hour
                """
            )
            created.extend(["v_delay_history", "v_collection_summary"])
        if list(history_run.glob("date=*/hour=*/snapshot_timestamp=*/feed_summary.parquet")):
            connection.execute(f"CREATE OR REPLACE VIEW v_feed_health_history AS SELECT * FROM read_parquet({_sql_string(str(feeds.resolve()))})")
            created.append("v_feed_health_history")
    if history_gold_run is not None:
        for view, file_name in (("v_route_delay_history", "route_delay_history.parquet"), ("v_stop_delay_history", "stop_delay_history.parquet")):
            path = history_gold_run / file_name
            if path.is_file():
                connection.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet({_sql_string(str(path.resolve()))})")
                created.append(view)
    return created
