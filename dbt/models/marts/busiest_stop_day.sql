select
    service_date,
    stop_id,
    stop_name,
    scheduled_departures_count,
    row_number() over (order by scheduled_departures_count desc, service_date, stop_id)::integer as rank
from {{ ref('stop_daily_departures') }}
qualify rank <= 50

