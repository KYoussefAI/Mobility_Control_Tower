select
    cast(service_id as varchar) as service_id,
    cast(date as date) as service_date,
    cast(exception_type as integer) as exception_type
from read_parquet('{{ var("static_path") }}/calendar_dates.parquet')

