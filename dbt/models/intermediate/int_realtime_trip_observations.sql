with latest_delay as (
    select
        source,
        snapshot_id,
        trip_id,
        route_id,
        delay_seconds,
        row_number() over (
            partition by source, snapshot_id, trip_id
            order by stop_sequence nulls last, stop_id
        ) as rn
    from {{ ref('stg_history_stop_time_updates') }}
),
deduped as (
    select
        tu.source,
        tu.snapshot_id,
        tu.snapshot_timestamp,
        tu.collection_time,
        tu.feed_header_timestamp,
        tu.collection_date as service_date,
        tu.route_id,
        tu.trip_id,
        cast(null as varchar) as direction_id,
        tu.schedule_relationship,
        case
            when eligible.trip_id is not null then 'EXACT'
            when tu.trip_id is null or trim(tu.trip_id) = '' then 'UNMATCHED'
            else 'UNMATCHED'
        end as match_status,
        case
            when eligible.trip_id is not null then 'SOURCE_TRIP_ID'
            else 'NO_STATIC_TRIP_MATCH'
        end as match_method,
        case
            when eligible.trip_id is not null then 1.0
            else 0.0
        end as match_confidence,
        eligible.static_run_id as matched_static_run_id,
        upper(coalesce(tu.schedule_relationship, '')) in ('CANCELED', 'CANCELLED') as is_explicitly_canceled,
        latest.delay_seconds is not null as has_usable_delay,
        latest.delay_seconds as latest_observed_delay_seconds,
        md5(concat_ws('|', tu.source, tu.snapshot_id, coalesce(tu.trip_id, ''), coalesce(tu.route_id, ''))) as observation_key,
        'reliability_v1' as calculation_version,
        row_number() over (
            partition by tu.source, tu.snapshot_id, coalesce(tu.trip_id, ''), coalesce(tu.route_id, '')
            order by tu.collection_time desc
        ) as duplicate_rank
    from {{ ref('stg_history_trip_updates') }} tu
    left join {{ ref('int_realtime_eligible_scheduled_trips') }} eligible
        on tu.source = eligible.source
        and tu.collection_date = eligible.service_date
        and tu.trip_id = eligible.trip_id
    left join latest_delay latest
        on tu.source = latest.source
        and tu.snapshot_id = latest.snapshot_id
        and tu.trip_id = latest.trip_id
        and latest.rn = 1
)
select
    source,
    snapshot_id,
    snapshot_timestamp,
    collection_time,
    feed_header_timestamp,
    service_date,
    route_id,
    trip_id,
    direction_id,
    schedule_relationship,
    match_status,
    match_method,
    match_confidence,
    matched_static_run_id,
    is_explicitly_canceled,
    has_usable_delay,
    latest_observed_delay_seconds,
    observation_key,
    calculation_version
from deduped
where duplicate_rank = 1
