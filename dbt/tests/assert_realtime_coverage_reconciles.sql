select *
from {{ ref('realtime_trip_coverage') }}
where observed_eligible_trip_count > eligible_scheduled_trip_count
   or explicit_cancellation_count > eligible_scheduled_trip_count
   or unobserved_eligible_trip_count <> eligible_scheduled_trip_count - observed_eligible_trip_count
