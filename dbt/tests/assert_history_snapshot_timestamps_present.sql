select *
from {{ ref('stg_history_feed_summary') }}
where snapshot_timestamp is null or trim(snapshot_timestamp) = ''
