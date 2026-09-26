# Data Model

## Staging models

| Model | Grain | Key relationships |
| --- | --- | --- |
| `stg_routes` | One route | `route_id` is unique and not null |
| `stg_trips` | One scheduled trip | `trip_id` is unique; `route_id` references `stg_routes` |
| `stg_stops` | One stop | `stop_id` is unique and not null |
| `stg_stop_times` | One stop sequence in a trip | `trip_id` references `stg_trips`; `stop_id` references `stg_stops` |
| `stg_calendar` | One regular service definition | `service_id` with weekday and date-window fields |
| `stg_calendar_dates` | One service-date exception | `exception_type` adds or removes service |
| `stg_realtime_updates` | One snapshot/entity/stop update | Carries trip, stop, service date, and published delay |
| `stg_feed_snapshots` | One collected snapshot | `snapshot_id` is unique and not null |

GTFS service times are stored as seconds after service-day midnight. For example, `25:05:00` is stored as `90,300`, preserving after-midnight service without changing the service date.

## Intermediate models

| Model | Grain | Responsibility |
| --- | --- | --- |
| `int_service_dates` | Service identifier and active date | Expands weekday calendars and applies added or removed exceptions |
| `int_scheduled_trips` | Scheduled trip and service date | Joins active services, trips, and routes |
| `int_delay_observations` | Deduplicated snapshot/entity/stop sequence | Matches realtime rows to static trips and stop times, then classifies delay eligibility |

`int_delay_observations` exposes `static_trip_match`, `raw_delay_present`, `has_known_delay`, and `delay_quality_status`, keeping match coverage separate from delay performance.

## Analytical marts

| Mart | Grain | Responsibility |
| --- | --- | --- |
| `route_daily_service` | Route and service date | Scheduled trip and departure volume |
| `route_delay_summary` | Route and service date | Delay distribution, on-time share, and sample status |
| `hourly_delay_summary` | Service date and clock hour | Hourly delay and on-time metrics |
| `network_on_time_performance` | Service date | Network on-time performance over eligible observations |
| `realtime_coverage` | Service date | Share of scheduled trips matched to realtime |
| `feed_freshness` | Snapshot | Publisher-feed age and freshness status |

## Metric contracts

- **On time:** delay from -60 through +300 seconds, inclusive.
- **Eligible delay:** non-null and within ±7,200 seconds.
- **Coverage denominator:** distinct scheduled trips on a date with at least one collected snapshot.
- **Coverage numerator:** distinct scheduled trips matched by exact `trip_id`.
- **Unknown trips:** denominator minus matched trips; no cancellation inference is made.
- **Reliable sample:** at least five eligible observations in a route-day or hour group.
- **Feed freshness:** `FRESH` through 90 seconds, `DELAYED` through 300 seconds, then `STALE`; a missing publisher time is `UNKNOWN`.

Analytical thresholds are passed to dbt by the Python runner. Business assertions reconcile percentages, counts, delay eligibility, coverage, and sample-size status.
