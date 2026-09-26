with regular_service as (
    select
        cast(service_id as varchar) as service_id,
        service_date::date as service_date
    from {{ ref('stg_calendar') }},
    generate_series(
        strptime(cast(start_date as varchar), '%Y%m%d')::date,
        strptime(cast(end_date as varchar), '%Y%m%d')::date,
        interval 1 day
    ) as generated(service_date)
    where
        (strftime(service_date, '%w') = '1' and cast(monday as varchar) = '1')
        or (strftime(service_date, '%w') = '2' and cast(tuesday as varchar) = '1')
        or (strftime(service_date, '%w') = '3' and cast(wednesday as varchar) = '1')
        or (strftime(service_date, '%w') = '4' and cast(thursday as varchar) = '1')
        or (strftime(service_date, '%w') = '5' and cast(friday as varchar) = '1')
        or (strftime(service_date, '%w') = '6' and cast(saturday as varchar) = '1')
        or (strftime(service_date, '%w') = '0' and cast(sunday as varchar) = '1')
),
added_service as (
    select
        cast(service_id as varchar) as service_id,
        strptime(cast(date as varchar), '%Y%m%d')::date as service_date
    from {{ ref('stg_calendar_dates') }}
    where cast(exception_type as varchar) = '1'
),
removed_service as (
    select
        cast(service_id as varchar) as service_id,
        strptime(cast(date as varchar), '%Y%m%d')::date as service_date
    from {{ ref('stg_calendar_dates') }}
    where cast(exception_type as varchar) = '2'
)
select distinct
    service_id,
    cast(service_date as varchar) as service_date
from (
    select * from regular_service
    union
    select * from added_service
) service
anti join removed_service using (service_id, service_date)

