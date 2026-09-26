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
        when feed_age_seconds <= 90 then 'FRESH'
        when feed_age_seconds <= 300 then 'DELAYED'
        else 'STALE'
    end as freshness_status
from {{ ref('stg_feed_snapshots') }}

