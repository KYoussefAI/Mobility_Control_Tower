select service_date, observed_stop_updates, on_time_observations, outside_on_time_window_observations
from {{ ref('network_on_time_performance') }}
where observed_stop_updates != on_time_observations + outside_on_time_window_observations

