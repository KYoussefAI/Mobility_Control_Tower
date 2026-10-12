{{ config(materialized='table') }}

with matched_updates as (
    select
        updates.snapshot_id,
        updates.collected_at,
        updates.update_timestamp,
        coalesce(updates.update_timestamp, updates.collected_at) as effective_update_at,
        updates.service_date,
        updates.entity_id,
        updates.trip_id,
        scheduled.route_id,
        scheduled.route_short_name,
        scheduled.route_long_name,
        stop_times.stop_id,
        updates.stop_sequence,
        stop_times.departure_seconds,
        updates.delay_seconds,
        updates.schedule_relationship,
        updates.is_on_time
    from {{ ref('int_delay_observations') }} updates
    inner join {{ ref('int_scheduled_trips') }} scheduled
        on updates.service_date = scheduled.service_date
        and updates.trip_id = scheduled.trip_id
        and (updates.route_id is null or updates.route_id = scheduled.route_id)
    inner join {{ ref('stg_stop_times') }} stop_times
        on updates.trip_id = stop_times.trip_id
        and updates.stop_sequence = stop_times.stop_sequence
        and (updates.stop_id is null or updates.stop_id = stop_times.stop_id)
    where updates.source_key_status = 'UNAMBIGUOUS'
      and updates.has_known_delay
)

select *
from matched_updates
qualify row_number() over (
    partition by service_date, trip_id, stop_sequence
    order by
        effective_update_at desc,
        collected_at desc,
        snapshot_id desc,
        entity_id desc
) = 1
