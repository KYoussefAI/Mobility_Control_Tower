{{ config(materialized='incremental', unique_key='evidence_key', incremental_strategy='delete+insert', on_schema_change='fail') }}

select
    source,
    service_date,
    route_id,
    direction_id,
    reference_stop_id,
    following_observation_time as event_timestamp,
    case
        when observed_headway_seconds < planned_headway_seconds * {{ var("bunching_ratio", 0.5) }} then 'BUNCHING'
        when observed_headway_seconds > planned_headway_seconds * {{ var("service_gap_ratio", 2.0) }} then 'SERVICE_GAP'
    end as event_type,
    planned_headway_seconds,
    observed_headway_seconds,
    headway_ratio,
    case
        when observed_headway_seconds < planned_headway_seconds * {{ var("bunching_ratio", 0.5) }} then {{ var("bunching_ratio", 0.5) }}
        when observed_headway_seconds > planned_headway_seconds * {{ var("service_gap_ratio", 2.0) }} then {{ var("service_gap_ratio", 2.0) }}
    end as threshold_ratio,
    observation_method,
    case
        when observed_headway_seconds > planned_headway_seconds * {{ var("service_gap_ratio", 2.0) }} then 'WARNING'
        else 'INFO'
    end as severity,
    md5(concat_ws('|', headway_key, 'HEADWAY_EVENT')) as evidence_key,
    calculation_version
from {{ ref('fct_observed_headways') }}
where eligible_for_reliability
  and (
      observed_headway_seconds < planned_headway_seconds * {{ var("bunching_ratio", 0.5) }}
      or observed_headway_seconds > planned_headway_seconds * {{ var("service_gap_ratio", 2.0) }}
  )
