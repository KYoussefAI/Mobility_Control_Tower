select *
from {{ ref('route_excess_waiting_time') }}
where eligibility_status <> 'ELIGIBLE'
  and excess_waiting_time_seconds is not null
