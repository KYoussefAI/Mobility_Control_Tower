select
    cast(route_id as varchar) as route_id,
    cast(route_short_name as varchar) as route_short_name,
    cast(route_long_name as varchar) as route_long_name,
    cast(route_type as varchar) as route_type
from {{ silver_csv('routes') }}

