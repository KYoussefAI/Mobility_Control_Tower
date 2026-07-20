select
    sd.service_date,
    tb.route_type,
    st.stop_id,
    count(*)::integer as scheduled_departures_count
from {{ ref('stg_stop_times') }} st
join {{ ref('int_trip_base') }} tb using (trip_id)
join {{ ref('int_service_dates') }} sd using (service_id)
where coalesce(st.departure_time, '') <> ''
group by 1, 2, 3
