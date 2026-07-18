select
    cast(trip_id as varchar) as trip_id,
    cast(route_id as varchar) as route_id,
    cast(service_id as varchar) as service_id
from {{ silver_csv('trips') }}

