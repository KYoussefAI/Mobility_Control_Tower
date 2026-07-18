select
    r.service_date,
    count(distinct r.route_id)::integer as active_routes_count,
    sum(r.scheduled_trips_count)::integer as scheduled_trips_count,
    coalesce(sum(s.scheduled_departures_count), 0)::integer as scheduled_stop_departures_count,
    count(distinct s.stop_id)::integer as active_stops_count
from {{ ref('route_daily_trips') }} r
left join {{ ref('stop_daily_departures') }} s using (service_date)
group by 1
order by service_date

