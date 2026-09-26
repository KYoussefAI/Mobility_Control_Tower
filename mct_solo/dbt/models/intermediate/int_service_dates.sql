with regular as (
    select c.service_id, cast(day.service_date as date) as service_date
    from {{ ref('stg_calendar') }} c,
    generate_series(c.start_date, c.end_date, interval 1 day) as day(service_date)
    where case extract(isodow from day.service_date)
        when 1 then c.monday
        when 2 then c.tuesday
        when 3 then c.wednesday
        when 4 then c.thursday
        when 5 then c.friday
        when 6 then c.saturday
        when 7 then c.sunday
    end = 1
),
added as (
    select service_id, service_date
    from {{ ref('stg_calendar_dates') }}
    where exception_type = 1
),
removed as (
    select service_id, service_date
    from {{ ref('stg_calendar_dates') }}
    where exception_type = 2
),
candidates as (
    select * from regular
    union
    select * from added
)
select candidates.service_id, candidates.service_date
from candidates
left join removed using (service_id, service_date)
where removed.service_id is null

