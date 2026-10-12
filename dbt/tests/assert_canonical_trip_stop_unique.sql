select service_date, trip_id, stop_sequence, count(*) as row_count
from {{ ref('int_trip_stop_observations') }}
group by 1, 2, 3
having count(*) > 1
