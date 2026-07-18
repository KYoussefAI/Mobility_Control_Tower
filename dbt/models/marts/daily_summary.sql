select
    collection_date,
    count(*)::integer as updates_collected,
    round(avg(delay_seconds), 2) as average_delay_seconds,
    max(delay_seconds) as maximum_observed_delay_seconds,
    min(delay_seconds) as minimum_observed_delay_seconds,
    round(quantile_cont(delay_seconds, 0.95), 2) as p95_delay_seconds,
    count(distinct snapshot_timestamp)::integer as snapshots_observed,
    count(distinct route_id)::integer as distinct_routes_observed,
    count(distinct stop_id)::integer as distinct_stops_observed
from {{ ref('stg_history_stop_time_updates') }}
group by 1
order by collection_date

