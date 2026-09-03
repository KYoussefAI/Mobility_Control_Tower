with route_type_totals as (
    select
        service_date,
        sum(scheduled_trips_count) as scheduled_trips_count
    from {{ ref('route_type_daily_summary') }}
    group by 1
)
select n.*
from {{ ref('network_daily_summary') }} n
join route_type_totals r using (service_date)
where n.scheduled_trips_count <> r.scheduled_trips_count
