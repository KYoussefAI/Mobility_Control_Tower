{% macro silver_csv(table_name) -%}
read_csv_auto('{{ var("silver_run") }}/{{ table_name }}.csv', header=true)
{%- endmacro %}

{% macro history_parquet(file_name) -%}
read_parquet('{{ var("history_run") }}/date=*/hour=*/snapshot_timestamp=*/{{ file_name }}', hive_partitioning=true)
{%- endmacro %}

