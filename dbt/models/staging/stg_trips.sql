select
    nullif(trim(cast(trip_id as varchar)), '') as trip_id,
    nullif(trim(cast(route_id as varchar)), '') as route_id,
    nullif(trim(cast(service_id as varchar)), '') as service_id,
    nullif(cast(trip_headsign as varchar), '') as trip_headsign,
    cast(direction_id as integer) as direction_id
from read_parquet('{{ var("static_path") }}/trips.parquet')

