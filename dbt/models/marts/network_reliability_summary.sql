{{ config(materialized='table') }}

with coverage as (
    select
        source,
        service_date,
        service_period,
        sum(eligible_scheduled_trip_count)::integer as eligible_scheduled_trip_count,
        sum(observed_eligible_trip_count)::integer as observed_eligible_trip_count,
        sum(unmatched_realtime_trip_count)::integer as unmatched_realtime_trip_count,
        case
            when sum(eligible_scheduled_trip_count) = 0 then null
            else round(100.0 * sum(observed_eligible_trip_count) / sum(eligible_scheduled_trip_count), 2)
        end as realtime_coverage_percentage
    from {{ ref('realtime_trip_coverage') }}
    group by 1, 2, 3
),
events as (
    select
        source,
        service_date,
        count(*) filter (where event_type = 'SERVICE_GAP')::integer as service_gap_count,
        count(*) filter (where event_type = 'BUNCHING')::integer as bunching_count
    from {{ ref('fct_headway_reliability_events') }}
    group by 1, 2
),
freshness as (
    select
        source,
        collection_date as service_date,
        case
            when max(feed_age_seconds) <= {{ var("current_feed_age_seconds", 300) }} then 'FRESH'
            when max(feed_age_seconds) is null then 'UNKNOWN'
            else 'STALE'
        end as feed_freshness_status,
        max(collection_time) as data_as_of
    from {{ ref('stg_history_feed_summary') }}
    group by 1, 2
)
select
    c.source,
    c.service_date,
    c.service_period,
    'reliability_v1' as calculation_version,
    c.eligible_scheduled_trip_count,
    c.realtime_coverage_percentage,
    otp.on_time_percentage,
    nd.median_delay_seconds,
    nd.p90_delay_seconds,
    coalesce(cancel.explicit_cancellation_count, 0)::integer as explicit_cancellation_count,
    cancel.explicit_cancellation_percentage,
    coalesce(events.service_gap_count, 0)::integer as service_gap_count,
    coalesce(events.bunching_count, 0)::integer as bunching_count,
    0::integer as active_alert_count,
    case
        when c.observed_eligible_trip_count + c.unmatched_realtime_trip_count = 0 then null
        else round(100.0 * c.unmatched_realtime_trip_count / (c.observed_eligible_trip_count + c.unmatched_realtime_trip_count), 2)
    end as unmatched_realtime_percentage,
    coalesce(freshness.feed_freshness_status, 'UNKNOWN') as feed_freshness_status,
    'UNKNOWN' as quality_status,
    case
        when c.realtime_coverage_percentage is null then 'NOT_APPLICABLE'
        when c.realtime_coverage_percentage >= 80 then 'HIGH'
        when c.realtime_coverage_percentage > 0 then 'LOW'
        else 'NO_COVERAGE'
    end as confidence_status,
    freshness.data_as_of
from coverage c
left join {{ ref('network_on_time_performance') }} otp
    on c.source = otp.source
    and c.service_date = otp.service_date
    and c.service_period = otp.service_period
left join {{ ref('network_delay_distribution') }} nd
    on c.source = nd.source
    and c.service_date = nd.service_date
    and c.service_period = nd.service_period
left join {{ ref('network_cancellation_summary') }} cancel
    on c.source = cancel.source
    and c.service_date = cancel.service_date
    and c.service_period = cancel.service_period
left join events
    on c.source = events.source
    and c.service_date = events.service_date
left join freshness
    on c.source = freshness.source
    and c.service_date = freshness.service_date
