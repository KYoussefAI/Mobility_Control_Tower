select
    snapshot_id,
    collected_at,
    collection_date,
    header_timestamp,
    feed_age_seconds,
    entity_count,
    trip_update_count,
    stop_time_update_count,
    case
        when feed_age_seconds is null then 'UNKNOWN'
        when feed_age_seconds <= {{ var('fresh_realtime_seconds') }} then 'FRESH'
        when feed_age_seconds <= {{ var('stale_realtime_seconds') }} then 'DELAYED'
        else 'STALE'
    end as freshness_status
from {{ ref('stg_feed_snapshots') }}

