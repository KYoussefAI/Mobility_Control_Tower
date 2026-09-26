select
    'route_delay_summary' as model_name,
    service_date,
    route_id as group_key,
    observed_stop_updates,
    sample_size_status
from {{ ref('route_delay_summary') }}
where sample_size_status != case
    when observed_stop_updates >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
    else 'LOW_SAMPLE'
end

union all

select
    'hourly_delay_summary' as model_name,
    service_date,
    cast(service_hour as varchar) as group_key,
    observed_stop_updates,
    sample_size_status
from {{ ref('hourly_delay_summary') }}
where sample_size_status != case
    when observed_stop_updates >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
    else 'LOW_SAMPLE'
end
