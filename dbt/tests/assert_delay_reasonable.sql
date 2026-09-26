select *
from {{ ref('stg_history_stop_time_updates') }}
where delay_seconds < -7200 or delay_seconds > 7200

