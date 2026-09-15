{{ config(materialized='table') }}

select
    d.source,
    d.service_date,
    coalesce(c.service_period, 'unknown') as service_period,
    d.route_id,
    d.direction_id,
    d.stop_id,
    'reliability_v1' as calculation_version,
    count(*) filter (where d.is_eligible_delay_observation)::integer as eligible_observation_count,
    count(distinct case when d.is_eligible_delay_observation then d.trip_id end)::integer as distinct_trip_count,
    count(*) filter (where d.delay_seconds is null)::integer as missing_delay_count,
    count(*) filter (where d.is_eligible_delay_observation and d.delay_seconds < {{ var("early_threshold_seconds", -60) }})::integer as early_observation_count,
    count(*) filter (where d.is_eligible_delay_observation and d.delay_seconds between {{ var("early_threshold_seconds", -60) }} and {{ var("late_threshold_seconds", 300) }})::integer as on_time_observation_count,
    count(*) filter (where d.is_eligible_delay_observation and d.delay_seconds > {{ var("late_threshold_seconds", 300) }})::integer as late_observation_count,
    count(*) filter (where d.is_eligible_delay_observation and d.delay_seconds > {{ var("severe_delay_seconds", 900) }})::integer as severe_delay_observation_count,
    round(avg(d.delay_seconds) filter (where d.is_eligible_delay_observation), 2) as average_delay_seconds,
    quantile_cont(d.delay_seconds, 0.5) filter (where d.is_eligible_delay_observation) as median_delay_seconds,
    quantile_cont(d.delay_seconds, 0.9) filter (where d.is_eligible_delay_observation) as p90_delay_seconds,
    quantile_cont(d.delay_seconds, 0.95) filter (where d.is_eligible_delay_observation) as p95_delay_seconds,
    min(d.delay_seconds) filter (where d.is_eligible_delay_observation) as minimum_delay_seconds,
    max(d.delay_seconds) filter (where d.is_eligible_delay_observation) as maximum_delay_seconds,
    case when count(*) = 0 then null else round(100.0 * count(*) filter (where d.delay_seconds is null) / count(*), 2) end as missing_delay_percentage,
    max(c.coverage_percentage) as coverage_percentage,
    case
        when count(*) filter (where d.is_eligible_delay_observation) >= 30 then 'HIGH'
        when count(*) filter (where d.is_eligible_delay_observation) > 0 then 'LOW_SAMPLE'
        else 'NOT_ENOUGH_DATA'
    end as confidence_status
from {{ ref('fct_realtime_delay_observations') }} d
left join {{ ref('realtime_trip_coverage') }} c
    on d.source = c.source
    and d.service_date = c.service_date
    and d.route_id = c.route_id
group by 1, 2, 3, 4, 5, 6, 7
