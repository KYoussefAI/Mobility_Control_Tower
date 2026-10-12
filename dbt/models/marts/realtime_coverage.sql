with monitored_dates as (
    select distinct collection_date as service_date
    from {{ ref('stg_feed_snapshots') }}
),
scheduled as (
    select service_date, count(distinct trip_id) as eligible_scheduled_trips
    from {{ ref('int_scheduled_trips') }}
    where service_date in (select service_date from monitored_dates)
    group by 1
),
observed as (
    select service_date, count(distinct trip_id) as observed_matched_trips
    from {{ ref('int_trip_stop_observations') }}
    group by 1
)
select
    scheduled.service_date,
    scheduled.eligible_scheduled_trips as scheduled_trips,
    coalesce(observed.observed_matched_trips, 0) as matched_realtime_trips,
    scheduled.eligible_scheduled_trips - coalesce(observed.observed_matched_trips, 0) as unknown_trips,
    round(
        100.0 * coalesce(observed.observed_matched_trips, 0)
        / nullif(scheduled.eligible_scheduled_trips, 0),
        2
    ) as coverage_percentage
from scheduled
left join observed using (service_date)

