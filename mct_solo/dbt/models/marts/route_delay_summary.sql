select
    service_date,
    route_id,
    route_short_name,
    route_long_name,
    count(*) as observed_stop_updates,
    case
        when count(*) >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
        else 'LOW_SAMPLE'
    end as sample_size_status,
    count(distinct trip_id) as observed_trips,
    round(avg(delay_seconds), 1) as average_delay_seconds,
    round(median(delay_seconds), 1) as median_delay_seconds,
    round(quantile_cont(delay_seconds, 0.90), 1) as p90_delay_seconds,
    count(*) filter (where is_on_time) as on_time_observations,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage
from {{ ref('int_delay_observations') }}
where static_trip_match and has_known_delay
group by 1, 2, 3, 4
