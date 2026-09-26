select
    cast(service_id as varchar) as service_id,
    cast(monday as integer) as monday,
    cast(tuesday as integer) as tuesday,
    cast(wednesday as integer) as wednesday,
    cast(thursday as integer) as thursday,
    cast(friday as integer) as friday,
    cast(saturday as integer) as saturday,
    cast(sunday as integer) as sunday,
    cast(start_date as date) as start_date,
    cast(end_date as date) as end_date
from read_parquet('{{ var("static_path") }}/calendar.parquet')

