select
    service_date,
    cast(floor((departure_seconds % 86400) / 3600) as integer) as service_hour,
    count(*) as observed_stop_updates,
    case
        when count(*) >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
        else 'LOW_SAMPLE'
    end as sample_size_status,
    round(avg(delay_seconds), 1) as average_delay_seconds,
    round(median(delay_seconds), 1) as median_delay_seconds,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage
from {{ ref('int_delay_observations') }}
where static_trip_match and has_known_delay and departure_seconds is not null
group by 1, 2
