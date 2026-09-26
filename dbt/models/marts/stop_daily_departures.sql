select
    sd.service_date,
    st.stop_id,
    s.stop_name,
    count(*)::integer as scheduled_departures_count
from {{ ref('stg_stop_times') }} st
join {{ ref('int_trip_base') }} tb using (trip_id)
join {{ ref('int_service_dates') }} sd using (service_id)
left join {{ ref('stg_stops') }} s using (stop_id)
where coalesce(st.departure_time, '') <> ''
group by 1, 2, 3
order by service_date, stop_id

