# KPI Definitions

Mobility Control Tower publishes operational indicators, not certified agency dispatch metrics. Every realtime KPI uses observed GTFS-Realtime evidence and carries coverage or confidence context. Missing Trip Updates are unknown; they are never counted as on-time and never counted as canceled.

| KPI | Grain | Formula | Eligibility | Coverage / confidence | Limitation |
| --- | --- | --- | --- | --- | --- |
| Realtime feed coverage | source + service date + route + period + feed type | observed eligible scheduled trips / eligible scheduled trips | scheduled trips active in the source timezone and matchable by namespaced trip or route identifiers | eligible trip count, observed trip count, unmatched observations, coverage percentage, confidence | Absence from a feed is unknown service state. |
| Delay distribution | source + route + stop + direction + service date + period | median, average, p90, p95, max of usable delay seconds | Stop Time Updates with numeric arrival or departure delay | observed update count, usable delay count, distinct trip count, missing-delay percentage | Represents reported updates, not all scheduled trips. |
| On-time performance | source + route + period + calculation version | observations with delay in configured window / observations with usable delay | Default window is -60 to +300 seconds and is configurable | eligible observations, thresholds, coverage from feed coverage model | Project default thresholds are not universal transit standards. |
| Explicit cancellations | source + service date + route + trip | count of Trip Updates with explicit CANCELED/CANCELLED relationship | GTFS-Realtime TripDescriptor schedule relationship only | evidence type and first/last seen timestamps where available | Missing Trip Updates are not cancellations. |
| Headway reliability | source + route + stop or corridor + period + method | observed headways compared with scheduled headways | At least two observed headways and a planned headway baseline | sample size, evidence method, bunching/gap ratios, confidence | Trip Update-derived headways are approximations unless Vehicle Position stop passage evidence is available. |
| Excess waiting time | source + route + frequent-service period + method | sum(observed_headway^2)/(2*sum(observed_headway)) - sum(scheduled_headway^2)/(2*sum(scheduled_headway)) | Frequent-service periods with sufficient observed headways | sample size, method, exclusion reason when not eligible | Not calculated from one or two isolated observations. |
| Alert service-exposure proxy | source + alert + active period + affected entity | affected scheduled trips/stops/routes multiplied by active duration or service intensity | GTFS-Realtime Service Alerts with informed entities | affected entity counts, active duration, unmatched entities | This is not passenger impact because ridership is unavailable. |
| Network reliability summary | source + period | status matrix from freshness, coverage, OTP, p90 delay, cancellations, gaps, bunching, alerts, match rate, quality | Public marts and historical realtime views available in the current serving artifact | component values remain visible; no opaque composite score | Current implementation is a local operational prototype. |

Timestamps are stored in UTC. Service dates are derived in each source timezone. GTFS times above 23:00 remain valid service-day times. Route, stop, trip, agency, vehicle, and service-date keys are namespaced by source for multi-city use.

## Authoritative dbt Models

Python `reliability.py` is diagnostic only. Authoritative production values are
computed by dbt and exposed through DuckDB serving views.

| Model | Grain | Unique key | Calculation version | Notes |
| --- | --- | --- | --- | --- |
| `int_realtime_eligible_scheduled_trips` | source + service_date + route_id + trip_id | generated eligibility key in downstream marts | `reliability_v1` | Missing or unsupported trips are labelled with eligibility status rather than silently dropped. |
| `int_realtime_trip_observations` | source + snapshot_id + trip_id + route_id | `observation_key` | `reliability_v1` | Missing Trip Updates do not create rows; explicit cancellation uses only supported schedule relationship evidence. |
| `fct_realtime_delay_observations` | source + snapshot_id + trip_id + stop_id + stop_sequence + event_type | `delay_observation_key` | `reliability_v1` | Arrival delay takes precedence over departure; null delay remains null and zero delay remains valid evidence. |
| `realtime_trip_coverage` | source + service_date + route_id + service_period + feed_type | composite grain columns | `reliability_v1` | Coverage numerator is matched observed eligible trips, denominator is eligible scheduled trips. |
| `route_on_time_performance` | source + service_date + route_id + service_period + threshold profile | composite grain columns | `reliability_v1` | Uses configurable early and late thresholds, not a universal standard. |
| `route_delay_distribution` | source + service_date + route_id + direction_id + service_period | composite grain columns | `reliability_v1` | Every average and percentile is published with sample size and coverage. |
| `fct_explicit_trip_cancellations` | source + service_date + trip_id + cancellation evidence | `cancellation_evidence_key` | `reliability_v1` | Repeated snapshots dedupe to one cancellation fact per trip evidence key. |
| `fct_observed_headways` | source + service_date + route + direction + reference stop + method + leading/following trip | `headway_key` | `reliability_v1` | Current method is `TRIP_UPDATE_APPROXIMATION`; Vehicle Position passage evidence should use its own method value. |
| `fct_headway_reliability_events` | one event per observed headway threshold breach | `evidence_key` | `reliability_v1` | Bunching and service-gap events are mutually exclusive tests. |
| `route_excess_waiting_time` | source + service_date + route + direction + reference stop + period + method | composite grain columns | `reliability_v1` | Ineligible or tiny samples return explicit exclusion semantics instead of zero. |
| `network_reliability_summary` | source + service_date + service_period | composite grain columns | `reliability_v1` | Transparent status matrix; no opaque composite score. |
