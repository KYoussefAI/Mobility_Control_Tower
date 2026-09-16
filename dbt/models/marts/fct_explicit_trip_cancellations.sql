{{ config(materialized='incremental', unique_key='cancellation_evidence_key', incremental_strategy='delete+insert', on_schema_change='fail') }}

with cancellations as (
    select
        source,
        service_date,
        route_id,
        trip_id,
        schedule_relationship,
        match_status,
        matched_static_run_id,
        snapshot_id,
        collection_time,
        row_number() over (
            partition by source, service_date, trip_id
            order by collection_time
        ) as first_rank,
        row_number() over (
            partition by source, service_date, trip_id
            order by collection_time desc
        ) as last_rank
    from {{ ref('int_realtime_trip_observations') }}
    where is_explicitly_canceled
),
rolled as (
    select
        source,
        service_date,
        route_id,
        trip_id,
        min(collection_time) as first_seen_at,
        max(collection_time) as last_seen_at,
        max(case when first_rank = 1 then snapshot_id end) as first_snapshot_id,
        max(case when last_rank = 1 then snapshot_id end) as last_snapshot_id,
        max(schedule_relationship) as schedule_relationship,
        max(match_status) as match_status,
        max(matched_static_run_id) as matched_static_run_id
    from cancellations
    group by 1, 2, 3, 4
)
select
    source,
    service_date,
    route_id,
    trip_id,
    md5(concat_ws('|', source, service_date, trip_id, 'GTFS_RT_TRIP_SCHEDULE_RELATIONSHIP_CANCELED')) as cancellation_evidence_key,
    first_seen_at,
    last_seen_at,
    first_snapshot_id,
    last_snapshot_id,
    schedule_relationship,
    'GTFS_RT_TRIP_SCHEDULE_RELATIONSHIP_CANCELED' as evidence_type,
    match_status,
    matched_static_run_id,
    cast(null as varchar) as related_alert_id,
    'reliability_v1' as calculation_version
from rolled
