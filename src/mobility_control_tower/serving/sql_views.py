"""SQL view definitions for the local DuckDB serving layer."""

from __future__ import annotations

from pathlib import Path

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


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def create_history_views(connection: duckdb.DuckDBPyConnection, history_run: Path | None = None, history_gold_run: Path | None = None) -> list[str]:
    """Create read-through views over partitioned historical Parquet datasets."""
    created: list[str] = []
    if history_run is not None:
        stop_updates = str((history_run / "date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet").resolve())
        feed_summary = str((history_run / "date=*/hour=*/snapshot_timestamp=*/feed_summary.parquet").resolve())
        connection.execute(
            """
            CREATE OR REPLACE VIEW v_delay_history AS
            SELECT
                snapshot_timestamp,
                collection_time,
                feed_age_seconds,
                poll_number,
                collection_date,
                collection_hour,
                trip_id,
                route_id,
                stop_id,
                stop_sequence,
                COALESCE(TRY_CAST(NULLIF(CAST(arrival_delay AS VARCHAR), '') AS DOUBLE),
                         TRY_CAST(NULLIF(CAST(departure_delay AS VARCHAR), '') AS DOUBLE)) AS delay_seconds,
                arrival_delay,
                departure_delay,
                arrival_time,
                departure_time,
                schedule_relationship
            FROM read_parquet({stop_updates}, hive_partitioning = true)
            """.format(stop_updates=_sql_string(stop_updates)),
        )
        created.append("v_delay_history")
        connection.execute(
            """
            CREATE OR REPLACE VIEW v_feed_health_history AS
            SELECT
                snapshot_timestamp,
                collection_time,
                feed_age_seconds,
                poll_number,
                collection_date,
                collection_hour,
                feed_type,
                gtfs_realtime_version,
                header_timestamp,
                header_timestamp_iso,
                entity_count,
                parsed_entity_count,
                skipped_entity_count
            FROM read_parquet({feed_summary}, hive_partitioning = true)
            ORDER BY collection_time
            """.format(feed_summary=_sql_string(feed_summary)),
        )
        created.append("v_feed_health_history")
        connection.execute(
            """
            CREATE OR REPLACE VIEW v_collection_summary AS
            SELECT
                collection_date,
                collection_hour,
                COUNT(DISTINCT snapshot_timestamp) AS snapshots_collected,
                COUNT(*) AS updates_collected,
                COUNT(DISTINCT route_id) AS routes_observed,
                COUNT(DISTINCT stop_id) AS stops_observed,
                AVG(delay_seconds) AS average_delay_seconds,
                MAX(delay_seconds) AS maximum_observed_delay_seconds,
                MIN(delay_seconds) AS minimum_observed_delay_seconds
            FROM v_delay_history
            GROUP BY collection_date, collection_hour
            ORDER BY collection_date, collection_hour
            """
        )
        created.append("v_collection_summary")
    if history_gold_run is not None:
        route_delay = history_gold_run / "route_delay_history.parquet"
        stop_delay = history_gold_run / "stop_delay_history.parquet"
        if route_delay.is_file():
            connection.execute(
                """
                CREATE OR REPLACE VIEW v_route_delay_history AS
                SELECT *
                FROM read_parquet({route_delay})
                ORDER BY average_delay_seconds DESC NULLS LAST
                """.format(route_delay=_sql_string(str(route_delay.resolve()))),
            )
            created.append("v_route_delay_history")
        if stop_delay.is_file():
            connection.execute(
                """
                CREATE OR REPLACE VIEW v_stop_delay_history AS
                SELECT *
                FROM read_parquet({stop_delay})
                ORDER BY average_delay_seconds DESC NULLS LAST
                """.format(stop_delay=_sql_string(str(stop_delay.resolve()))),
            )
            created.append("v_stop_delay_history")
    elif history_run is not None:
        connection.execute(
            """
            CREATE OR REPLACE VIEW v_route_delay_history AS
            SELECT
                route_id,
                COUNT(*) AS updates_collected,
                AVG(delay_seconds) AS average_delay_seconds,
                MAX(delay_seconds) AS maximum_observed_delay_seconds,
                MIN(delay_seconds) AS minimum_observed_delay_seconds,
                QUANTILE_CONT(delay_seconds, 0.95) AS p95_delay_seconds,
                COUNT(DISTINCT snapshot_timestamp) AS snapshots_observed
            FROM v_delay_history
            GROUP BY route_id
            ORDER BY average_delay_seconds DESC NULLS LAST
            """
        )
        created.append("v_route_delay_history")
        connection.execute(
            """
            CREATE OR REPLACE VIEW v_stop_delay_history AS
            SELECT
                stop_id,
                COUNT(*) AS updates_collected,
                AVG(delay_seconds) AS average_delay_seconds,
                MAX(delay_seconds) AS maximum_observed_delay_seconds,
                MIN(delay_seconds) AS minimum_observed_delay_seconds,
                QUANTILE_CONT(delay_seconds, 0.95) AS p95_delay_seconds,
                COUNT(DISTINCT snapshot_timestamp) AS snapshots_observed
            FROM v_delay_history
            GROUP BY stop_id
            ORDER BY average_delay_seconds DESC NULLS LAST
            """
        )
        created.append("v_stop_delay_history")
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
    "history-routes": "SELECT * FROM v_route_delay_history LIMIT {limit}",
    "history-stops": "SELECT * FROM v_stop_delay_history LIMIT {limit}",
    "history-feed-health": "SELECT * FROM v_feed_health_history LIMIT {limit}",
    "history-delay-trend": "SELECT * FROM v_collection_summary LIMIT {limit}",
    "history-summary": "SELECT * FROM v_collection_summary LIMIT {limit}",
}
