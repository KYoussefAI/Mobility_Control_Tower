select
    t.trip_id,
    t.route_id,
    t.service_id,
    r.route_short_name,
    r.route_long_name,
    r.route_type
from {{ ref('stg_trips') }} t
left join {{ ref('stg_routes') }} r using (route_id)

