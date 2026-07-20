with route_totals as (
    select
        service_date,
        sum(scheduled_trips_count) as scheduled_trips_count,
        count(distinct route_id) as active_routes_count
    from {{ ref('route_daily_trips') }}
    group by 1
)
select n.*
from {{ ref('network_daily_summary') }} n
join route_totals r using (service_date)
where n.scheduled_trips_count <> r.scheduled_trips_count
   or n.active_routes_count <> r.active_routes_count
