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

RELIABILITY_VIEW_SQL = {
    "v_network_reliability": """
        CREATE OR REPLACE VIEW v_network_reliability AS
        SELECT *
        FROM network_reliability_summary
    """,
    "v_network_reliability_summary": """
        CREATE OR REPLACE VIEW v_network_reliability_summary AS
        SELECT *
        FROM network_reliability_summary
    """,
    "v_route_reliability": """
        CREATE OR REPLACE VIEW v_route_reliability AS
        SELECT
            d.source,
            d.service_date,
            d.service_period,
            d.route_id,
            d.calculation_version,
            d.eligible_observation_count,
            d.distinct_trip_count,
            d.missing_delay_count,
            d.early_observation_count,
            d.on_time_observation_count,
            d.late_observation_count,
            d.severe_delay_observation_count,
            d.average_delay_seconds,
            d.median_delay_seconds,
            d.p90_delay_seconds,
            d.p95_delay_seconds,
            d.minimum_delay_seconds,
            d.maximum_delay_seconds,
            otp.on_time_percentage,
            d.coverage_percentage,
            d.confidence_status,
            'dbt_authoritative_reliability_mart' AS source_model
        FROM route_delay_distribution d
        LEFT JOIN route_on_time_performance otp
          ON d.source = otp.source
         AND d.service_date = otp.service_date
         AND d.service_period = otp.service_period
         AND d.route_id = otp.route_id
    """,
    "v_route_on_time_performance": """
        CREATE OR REPLACE VIEW v_route_on_time_performance AS
        SELECT * FROM route_on_time_performance
    """,
    "v_route_delay_distribution": """
        CREATE OR REPLACE VIEW v_route_delay_distribution AS
        SELECT * FROM route_delay_distribution
    """,
    "v_explicit_cancellations": """
        CREATE OR REPLACE VIEW v_explicit_cancellations AS
        SELECT * FROM fct_explicit_trip_cancellations
    """,
    "v_observed_headways": """
        CREATE OR REPLACE VIEW v_observed_headways AS
        SELECT * FROM fct_observed_headways
    """,
    "v_headway_reliability_events": """
        CREATE OR REPLACE VIEW v_headway_reliability_events AS
        SELECT * FROM fct_headway_reliability_events
    """,
    "v_headway_reliability": """
        CREATE OR REPLACE VIEW v_headway_reliability AS
        SELECT * FROM fct_observed_headways
    """,
    "v_excess_waiting_time": """
        CREATE OR REPLACE VIEW v_excess_waiting_time AS
        SELECT * FROM route_excess_waiting_time
    """,
    "v_realtime_trip_coverage": """
        CREATE OR REPLACE VIEW v_realtime_trip_coverage AS
        SELECT * FROM realtime_trip_coverage
    """,
    "v_reliability_incident_snapshot": """
        CREATE OR REPLACE VIEW v_reliability_incident_snapshot AS
        SELECT * FROM reliability_incident_snapshot
    """,
}


RT_VIEW_REQUIREMENTS = {
    "v_rt_feed_health": "rt_feed_health_snapshot",
    "v_rt_identifier_compatibility": "rt_identifier_compatibility_snapshot",
    "v_rt_top_delayed_routes_snapshot": "rt_route_delay_snapshot",
    "v_rt_top_delayed_stops_snapshot": "rt_stop_delay_snapshot",
}

