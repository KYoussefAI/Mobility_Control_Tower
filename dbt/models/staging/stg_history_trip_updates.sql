select
    coalesce(cast(source as varchar), '{{ var("source_id", "tisseo") }}') as source,
    cast(snapshot_id as varchar) as snapshot_id,
    cast(snapshot_timestamp as varchar) as snapshot_timestamp,
    cast(collection_time as timestamp) as collection_time,
    cast(feed_header_timestamp as varchar) as feed_header_timestamp,
    try_cast(feed_age_seconds as integer) as feed_age_seconds,
    try_cast(poll_number as integer) as poll_number,
    cast(collection_date as varchar) as collection_date,
    cast(collection_hour as varchar) as collection_hour,
    cast(feed_type as varchar) as feed_type,
    cast(trip_id as varchar) as trip_id,
    cast(route_id as varchar) as route_id,
    cast(schedule_relationship as varchar) as schedule_relationship
from {{ history_parquet('trip_updates.parquet') }}
