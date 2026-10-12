select
    service_date,
    cast(floor((departure_seconds % 86400) / 3600) as integer) as service_hour,
    count(*) as observed_trip_stops,
    count(distinct trip_id) as observed_trips,
    case
        when count(*) >= {{ var('min_sufficient_sample_size') }} then 'SUFFICIENT_SAMPLE'
        else 'LOW_SAMPLE'
    end as sample_size_status,
    round(median(delay_seconds), 1) as median_delay_seconds,
    round(quantile_cont(delay_seconds, 0.90), 1) as p90_delay_seconds,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage
from {{ ref('int_trip_stop_observations') }}
where departure_seconds is not null
group by 1, 2
