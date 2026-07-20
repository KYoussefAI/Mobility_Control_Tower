select *
from {{ ref('fct_observed_headways') }}
where observed_headway_seconds <= 0
