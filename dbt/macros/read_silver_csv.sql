{% macro silver_csv(table_name) -%}
read_csv_auto('{{ var("silver_run") }}/{{ table_name }}.csv', header=true)
{%- endmacro %}
