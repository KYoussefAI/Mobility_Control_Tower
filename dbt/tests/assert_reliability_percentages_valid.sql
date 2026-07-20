select *
from {{ ref('realtime_trip_coverage') }}
where coverage_percentage < 0 or coverage_percentage > 100

union all

select *
from {{ ref('realtime_trip_coverage') }}
where false
