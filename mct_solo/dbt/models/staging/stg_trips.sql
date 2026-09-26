select
    cast(trip_id as varchar) as trip_id,
    cast(route_id as varchar) as route_id,
    cast(service_id as varchar) as service_id,
    nullif(cast(trip_headsign as varchar), '') as trip_headsign,
    cast(direction_id as integer) as direction_id
from read_parquet('{{ var("static_path") }}/trips.parquet')

