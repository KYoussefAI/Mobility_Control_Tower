select performance.service_date
from {{ ref('network_on_time_performance') }} performance
left join {{ ref('realtime_coverage') }} coverage using (service_date)
where coverage.service_date is null
