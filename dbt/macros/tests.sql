{% test non_negative(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} < 0
{% endtest %}

{% test unique_combination(model, combination_of_columns) %}
select {{ combination_of_columns | join(', ') }}, count(*) as row_count
from {{ model }}
group by {{ combination_of_columns | join(', ') }}
having count(*) > 1
{% endtest %}

{% test valid_departure_hour(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} < 0 or {{ column_name }} > 47
{% endtest %}
