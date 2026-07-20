{{ config(materialized='table') }}

select
    c.source,
    c.service_date,
    c.route_id,
    c.service_period,
    c.calculation_version,
    c.eligible_scheduled_trip_count,
    c.explicit_cancellation_count,
    case
        when c.eligible_scheduled_trip_count = 0 then null
        else round(100.0 * c.explicit_cancellation_count / c.eligible_scheduled_trip_count, 2)
    end as explicit_cancellation_percentage
from {{ ref('realtime_trip_coverage') }} c
