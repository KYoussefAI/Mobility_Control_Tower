{{ config(materialized='table') }}

select
    source,
    service_date,
    service_period,
    'default' as threshold_profile,
    calculation_version,
    eligible_observation_count as eligible_delay_observation_count,
    on_time_observation_count,
    early_observation_count,
    late_observation_count,
    case
        when eligible_observation_count = 0 then null
        else round(100.0 * on_time_observation_count / eligible_observation_count, 2)
    end as on_time_percentage,
    {{ var("early_threshold_seconds", -60) }}::integer as early_threshold_seconds,
    {{ var("late_threshold_seconds", 300) }}::integer as late_threshold_seconds,
    coverage_percentage,
    confidence_status
from {{ ref('network_delay_distribution') }}
