select
    r.service_date,
    r.route_type,
    case cast(r.route_type as varchar)
        when '0' then 'Tram'
        when '1' then 'Subway/Metro'
        when '2' then 'Rail'
        when '3' then 'Bus'
        when '4' then 'Ferry'
        when '5' then 'Cable tram'
        when '6' then 'Aerial lift'
        when '7' then 'Funicular'
        else 'Unknown'
    end as route_type_label,
    count(distinct r.route_id)::integer as active_routes_count,
    sum(r.scheduled_trips_count)::integer as scheduled_trips_count,
    coalesce(max(s.scheduled_stop_departures_count), 0)::integer as scheduled_stop_departures_count
from {{ ref('route_daily_trips') }} r
left join (
    select
        service_date,
        route_type,
        sum(scheduled_departures_count)::integer as scheduled_stop_departures_count
    from {{ ref('int_route_type_stop_departures') }}
    group by 1, 2
) s
    on r.service_date = s.service_date
    and r.route_type = s.route_type
group by 1, 2, 3
order by service_date, route_type
