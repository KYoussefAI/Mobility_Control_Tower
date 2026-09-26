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

