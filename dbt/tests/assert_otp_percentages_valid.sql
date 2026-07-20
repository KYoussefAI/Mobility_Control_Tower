select source, service_date, service_period, calculation_version, on_time_percentage
from {{ ref('route_on_time_performance') }}
where on_time_percentage < 0 or on_time_percentage > 100

union all

select source, service_date, service_period, calculation_version, on_time_percentage
from {{ ref('network_on_time_performance') }}
where on_time_percentage < 0 or on_time_percentage > 100
