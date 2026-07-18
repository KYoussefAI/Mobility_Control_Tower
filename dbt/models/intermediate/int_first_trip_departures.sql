with ranked as (
    select
        st.trip_id,
        st.stop_id,
        st.stop_sequence,
        st.departure_time,
        st.departure_time_seconds,
        row_number() over (partition by st.trip_id order by st.stop_sequence nulls last) as rn
    from {{ ref('stg_stop_times') }} st
)
select
    trip_id,
    stop_id,
    floor(departure_time_seconds / 3600)::integer as departure_hour
from ranked
where rn = 1 and departure_time_seconds is not null

