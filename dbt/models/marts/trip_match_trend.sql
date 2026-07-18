select
    collection_date,
    collection_hour,
    count(*)::integer as updates_collected,
    count(distinct trip_id)::integer as distinct_trips_observed,
    count(distinct route_id)::integer as distinct_routes_observed,
    count(distinct stop_id)::integer as distinct_stops_observed,
    count(distinct snapshot_timestamp)::integer as snapshots_observed
from {{ ref('stg_history_stop_time_updates') }}
group by 1, 2
order by collection_date, collection_hour

