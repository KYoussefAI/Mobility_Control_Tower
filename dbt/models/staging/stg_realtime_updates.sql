select
    cast(snapshot_id as varchar) as snapshot_id,
    cast(collected_at as timestamptz) as collected_at,
    try_strptime(cast(service_date as varchar), '%Y%m%d')::date as service_date,
    cast(entity_id as varchar) as entity_id,
    nullif(cast(trip_id as varchar), '') as trip_id,
    nullif(cast(route_id as varchar), '') as route_id,
    cast(schedule_relationship as varchar) as schedule_relationship,
    cast(update_timestamp as timestamptz) as update_timestamp,
    nullif(cast(stop_id as varchar), '') as stop_id,
    cast(stop_sequence as integer) as stop_sequence,
    cast(arrival_delay as integer) as arrival_delay,
    cast(departure_delay as integer) as departure_delay,
    cast(observed_delay as integer) as observed_delay
from read_parquet(
    '{{ var("realtime_path") }}/stop_time_updates/**/*.parquet',
    union_by_name = true,
    hive_partitioning = false
)

