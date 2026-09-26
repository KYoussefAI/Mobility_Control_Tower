select
    service_date,
    count(*) as observed_stop_updates,
    count(distinct trip_id) as observed_trips,
    count(*) filter (where is_on_time) as on_time_observations,
    count(*) filter (where not is_on_time) as outside_on_time_window_observations,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage,
    round(avg(delay_seconds), 1) as average_delay_seconds
from {{ ref('int_delay_observations') }}
where static_trip_match and has_known_delay
group by 1

