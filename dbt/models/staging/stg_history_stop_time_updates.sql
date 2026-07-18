select
    cast(snapshot_timestamp as varchar) as snapshot_timestamp,
    cast(collection_time as timestamp) as collection_time,
    try_cast(feed_age_seconds as integer) as feed_age_seconds,
    try_cast(poll_number as integer) as poll_number,
    cast(collection_date as varchar) as collection_date,
    cast(collection_hour as varchar) as collection_hour,
    cast(trip_id as varchar) as trip_id,
    cast(route_id as varchar) as route_id,
    cast(stop_id as varchar) as stop_id,
    coalesce(try_cast(arrival_delay as double), try_cast(departure_delay as double)) as delay_seconds
from {{ history_parquet('stop_time_updates.parquet') }}

