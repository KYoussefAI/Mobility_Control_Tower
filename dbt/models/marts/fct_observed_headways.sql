{{ config(materialized='incremental', unique_key='headway_key', incremental_strategy='delete+insert', on_schema_change='fail') }}

with first_stop_observations as (
    select
        d.source,
        d.service_date,
        d.route_id,
        d.direction_id,
        d.stop_id as reference_stop_id,
        d.trip_id,
        min(d.collection_time) as observation_time
    from {{ ref('fct_realtime_delay_observations') }} d
    where d.is_eligible_delay_observation
    group by 1, 2, 3, 4, 5, 6
),
ordered as (
    select
        *,
        lag(trip_id) over (
            partition by source, service_date, route_id, direction_id, reference_stop_id
            order by observation_time, trip_id
        ) as leading_trip_id,
        lag(observation_time) over (
            partition by source, service_date, route_id, direction_id, reference_stop_id
            order by observation_time, trip_id
        ) as leading_observation_time
    from first_stop_observations
),
planned as (
    select
        source,
        service_date,
        route_id,
        avg(planned_headway_minutes * 60.0) as planned_headway_seconds
    from (
        select
            '{{ var("source_id", "tisseo") }}' as source,
            service_date,
            route_id,
            planned_headway_minutes
        from {{ ref('route_hourly_headway') }}
        where planned_headway_minutes is not null
    )
    group by 1, 2, 3
)
select
    md5(concat_ws('|', o.source, o.service_date, o.route_id, coalesce(o.direction_id, ''), o.reference_stop_id, o.leading_trip_id, o.trip_id, 'TRIP_UPDATE_APPROXIMATION')) as headway_key,
    o.source,
    o.service_date,
    o.route_id,
    o.direction_id,
    o.reference_stop_id,
    'TRIP_UPDATE_APPROXIMATION' as observation_method,
    o.leading_trip_id,
    o.trip_id as following_trip_id,
    o.leading_observation_time,
    o.observation_time as following_observation_time,
    date_diff('second', o.leading_observation_time, o.observation_time)::integer as observed_headway_seconds,
    p.planned_headway_seconds,
    date_diff('second', o.leading_observation_time, o.observation_time) - p.planned_headway_seconds as headway_deviation_seconds,
    date_diff('second', o.leading_observation_time, o.observation_time) / nullif(p.planned_headway_seconds, 0) as headway_ratio,
    p.planned_headway_seconds is not null
        and date_diff('second', o.leading_observation_time, o.observation_time) > 0 as eligible_for_reliability,
    case
        when o.leading_trip_id is null then 'INSUFFICIENT_SAMPLE'
        when p.planned_headway_seconds is null then 'NO_PLANNED_HEADWAY'
        else null
    end as ineligibility_reason,
    cast(null as double) as coverage_percentage,
    'reliability_v1' as calculation_version
from ordered o
left join planned p
    on o.source = p.source
    and o.service_date = p.service_date
    and o.route_id = p.route_id
where o.leading_trip_id is not null
