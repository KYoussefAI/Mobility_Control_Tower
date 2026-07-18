select
    collection_date,
    collection_hour,
    count(distinct snapshot_timestamp)::integer as snapshots_collected,
    round(avg(feed_age_seconds), 2) as average_feed_age_seconds,
    max(feed_age_seconds) as maximum_feed_age_seconds,
    min(feed_age_seconds) as minimum_feed_age_seconds,
    sum(parsed_entity_count)::integer as parsed_entities,
    sum(skipped_entity_count)::integer as skipped_entities
from {{ ref('stg_history_feed_summary') }}
group by 1, 2
order by collection_date, collection_hour

