with route_type_totals as (
    select
        service_date,
        sum(scheduled_stop_departures_count) as scheduled_stop_departures_count
    from {{ ref('route_type_daily_summary') }}
    group by 1
)
select n.*
from {{ ref('network_daily_summary') }} n
join route_type_totals r using (service_date)
where n.scheduled_stop_departures_count <> r.scheduled_stop_departures_count
