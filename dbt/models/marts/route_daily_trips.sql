select
    sd.service_date,
    tb.route_id,
    tb.route_short_name,
    tb.route_long_name,
    tb.route_type,
    count(*)::integer as scheduled_trips_count
from {{ ref('int_service_dates') }} sd
join {{ ref('int_trip_base') }} tb using (service_id)
group by 1, 2, 3, 4, 5
order by service_date, route_id

