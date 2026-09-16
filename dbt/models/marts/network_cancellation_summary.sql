{{ config(materialized='table') }}

select
    source,
    service_date,
    service_period,
    calculation_version,
    sum(eligible_scheduled_trip_count)::integer as eligible_scheduled_trip_count,
    sum(explicit_cancellation_count)::integer as explicit_cancellation_count,
    case
        when sum(eligible_scheduled_trip_count) = 0 then null
        else round(100.0 * sum(explicit_cancellation_count) / sum(eligible_scheduled_trip_count), 2)
    end as explicit_cancellation_percentage
from {{ ref('realtime_trip_coverage') }}
group by 1, 2, 3, 4
