{{ config(materialized='table') }}

with normalized as (
    select
        *,
        coalesce(
            service_date,
            cast(timezone('Europe/Paris', collected_at) as date)
        ) as normalized_service_date
    from {{ ref('stg_realtime_updates') }}
),

analytically_distinct as (
    select
        snapshot_id,
        min(collected_at) as collected_at,
        normalized_service_date as service_date,
        entity_id,
        trip_id,
        route_id,
        stop_id,
        stop_sequence,
        observed_delay,
        schedule_relationship,
        update_timestamp
    from normalized
    group by
        snapshot_id,
        normalized_service_date,
        entity_id,
        trip_id,
        route_id,
        stop_id,
        stop_sequence,
        observed_delay,
        schedule_relationship,
        update_timestamp
),

source_keys as (
    select
        snapshot_id,
        entity_id,
        stop_sequence,
        count(*) as payload_variant_count,
        case when count(*) = 1 then min(collected_at) end as collected_at,
        case when count(*) = 1 then min(service_date) end as service_date,
        case when count(*) = 1 then min(trip_id) end as trip_id,
        case when count(*) = 1 then min(route_id) end as route_id,
        case when count(*) = 1 then min(stop_id) end as stop_id,
        case when count(*) = 1 then min(observed_delay) end as observed_delay,
        case when count(*) = 1 then min(schedule_relationship) end as schedule_relationship,
        case when count(*) = 1 then min(update_timestamp) end as update_timestamp
    from analytically_distinct
    group by snapshot_id, entity_id, stop_sequence
)

select
    updates.snapshot_id,
    updates.collected_at,
    updates.update_timestamp,
    updates.service_date,
    updates.entity_id,
    updates.trip_id,
    updates.route_id,
    updates.stop_id,
    updates.stop_sequence,
    updates.observed_delay as delay_seconds,
    updates.schedule_relationship,
    updates.payload_variant_count,
    case
        when updates.payload_variant_count = 1 then 'UNAMBIGUOUS'
        else 'AMBIGUOUS'
    end as source_key_status,
    updates.payload_variant_count = 1
        and updates.observed_delay is not null as raw_delay_present,
    updates.payload_variant_count = 1
        and updates.observed_delay is not null
        and abs(updates.observed_delay) <= {{ var('max_abs_delay_seconds') }} as has_known_delay,
    case
        when updates.payload_variant_count > 1 then 'AMBIGUOUS_SOURCE'
        when updates.observed_delay is null then 'MISSING'
        when abs(updates.observed_delay) > {{ var('max_abs_delay_seconds') }} then 'OUT_OF_RANGE'
        else 'VALID'
    end as delay_quality_status,
    updates.payload_variant_count = 1
        and updates.observed_delay between {{ var('on_time_early_seconds') }}
        and {{ var('on_time_late_seconds') }} as is_on_time
from source_keys updates
