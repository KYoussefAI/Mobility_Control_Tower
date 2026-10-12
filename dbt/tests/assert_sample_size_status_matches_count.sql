select
    'route_delay_summary' as model_name,
    service_date,
    route_id as group_key,
    observed_trip_stops,
    sample_size_status
from {{ ref('route_delay_summary') }}
where sample_size_status != case
    when observed_trip_stops >= {{ var('min_sufficient_sample_size') }} then 'SUFFICIENT_SAMPLE'
    else 'LOW_SAMPLE'
end

union all

select
    'hourly_delay_summary' as model_name,
    service_date,
    cast(service_hour as varchar) as group_key,
    observed_trip_stops,
    sample_size_status
from {{ ref('hourly_delay_summary') }}
where sample_size_status != case
    when observed_trip_stops >= {{ var('min_sufficient_sample_size') }} then 'SUFFICIENT_SAMPLE'
    else 'LOW_SAMPLE'
end
