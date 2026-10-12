select service_date, observed_trip_stops, on_time_trip_stops, outside_on_time_window
from {{ ref('network_on_time_performance') }}
where observed_trip_stops != on_time_trip_stops + outside_on_time_window

