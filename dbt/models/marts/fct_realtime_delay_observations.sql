{{ config(materialized='incremental', unique_key='delay_observation_key', incremental_strategy='delete+insert', on_schema_change='fail') }}

select
    md5(concat_ws('|', stu.source, stu.snapshot_id, coalesce(stu.trip_id, ''), coalesce(stu.stop_id, ''), coalesce(cast(stu.stop_sequence as varchar), ''), 'ARRIVAL_OR_DEPARTURE')) as delay_observation_key,
    stu.source,
    stu.snapshot_id,
    stu.snapshot_timestamp,
    stu.collection_time,
    stu.collection_date as service_date,
    stu.collection_hour,
    stu.route_id,
    stu.trip_id,
    cast(null as varchar) as direction_id,
    stu.stop_id,
    stu.stop_sequence,
    case
        when stu.arrival_delay_seconds is not null then 'ARRIVAL'
        when stu.departure_delay_seconds is not null then 'DEPARTURE'
        else 'UNKNOWN'
    end as event_type,
    cast(null as timestamp) as scheduled_event_time,
    coalesce(nullif(stu.arrival_time, ''), nullif(stu.departure_time, '')) as observed_or_predicted_event_time,
    stu.delay_seconds,
    case
        when stu.arrival_delay_seconds is not null then 'ARRIVAL_DELAY'
        when stu.departure_delay_seconds is not null then 'DEPARTURE_DELAY'
        else 'NO_DELAY_FIELD'
    end as delay_source,
    coalesce(obs.match_status, 'UNMATCHED') as match_status,
    stu.feed_age_seconds,
    coalesce(stu.feed_age_seconds, 999999) <= {{ var("current_feed_age_seconds", 300) }} as is_current_enough,
    stu.delay_seconds is not null
        and coalesce(stu.feed_age_seconds, 999999) <= {{ var("current_feed_age_seconds", 300) }}
        and stu.delay_seconds between {{ var("minimum_delay_seconds", -7200) }} and {{ var("maximum_delay_seconds", 7200) }} as is_eligible_delay_observation,
    case
        when stu.delay_seconds is null then 'MISSING_DELAY'
        when coalesce(stu.feed_age_seconds, 999999) > {{ var("current_feed_age_seconds", 300) }} then 'STALE_OBSERVATION'
        when stu.delay_seconds < {{ var("minimum_delay_seconds", -7200) }} or stu.delay_seconds > {{ var("maximum_delay_seconds", 7200) }} then 'IMPLAUSIBLE_DELAY'
        else null
    end as ineligibility_reason,
    'reliability_v1' as calculation_version
from {{ ref('stg_history_stop_time_updates') }} stu
left join {{ ref('int_realtime_trip_observations') }} obs
    on stu.source = obs.source
    and stu.snapshot_id = obs.snapshot_id
    and stu.trip_id = obs.trip_id
