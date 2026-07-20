with stop_totals as (
    select
        service_date,
        sum(scheduled_departures_count) as scheduled_stop_departures_count,
        count(distinct stop_id) as active_stops_count
    from {{ ref('stop_daily_departures') }}
    group by 1
)
select n.*
from {{ ref('network_daily_summary') }} n
join stop_totals s using (service_date)
where n.scheduled_stop_departures_count <> s.scheduled_stop_departures_count
   or n.active_stops_count <> s.active_stops_count
