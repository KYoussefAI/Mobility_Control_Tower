select service_date, scheduled_trips, matched_realtime_trips, unknown_trips
from {{ ref('realtime_coverage') }}
where scheduled_trips != matched_realtime_trips + unknown_trips
   or matched_realtime_trips > scheduled_trips

