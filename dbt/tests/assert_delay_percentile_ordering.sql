select *
from {{ ref('route_delay_distribution') }}
where minimum_delay_seconds > median_delay_seconds
   or median_delay_seconds > p90_delay_seconds
   or p90_delay_seconds > p95_delay_seconds
   or p95_delay_seconds > maximum_delay_seconds
