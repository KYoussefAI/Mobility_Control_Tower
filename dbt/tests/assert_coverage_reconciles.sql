select service_date, eligible_scheduled_trips, observed_matched_trips, trips_with_unknown_status
from {{ ref('realtime_coverage') }}
where eligible_scheduled_trips != observed_matched_trips + trips_with_unknown_status
   or observed_matched_trips > eligible_scheduled_trips

