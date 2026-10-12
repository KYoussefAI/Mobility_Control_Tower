{{ config(materialized='table') }}

with snapshots as (
    select
        cast(snapshot_id as varchar) as snapshot_id,
        cast(collected_at as timestamptz) as collected_at,
        cast(collection_date as date) as collection_date,
        cast(source_url as varchar) as source_url,
        cast(sha256 as varchar) as sha256,
        cast(header_timestamp as timestamptz) as header_timestamp,
        cast(feed_age_seconds as integer) as feed_age_seconds,
        cast(entity_count as integer) as entity_count,
        cast(trip_update_count as integer) as trip_update_count,
        cast(stop_time_update_count as integer) as stop_time_update_count
    from read_parquet(
        '{{ var("realtime_path") }}/feed_snapshots/**/*.parquet',
        union_by_name = true,
        hive_partitioning = false
    )
)

select
    snapshot_id,
    min(collected_at) as collected_at,
    min(collection_date) as collection_date,
    min(source_url) as source_url,
    min(sha256) as sha256,
    min(header_timestamp) as header_timestamp,
    min(feed_age_seconds) as feed_age_seconds,
    min(entity_count) as entity_count,
    min(trip_update_count) as trip_update_count,
    min(stop_time_update_count) as stop_time_update_count
from snapshots
group by snapshot_id
