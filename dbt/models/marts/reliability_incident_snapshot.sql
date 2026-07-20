{{ config(materialized='table') }}

select
    source,
    'route' as entity_type,
    route_id as entity_id,
    cast(service_date || ' 00:00:00' as timestamp) as period_start,
    cast(service_date || ' 23:59:59' as timestamp) as period_end,
    'realtime_coverage_percentage' as metric_name,
    coverage_percentage as metric_value,
    'default' as threshold_profile,
    coverage_percentage as coverage,
    confidence_status as confidence,
    cast(null as timestamp) as data_as_of,
    calculation_version
from {{ ref('realtime_trip_coverage') }}

union all

select
    source,
    'route' as entity_type,
    route_id as entity_id,
    cast(service_date || ' 00:00:00' as timestamp) as period_start,
    cast(service_date || ' 23:59:59' as timestamp) as period_end,
    'p90_delay_seconds' as metric_name,
    p90_delay_seconds as metric_value,
    'default' as threshold_profile,
    coverage_percentage as coverage,
    confidence_status as confidence,
    cast(null as timestamp) as data_as_of,
    calculation_version
from {{ ref('route_delay_distribution') }}
