select
    cast(trip_id as varchar) as trip_id,
    cast(stop_id as varchar) as stop_id,
    cast(stop_sequence as integer) as stop_sequence,
    cast(departure_time as varchar) as departure_time,
    try_cast(departure_time_seconds as integer) as departure_time_seconds
from {{ silver_csv('stop_times') }}

