select
    route_id,
    route_short_name,
    route_long_name,
    route_type,
    count(distinct service_date)::integer as active_service_days,
    sum(scheduled_trips_count)::integer as total_scheduled_trips,
    round(avg(scheduled_trips_count), 2) as average_trips_per_active_day,
    max(scheduled_trips_count)::integer as max_daily_trips,
    min(service_date) as first_service_date,
    max(service_date) as last_service_date
from {{ ref('route_daily_trips') }}
group by 1, 2, 3, 4
order by total_scheduled_trips desc, route_id

