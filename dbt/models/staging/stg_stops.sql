select
    nullif(trim(cast(stop_id as varchar)), '') as stop_id,
    nullif(trim(cast(stop_name as varchar)), '') as stop_name,
    cast(stop_lat as double) as stop_lat,
    cast(stop_lon as double) as stop_lon
from read_parquet('{{ var("static_path") }}/stops.parquet')
