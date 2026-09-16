{{ config(materialized='table') }}

select
    source,
    service_date,
    route_id,
    direction_id,
    reference_stop_id,
    'all' as service_period,
    observation_method,
    calculation_version,
    count(*)::integer as observed_headway_count,
    count(planned_headway_seconds)::integer as planned_headway_count,
    case
        when sum(observed_headway_seconds) > 0 then sum(observed_headway_seconds * observed_headway_seconds) / (2.0 * sum(observed_headway_seconds))
    end as actual_expected_wait_seconds,
    case
        when sum(planned_headway_seconds) > 0 then sum(planned_headway_seconds * planned_headway_seconds) / (2.0 * sum(planned_headway_seconds))
    end as scheduled_expected_wait_seconds,
    case
        when count(*) >= {{ var("minimum_ewt_headway_count", 3) }} and sum(observed_headway_seconds) > 0 and sum(planned_headway_seconds) > 0
        then
            sum(observed_headway_seconds * observed_headway_seconds) / (2.0 * sum(observed_headway_seconds))
            - sum(planned_headway_seconds * planned_headway_seconds) / (2.0 * sum(planned_headway_seconds))
    end as excess_waiting_time_seconds,
    max(coverage_percentage) as coverage_percentage,
    case
        when count(*) < {{ var("minimum_ewt_headway_count", 3) }} then 'NOT_ENOUGH_DATA'
        when sum(observed_headway_seconds) <= 0 or sum(planned_headway_seconds) <= 0 then 'INVALID_HEADWAY_TOTAL'
        else 'ELIGIBLE'
    end as eligibility_status,
    case
        when count(*) < {{ var("minimum_ewt_headway_count", 3) }} then 'INSUFFICIENT_OBSERVED_HEADWAY_COUNT'
        when sum(observed_headway_seconds) <= 0 or sum(planned_headway_seconds) <= 0 then 'NON_POSITIVE_HEADWAY_TOTAL'
        else null
    end as exclusion_reason,
    case
        when count(*) >= 10 then 'HIGH'
        when count(*) >= {{ var("minimum_ewt_headway_count", 3) }} then 'LOW_SAMPLE'
        else 'NOT_ENOUGH_DATA'
    end as confidence_status
from {{ ref('fct_observed_headways') }}
where eligible_for_reliability
group by 1, 2, 3, 4, 5, 6, 7, 8
