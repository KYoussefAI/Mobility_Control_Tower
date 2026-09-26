select
    cast(route_id as varchar) as route_id,
    nullif(cast(route_short_name as varchar), '') as route_short_name,
    nullif(cast(route_long_name as varchar), '') as route_long_name,
    cast(route_type as integer) as route_type
from read_parquet('{{ var("static_path") }}/routes.parquet')

