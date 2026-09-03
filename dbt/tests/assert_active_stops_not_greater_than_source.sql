select n.*
from {{ ref('network_daily_summary') }} n
cross join (
    select count(distinct stop_id) as source_stops_count
    from {{ ref('stg_stops') }}
) s
where n.active_stops_count > s.source_stops_count
