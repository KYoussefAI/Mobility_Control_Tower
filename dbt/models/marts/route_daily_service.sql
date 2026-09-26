with departures as (
    select trip_id, count(*) as scheduled_departures
    from {{ ref('stg_stop_times') }}
    group by trip_id
)
select
    trips.service_date,
    trips.route_id,
    trips.route_short_name,
    trips.route_long_name,
    count(distinct trips.trip_id) as scheduled_trips,
    sum(coalesce(departures.scheduled_departures, 0)) as scheduled_departures
from {{ ref('int_scheduled_trips') }} trips
left join departures using (trip_id)
group by 1, 2, 3, 4

