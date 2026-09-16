select evidence_key, count(distinct event_type) as event_types
from {{ ref('fct_headway_reliability_events') }}
group by 1
having count(distinct event_type) > 1
