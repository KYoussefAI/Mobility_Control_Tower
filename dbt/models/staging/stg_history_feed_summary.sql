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
    try_cast(entity_count as integer) as entity_count,
    try_cast(parsed_entity_count as integer) as parsed_entity_count,
    try_cast(skipped_entity_count as integer) as skipped_entity_count
from {{ history_parquet('feed_summary.parquet') }}
