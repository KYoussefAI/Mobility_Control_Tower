# KPI Dictionary

Production KPI authority is dbt. Python snapshot KPIs are diagnostic unless a dbt mart explicitly consumes their persisted source data. Null/unknown observations are not silently treated as on-time or cancelled.

| KPI | Meaning and grain | Calculation and source fields | Exclusions, missing data, limitations |
|---|---|---|---|
| Scheduled trips | Planned service volume per route and service date | Distinct GTFS `trip_id` after `calendar`/`calendar_dates` service expansion | Requires valid service calendar; GTFS times after 24:00 remain on the service day |
| Scheduled stop departures | Planned departures per stop/route/date/hour | Count of `stop_times` joined to active trips; departure seconds preserve after-midnight service time | Missing stop times are absent, not imputed |
| Planned headway | Scheduled spacing per route/date/hour | Difference between ordered first-trip departures | Only groups with enough departures; not observed reliability |
| Realtime trip coverage | Share of eligible scheduled trips observed in committed trip-update snapshots | Matched distinct trip IDs divided by eligible scheduled trips | Missing updates mean unknown/unobserved, never implicit on-time or cancellation; identifier compatibility constrains interpretation |
| Delay observation | One matched stop-time update observation | Arrival delay, falling back to departure delay, from GTFS-Realtime `StopTimeEvent.delay` | Rows without either delay are excluded; source delay quality and matching remain limitations |
| On-time performance | Share of eligible delay observations within configured on-time bounds, by route/network period | Count within bounds divided by eligible observations in dbt OTP marts | Unknown/unmatched observations are excluded and reported through coverage; not passenger-weighted |
| Delay distribution | Distribution and percentiles of observed delay seconds by route, stop, or network | dbt aggregation of realtime delay observations | Snapshot sampling can bias results; percentiles describe observed updates only |
| Explicit cancellations | Trips explicitly carrying the GTFS-Realtime cancelled schedule relationship | Distinct cancellation evidence keys from trip updates | A missing trip update is not a cancellation |
| Observed headway | Elapsed time between ordered observed vehicle/trip events for a route/time bucket | Timestamp difference in `fct_observed_headways` | Requires sufficient valid observations; polling cadence limits precision |
| Headway reliability | Gap/bunching classification for an observed headway | Observed headway compared with the applicable planned headway thresholds | Ineligible rows do not become healthy events; depends on schedule matching |
| Excess waiting time | Additional expected wait attributable to irregular observed service, by route/period | dbt aggregate over eligible observed headways relative to planned service | Absent when eligibility/sample requirements fail; not a direct passenger survey measure |
| Feed freshness | Age of a committed feed snapshot at collection/evaluation time | Collection timestamp minus feed header timestamp | Header timestamp may be absent or publisher-controlled; wall-clock and source-clock skew apply |
| Reliability incident snapshot | Analytical evidence consumed by incident rules, at rule/entity/evaluation grain | dbt mart derived from authoritative reliability outputs | Incident lifecycle state itself is owned by the operational repository, not dbt |

GTFS-Realtime collection is scheduled polling into historical snapshots. These KPIs must not be described as continuous event-stream metrics.
