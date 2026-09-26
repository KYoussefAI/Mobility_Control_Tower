select
    service_date,
    route_id,
    route_short_name,
    route_long_name,
    departure_hour,
    scheduled_departures_count,
    round(60.0 / nullif(scheduled_departures_count, 0), 2) as planned_headway_minutes
from {{ ref('route_hourly_departures') }}
order by service_date, route_id, departure_hour

