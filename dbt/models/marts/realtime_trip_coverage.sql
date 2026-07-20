{{ config(materialized='table') }}

with eligible as (
    select *
    from {{ ref('int_realtime_eligible_scheduled_trips') }}
    where eligibility_status = 'ELIGIBLE'
),
observed as (
    select distinct
        source,
        service_date,
        route_id,
        trip_id,
        match_status,
        is_explicitly_canceled
    from {{ ref('int_realtime_trip_observations') }}
),
eligible_counts as (
    select
        source,
        service_date,
        route_id,
        service_period,
        count(distinct trip_id)::integer as eligible_scheduled_trip_count
    from eligible
    group by 1, 2, 3, 4
),
matched_counts as (
    select
        e.source,
        e.service_date,
        e.route_id,
        e.service_period,
        count(distinct case when o.match_status = 'EXACT' then e.trip_id end)::integer as observed_eligible_trip_count,
        count(distinct case when o.is_explicitly_canceled then e.trip_id end)::integer as explicit_cancellation_count
    from eligible e
    left join observed o
        on e.source = o.source
        and e.service_date = o.service_date
        and e.trip_id = o.trip_id
    group by 1, 2, 3, 4
),
unmatched as (
    select
        source,
        service_date,
        route_id,
        'unknown' as service_period,
        count(distinct trip_id)::integer as unmatched_realtime_trip_count,
        count(distinct case when match_status = 'AMBIGUOUS' then trip_id end)::integer as ambiguous_realtime_trip_count
    from observed
    where match_status <> 'EXACT'
    group by 1, 2, 3, 4
)
select
    ec.source,
    ec.service_date,
    ec.route_id,
    ec.service_period,
    'trip_updates' as feed_type,
    'reliability_v1' as calculation_version,
    ec.eligible_scheduled_trip_count,
    coalesce(mc.observed_eligible_trip_count, 0)::integer as observed_eligible_trip_count,
    (ec.eligible_scheduled_trip_count - coalesce(mc.observed_eligible_trip_count, 0))::integer as unobserved_eligible_trip_count,
    coalesce(u.unmatched_realtime_trip_count, 0)::integer as unmatched_realtime_trip_count,
    coalesce(u.ambiguous_realtime_trip_count, 0)::integer as ambiguous_realtime_trip_count,
    coalesce(mc.explicit_cancellation_count, 0)::integer as explicit_cancellation_count,
    case
        when ec.eligible_scheduled_trip_count = 0 then null
        else round(100.0 * coalesce(mc.observed_eligible_trip_count, 0) / ec.eligible_scheduled_trip_count, 2)
    end as coverage_percentage,
    case
        when ec.eligible_scheduled_trip_count = 0 then 'NOT_APPLICABLE'
        when coalesce(mc.observed_eligible_trip_count, 0) = 0 then 'NO_REALTIME_EVIDENCE'
        else 'OBSERVED'
    end as coverage_status,
    case
        when ec.eligible_scheduled_trip_count = 0 then 'NOT_APPLICABLE'
        when 1.0 * coalesce(mc.observed_eligible_trip_count, 0) / ec.eligible_scheduled_trip_count >= 0.8 then 'HIGH'
        when coalesce(mc.observed_eligible_trip_count, 0) > 0 then 'LOW'
        else 'NO_COVERAGE'
    end as confidence_status
from eligible_counts ec
left join matched_counts mc using (source, service_date, route_id, service_period)
left join unmatched u using (source, service_date, route_id, service_period)
