select snapshot_id, entity_id, stop_sequence, delay_seconds
from {{ ref('int_delay_observations') }}
where has_known_delay and (delay_seconds is null or abs(delay_seconds) > {{ var('max_abs_delay_seconds') }})
