with feed as (
    select
        min(collection_date) as realtime_start_date,
        max(collection_date) as realtime_end_date,
        count(distinct collection_date) as realtime_history_days,
        count(*) as realtime_snapshots
    from {{ ref('feed_freshness') }}
),
schedule as (
    select
        min(service_date) as schedule_start_date,
        max(service_date) as schedule_end_date
    from {{ ref('int_service_dates') }}
),
matchable as (
    select count(*) as schedule_matchable_days
    from {{ ref('realtime_coverage') }}
),
canonical as (
    select count(*) as canonical_trip_stops
    from {{ ref('int_trip_stop_observations') }}
),
quality as (
    select
        count(*) filter (where source_key_status = 'AMBIGUOUS') as ambiguous_source_keys,
        count(*) filter (where delay_quality_status = 'OUT_OF_RANGE') as out_of_range_source_keys,
        count(*) filter (where delay_quality_status = 'MISSING') as missing_delay_source_keys
    from {{ ref('int_delay_observations') }}
)
select
    feed.*,
    schedule.*,
    matchable.*,
    canonical.*,
    quality.*,
    current_timestamp as rebuilt_at
from feed
cross join schedule
cross join matchable
cross join canonical
cross join quality
