with expected as (
    select service_date, count(*) as observed_trip_stops
    from {{ ref('int_trip_stop_observations') }}
    group by 1
)
select actual.service_date, actual.observed_trip_stops, expected.observed_trip_stops as expected_trip_stops
from {{ ref('network_on_time_performance') }} actual
full outer join expected using (service_date)
where actual.observed_trip_stops is distinct from expected.observed_trip_stops
