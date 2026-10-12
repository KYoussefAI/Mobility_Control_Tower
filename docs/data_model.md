# Data Model

The dbt project contains 19 models: 8 staging models, 4 intermediate models, and 7 analytical marts.

## Staging models

| Model | Grain | Key relationships |
| --- | --- | --- |
| `stg_routes` | One route | `route_id` is unique and not null |
| `stg_trips` | One scheduled trip | `trip_id` is unique; `route_id` references `stg_routes` |
| `stg_stops` | One stop | `stop_id` is unique and not null |
| `stg_stop_times` | One stop sequence in a trip | `trip_id` references `stg_trips`; `stop_id` references `stg_stops` |
| `stg_calendar` | One regular service definition | `service_id` carries weekday and date-window fields |
| `stg_calendar_dates` | One service-date exception | `exception_type` adds or removes service |
| `stg_realtime_updates` | One received snapshot/entity/stop update | Carries trip, route, stop, service date, timestamps, and published delay |
| `stg_feed_snapshots` | One collected snapshot | `snapshot_id` is unique and not null |

GTFS service times are stored as seconds after service-day midnight. For example, `25:05:00` becomes `90,300`, preserving after-midnight service without changing the service date.

## Intermediate models

| Model | Grain | Responsibility |
| --- | --- | --- |
| `int_service_dates` | Service identifier and active date | Expands weekday calendars and applies added or removed exceptions |
| `int_scheduled_trips` | Scheduled trip and service date | Joins active services, trips, and routes |
| `int_delay_observations` | Snapshot, entity, and stop sequence | Collapses exact analytical duplicates, marks conflicting source variants, and classifies delay quality |
| `int_trip_stop_observations` | Service date, trip, and stop sequence | Selects the latest valid publication for a trip-stop scheduled on that same date |

### Source-key classification

`int_delay_observations` groups the key `(snapshot_id, entity_id, stop_sequence)`. Identical copies at that key may collapse. If variants disagree on analytical fields such as the trip-stop identity or delay, the grouped row is marked `AMBIGUOUS_SOURCE` rather than resolved by an arbitrary choice.

Delay quality is classified independently:

- `VALID`: delay is present and within ±7,200 seconds;
- `MISSING`: neither an arrival nor departure delay is available;
- `OUT_OF_RANGE`: delay exceeds the configured sanity bound; or
- `AMBIGUOUS_SOURCE`: conflicting variants exist at the source key.

All categories remain traceable. Only unambiguous, valid delays can enter the canonical KPI model.

### Canonical trip-stop observations

`int_trip_stop_observations` joins realtime records to `int_scheduled_trips` on both service date and trip identifier. It verifies the published route when present and validates the stop sequence and stop identifier against the scheduled stop-time record when present. It then chooses the latest `update_timestamp`, falling back to collection time, for each `(service_date, trip_id, stop_sequence)`.

This is the canonical KPI grain. It removes repeated-poll weighting while preserving one latest valid published state for every matched trip-stop. It is a GTFS-Realtime publication, not a verified physical arrival record.

Both realtime intermediate models are materialized as DuckDB tables so downstream marts reuse the expensive source scan and canonicalization work.

## Analytical marts

| Mart | Grain | Responsibility |
| --- | --- | --- |
| `route_daily_service` | Route and service date | Scheduled trip and departure volume |
| `route_delay_summary` | Route and service date | Canonical delay distribution, on-time share, and sample status |
| `hourly_delay_summary` | Service date and clock hour | Canonical hourly delay and on-time metrics |
| `network_on_time_performance` | Service date | Network performance over canonical matched trip-stops |
| `realtime_coverage` | Service date | Share of eligible scheduled trips with a canonical realtime match |
| `feed_freshness` | Snapshot | Publisher-feed age and freshness status |
| `data_coverage_summary` | One rebuild | Realtime history, static validity, canonical sample, source exclusions, and rebuild time |

## Metric contracts

| Metric or status | Contract |
| --- | --- |
| On-time | Latest canonical published delay between -60 and +300 seconds, inclusive |
| Median delay | Median delay over canonical matched trip-stop records |
| P90 delay | Value at or below which 90% of canonical matched delays fall |
| Coverage denominator | Distinct scheduled trips on a collected, schedule-compatible service date |
| Coverage numerator | Distinct eligible scheduled trips with at least one valid canonical realtime match |
| Coverage | Numerator divided by denominator |
| Unknown | Eligible scheduled trip without a valid realtime match; no service outcome is inferred |
| Feed freshness | Age of the publisher timestamp at snapshot collection |
| Sample size | Number of canonical matched trip-stop records behind a statistic |
| Sufficient sample | At least 30 canonical trip-stop records in a route-day or hour group; otherwise `LOW_SAMPLE` |

Freshness status is `FRESH` through 90 seconds, `DELAYED` above 90 through 300 seconds, and `STALE` above 300 seconds. If the publisher timestamp is unavailable, freshness is `UNKNOWN`.

Median and P90 are the primary delay distribution measures; average delay is retained as a secondary diagnostic. Analytical thresholds are passed to dbt by the Python runner. Business assertions reconcile canonical counts, percentages, eligibility, schedule-compatible dates, coverage, and sample-size status.
