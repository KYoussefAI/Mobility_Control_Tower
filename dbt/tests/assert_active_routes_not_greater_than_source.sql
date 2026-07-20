select n.*
from {{ ref('network_daily_summary') }} n
cross join (
    select count(distinct route_id) as source_routes_count
    from {{ ref('stg_routes') }}
) s
where n.active_routes_count > s.source_routes_count
