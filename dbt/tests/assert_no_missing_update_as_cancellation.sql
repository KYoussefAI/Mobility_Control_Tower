select c.*
from {{ ref('fct_explicit_trip_cancellations') }} c
left join {{ ref('int_realtime_trip_observations') }} o
  on c.source = o.source
 and c.service_date = o.service_date
 and c.trip_id = o.trip_id
 and o.is_explicitly_canceled
where o.trip_id is null