RELIABILITY_VIEW_REQUIREMENTS = {
    "v_network_reliability": "network_reliability_summary",
    "v_network_reliability_summary": "network_reliability_summary",
    "v_route_reliability": "route_delay_distribution",
    "v_route_on_time_performance": "route_on_time_performance",
    "v_route_delay_distribution": "route_delay_distribution",
    "v_explicit_cancellations": "fct_explicit_trip_cancellations",
    "v_observed_headways": "fct_observed_headways",
    "v_headway_reliability_events": "fct_headway_reliability_events",
    "v_headway_reliability": "fct_observed_headways",
    "v_excess_waiting_time": "route_excess_waiting_time",
    "v_realtime_trip_coverage": "realtime_trip_coverage",
    "v_reliability_incident_snapshot": "reliability_incident_snapshot",
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
    for view_name, sql in RELIABILITY_VIEW_SQL.items():
        required_table = RELIABILITY_VIEW_REQUIREMENTS[view_name]
        if required_table in loaded_tables:
            connection.execute(sql)
            created.append(view_name)
    return created


def create_history_views(connection: duckdb.DuckDBPyConnection, history_run: Path | None = None, history_gold_run: Path | None = None) -> list[str]:
    """Create read-through views over partitioned historical Parquet datasets."""
    created: list[str] = []
    if history_run is not None:
        stop_update_files = list(history_run.glob("date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet"))
        if stop_update_files:
            stop_updates = str((history_run / "date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet").resolve())
            feed_summary = str((history_run / "date=*/hour=*/snapshot_timestamp=*/feed_summary.parquet").resolve())
            connection.execute(
                f"""
            CREATE OR REPLACE VIEW v_delay_history AS
            SELECT
                source,
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
            FROM read_parquet({_sql_string(stop_updates)}, hive_partitioning = true)
            """,
            )
            created.append("v_delay_history")
            connection.execute(
                f"""
            CREATE OR REPLACE VIEW v_feed_health_history AS
            SELECT
                source,
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
            FROM read_parquet({_sql_string(feed_summary)}, hive_partitioning = true)
            ORDER BY collection_time
            """,
            )
            created.append("v_feed_health_history")
            connection.execute(
                """
            CREATE OR REPLACE VIEW v_collection_summary AS
            SELECT
                source,
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
            GROUP BY source, collection_date, collection_hour
            ORDER BY source, collection_date, collection_hour
            """
            )
            created.append("v_collection_summary")
        vehicle_files = list(history_run.glob("date=*/hour=*/snapshot_timestamp=*/vehicle_positions.parquet"))
        if vehicle_files:
            vehicle_positions = str((history_run / "date=*/hour=*/snapshot_timestamp=*/vehicle_positions.parquet").resolve())
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW v_latest_vehicle_positions AS
                WITH ranked AS (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY source, vehicle_id ORDER BY collection_time DESC, snapshot_timestamp DESC) AS rn
                    FROM read_parquet({_sql_string(vehicle_positions)}, hive_partitioning = true)
                )
                SELECT
                    source,
                    snapshot_id,
                    collection_time,
                    feed_header_timestamp,
                    entity_id,
                    vehicle_id,
                    trip_id,
                    route_id,
                    current_stop_sequence,
                    stop_id,
                    current_status,
                    TRY_CAST(latitude AS DOUBLE) AS latitude,
                    TRY_CAST(longitude AS DOUBLE) AS longitude,
                    TRY_CAST(bearing AS DOUBLE) AS bearing,
                    TRY_CAST(speed AS DOUBLE) AS speed,
                    timestamp AS vehicle_timestamp,
                    CASE
                        WHEN TRY_CAST(latitude AS DOUBLE) BETWEEN -90 AND 90
                         AND TRY_CAST(longitude AS DOUBLE) BETWEEN -180 AND 180 THEN false
                        ELSE true
                    END AS invalid_coordinate_flag,
                    CASE WHEN feed_age_seconds > 90 THEN true ELSE false END AS stale_position_flag
                FROM ranked
                WHERE rn = 1
                ORDER BY collection_time DESC
                """
            )
            created.append("v_latest_vehicle_positions")

        alert_files = list(history_run.glob("date=*/hour=*/snapshot_timestamp=*/alerts.parquet"))
        informed_files = list(history_run.glob("date=*/hour=*/snapshot_timestamp=*/alert_informed_entities.parquet"))
        if alert_files and informed_files:
            alerts = str((history_run / "date=*/hour=*/snapshot_timestamp=*/alerts.parquet").resolve())
            informed = str((history_run / "date=*/hour=*/snapshot_timestamp=*/alert_informed_entities.parquet").resolve())
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW v_active_service_alerts AS
                SELECT
                    a.source,
                    a.snapshot_id,
                    a.entity_id AS alert_id,
                    a.cause,
                    a.effect,
                    a.active_period_start,
                    a.active_period_end,
                    a.header_text,
                    a.description_text,
                    i.agency_id,
                    i.route_id,
                    i.route_type,
                    i.stop_id,
                    i.trip_id,
                    CASE
                        WHEN NULLIF(CAST(a.active_period_end AS VARCHAR), '') IS NULL THEN true
                        WHEN TRY_CAST(a.active_period_end AS BIGINT) >= epoch(now()) THEN true
                        ELSE false
                    END AS currently_active
                FROM read_parquet({_sql_string(alerts)}, hive_partitioning = true) a
                LEFT JOIN read_parquet({_sql_string(informed)}, hive_partitioning = true) i
                  ON a.source = i.source
                 AND a.snapshot_id = i.snapshot_id
                 AND a.entity_id = i.entity_id
                WHERE
                    NULLIF(CAST(a.active_period_end AS VARCHAR), '') IS NULL
                    OR TRY_CAST(a.active_period_end AS BIGINT) >= epoch(now())
                ORDER BY a.collection_time DESC
                """
            )
            created.append("v_active_service_alerts")
    if history_gold_run is not None:
        route_delay = history_gold_run / "route_delay_history.parquet"
        stop_delay = history_gold_run / "stop_delay_history.parquet"
        if route_delay.is_file():
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW v_route_delay_history AS
                SELECT *
                FROM read_parquet({_sql_string(str(route_delay.resolve()))})
                ORDER BY average_delay_seconds DESC NULLS LAST
                """,
            )
            created.append("v_route_delay_history")
        if stop_delay.is_file():
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW v_stop_delay_history AS
                SELECT *
                FROM read_parquet({_sql_string(str(stop_delay.resolve()))})
                ORDER BY average_delay_seconds DESC NULLS LAST
                """,
            )
            created.append("v_stop_delay_history")
    elif history_run is not None and "v_delay_history" in created:
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
