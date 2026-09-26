select 'route_delay_summary' as model_name, on_time_percentage as invalid_percentage
from {{ ref('route_delay_summary') }}
where on_time_percentage not between 0 and 100

union all

select 'hourly_delay_summary', on_time_percentage
from {{ ref('hourly_delay_summary') }}
where on_time_percentage not between 0 and 100

union all

select 'network_on_time_performance', on_time_percentage
from {{ ref('network_on_time_performance') }}
where on_time_percentage not between 0 and 100

union all

select 'realtime_coverage', coverage_percentage
from {{ ref('realtime_coverage') }}
where coverage_percentage not between 0 and 100

