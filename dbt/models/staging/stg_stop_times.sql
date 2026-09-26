select
    nullif(trim(cast(trip_id as varchar)), '') as trip_id,
    nullif(trim(cast(stop_id as varchar)), '') as stop_id,
    cast(stop_sequence as integer) as stop_sequence,
    cast(arrival_seconds as integer) as arrival_seconds,
    cast(departure_seconds as integer) as departure_seconds
from read_parquet('{{ var("static_path") }}/stop_times.parquet')

