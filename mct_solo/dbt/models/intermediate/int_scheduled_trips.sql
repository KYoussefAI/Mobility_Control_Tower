select
    service.service_date,
    trips.trip_id,
    trips.service_id,
    trips.route_id,
    routes.route_short_name,
    routes.route_long_name,
    routes.route_type
from {{ ref('stg_trips') }} trips
join {{ ref('int_service_dates') }} service using (service_id)
join {{ ref('stg_routes') }} routes using (route_id)

