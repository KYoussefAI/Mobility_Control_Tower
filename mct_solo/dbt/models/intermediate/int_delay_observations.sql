with deduplicated as (
    select * exclude (_row_number)
    from (
        select
            updates.*,
            row_number() over (
                partition by snapshot_id, entity_id, stop_sequence
                order by collected_at desc
            ) as _row_number
        from {{ ref('stg_realtime_updates') }} updates
    )
    where _row_number = 1
)
select
    updates.snapshot_id,
    updates.collected_at,
    coalesce(
        updates.service_date,
        cast(timezone('Europe/Paris', updates.collected_at) as date)
    ) as service_date,
    updates.entity_id,
    updates.trip_id,
    coalesce(updates.route_id, trips.route_id) as route_id,
    routes.route_short_name,
    routes.route_long_name,
    updates.stop_id,
    updates.stop_sequence,
    stop_times.departure_seconds,
    updates.observed_delay as delay_seconds,
    updates.schedule_relationship,
    trips.trip_id is not null as static_trip_match,
    updates.observed_delay is not null as raw_delay_present,
    updates.observed_delay is not null and abs(updates.observed_delay) <= 7200 as has_known_delay,
    case
        when updates.observed_delay is null then 'MISSING'
        when abs(updates.observed_delay) > 7200 then 'OUT_OF_RANGE'
        else 'VALID'
    end as delay_quality_status,
    updates.observed_delay between {{ var('on_time_early_seconds') }} and {{ var('on_time_late_seconds') }} as is_on_time
from deduplicated updates
left join {{ ref('stg_trips') }} trips using (trip_id)
left join {{ ref('stg_routes') }} routes on coalesce(updates.route_id, trips.route_id) = routes.route_id
left join {{ ref('stg_stop_times') }} stop_times
    on updates.trip_id = stop_times.trip_id
    and updates.stop_sequence = stop_times.stop_sequence
