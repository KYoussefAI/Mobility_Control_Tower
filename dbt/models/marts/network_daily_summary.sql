with route_summary as (
    select
        service_date,
        count(distinct route_id)::integer as active_routes_count,
        sum(scheduled_trips_count)::integer as scheduled_trips_count
    from {{ ref('route_daily_trips') }}
    group by 1
),
stop_summary as (
    select
        service_date,
        sum(scheduled_departures_count)::integer as scheduled_stop_departures_count,
        count(distinct stop_id)::integer as active_stops_count
    from {{ ref('stop_daily_departures') }}
    group by 1
)
select
    coalesce(r.service_date, s.service_date) as service_date,
    coalesce(r.active_routes_count, 0)::integer as active_routes_count,
    coalesce(r.scheduled_trips_count, 0)::integer as scheduled_trips_count,
    coalesce(s.scheduled_stop_departures_count, 0)::integer as scheduled_stop_departures_count,
    coalesce(s.active_stops_count, 0)::integer as active_stops_count
from route_summary r
full outer join stop_summary s using (service_date)
order by service_date
