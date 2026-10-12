select
    service_date,
    count(*) as observed_trip_stops,
    count(distinct trip_id) as observed_trips,
    count(*) filter (where is_on_time) as on_time_trip_stops,
    count(*) filter (where not is_on_time) as outside_on_time_window,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage,
    round(median(delay_seconds), 1) as median_delay_seconds,
    round(quantile_cont(delay_seconds, 0.90), 1) as p90_delay_seconds,
    round(avg(delay_seconds), 1) as average_delay_seconds,
    count(*) as sample_size,
    case
        when count(*) >= {{ var('min_sufficient_sample_size') }} then 'SUFFICIENT_SAMPLE'
        else 'LOW_SAMPLE'
    end as sample_size_status
from {{ ref('int_trip_stop_observations') }}
group by 1

