select
    '{{ var("source_id", "tisseo") }}' as source,
    sd.service_date,
    tb.route_id,
    tb.trip_id,
    cast(null as varchar) as direction_id,
    st.departure_time as scheduled_start_time,
    st.departure_time_seconds as scheduled_start_seconds,
    case
        when fd.departure_hour between 0 and 5 then 'overnight'
        when fd.departure_hour between 6 and 9 then 'am_peak'
        when fd.departure_hour between 10 and 15 then 'midday'
        when fd.departure_hour between 16 and 19 then 'pm_peak'
        else 'evening'
    end as service_period,
    '{{ var("static_run_id", "fixture_static") }}' as static_run_id,
    case
        when tb.trip_id is null or trim(tb.trip_id) = '' then 'MISSING_TRIP_ID'
        when fd.departure_hour is null then 'OUTSIDE_PERIOD'
        else 'ELIGIBLE'
    end as eligibility_status,
    case
        when tb.trip_id is null or trim(tb.trip_id) = '' then 'Trip identifier is missing.'
        when fd.departure_hour is null then 'Trip has no usable first departure time.'
        else 'Trip has active service and a usable trip identifier.'
    end as eligibility_reason,
    'reliability_v1' as calculation_version
from {{ ref('int_trip_base') }} tb
join {{ ref('int_service_dates') }} sd using (service_id)
left join {{ ref('int_first_trip_departures') }} fd using (trip_id)
left join {{ ref('stg_stop_times') }} st
    on tb.trip_id = st.trip_id
    and fd.stop_id = st.stop_id
