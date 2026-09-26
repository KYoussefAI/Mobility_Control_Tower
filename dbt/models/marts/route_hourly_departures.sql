select
    sd.service_date,
    tb.route_id,
    tb.route_short_name,
    tb.route_long_name,
    fd.departure_hour,
    count(*)::integer as scheduled_departures_count
from {{ ref('int_first_trip_departures') }} fd
join {{ ref('int_trip_base') }} tb using (trip_id)
join {{ ref('int_service_dates') }} sd using (service_id)
group by 1, 2, 3, 4, 5
order by service_date, route_id, departure_hour

