select
    service_date,
    route_id,
    route_short_name,
    route_long_name,
    scheduled_trips_count,
    row_number() over (order by scheduled_trips_count desc, service_date, route_id)::integer as rank
from {{ ref('route_daily_trips') }}
qualify rank <= 50

