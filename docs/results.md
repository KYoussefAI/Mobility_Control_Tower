# Real-world Results and Engineering Findings

This document records the results of rebuilding the analytical layer over the accumulated local GTFS-Realtime history. The figures describe published TripUpdates and their compatibility with the static GTFS archive available at rebuild time.

## Collection window

| Property | Result |
| --- | ---: |
| First collected snapshot | 26 September 2026, 22:35:22 UTC |
| Last collected snapshot | 12 October 2026, 16:32:02 UTC |
| Unique snapshots | 1,436 |
| UTC calendar dates represented | 17 |
| Elapsed collection window | 15 days, 17 hours, 57 minutes |
| Median interval between snapshots | 5 minutes |
| Fresh snapshots across full history | 1,429 of 1,436 (99.5%) |
| Fresh snapshots in latest 24 hours | 85 of 86 (98.8%) |
| Static GTFS validity window | 8 October–11 November 2026 |
| Realtime dates compatible with that schedule | 5 of 17 |

The collector targets a five-minute cadence. The elapsed window and number of represented dates describe the retained history; they do not imply uninterrupted collection.

## Analytical grain

| Layer | Grain | Purpose |
| --- | --- | --- |
| Poll history | One source observation from one collection, keyed by snapshot, entity, and stop sequence | Lineage, source diagnostics, and feed health |
| Canonical KPI history | One latest valid published observation per service date, trip, and stop sequence | On-time performance and delay distributions |

Polling the same feed repeatedly does not produce independent service events. A trip-stop may be published in many snapshots as its prediction changes. Treating every poll as a separate observation would over-weight long-lived or frequently updated trips and inflate the apparent sample size.

The canonical model first collapses exact analytical duplicates, identifies conflicting variants at a source key, filters to valid schedule matches and sane delays, and then retains the latest effective publication for each `service_date` / `trip_id` / `stop_sequence`. Its 266,806 records represent published trip-stop updates, not individual passengers or verified physical arrivals.

## Network results

Representative results for the schedule-compatible service date 10 October 2026:

| Metric | Result |
| --- | ---: |
| On-time performance | 79.1% |
| Median published delay | 1 min 25 sec late |
| P90 published delay | 5 min 35 sec late |
| Observed trips | 1,331 |
| Canonical trip-stop records | 34,131 |
| Eligible scheduled trips | 8,201 |
| Trips without a valid realtime match | 6,870 |
| Realtime trip coverage | 16.2% |

On-time means the latest canonical published delay is between -60 and +300 seconds, inclusive. The P90 means 90% of canonical matched delays were at or below 5 minutes 35 seconds. The sample status was `SUFFICIENT`, based on 34,131 canonical matched trip-stop records.

## Route example

Route 13 is a representative route-level result for 10 October 2026; it is not presented as a best- or worst-performing route.

| Metric | Result |
| --- | ---: |
| On-time performance | 88.8% |
| Median published delay | 1 min 22 sec late |
| P90 published delay | 3 min 30 sec late |
| Observed trips | 20 |
| Canonical trip-stop records | 543 |

## Data-quality findings

The poll-grain intermediate contains 15,173,229 source keys after exact analytical duplicates are collapsed. Every percentage below uses that total as its denominator.

| Source classification | Count | Share of source keys | Analytical handling |
| --- | ---: | ---: | --- |
| Valid delay | 14,228,638 | 93.7746% | Eligible for schedule matching and canonical selection |
| Missing delay | 619,333 | 4.0817% | Preserved as unknown; excluded from reliability KPIs |
| Outside ±7,200 seconds | 320,274 | 2.1108% | Retained as `OUT_OF_RANGE`; excluded from KPI denominators |
| Ambiguous source key | 4,984 | 0.0328% | Conflicting variants remain traceable; excluded from reliability KPIs |

Source-level issues included exact duplicate keys, conflicting stop information, conflicting delay values, missing delays, and delays outside the configured sanity bound. Raw and Silver retain the received records. Exact duplicates may collapse only in the analytical layer; no ambiguity is resolved by guessing.

The 266,806 canonical records are not a remainder calculated directly from this table. Many valid source keys are repeated publications of the same trip-stop across successive polls, and canonicalization retains only the latest valid schedule-matched publication.

## Coverage interpretation

Realtime trip coverage is:

```text
distinct scheduled trips with a valid realtime match
────────────────────────────────────────────────────
eligible scheduled trips on a schedule-compatible date
```

For 10 October, 1,331 of 8,201 eligible scheduled trips had at least one canonical valid trip-stop match, producing 16.2% coverage. The remaining 6,870 trips are `UNKNOWN`. Low coverage does not imply that those trips were cancelled, delayed, or on time; it can reflect incomplete TripUpdate publication, collection gaps, identifier mismatches, or other upstream availability constraints.

Matching is date-aware. A trip is eligible only when the same `trip_id` exists in the static schedule on that service date. The 12 realtime-history dates outside the available static GTFS validity window cannot support schedule-comparison KPIs, even if an identical trip identifier exists elsewhere in the schedule. Those snapshots still contribute to feed-health history.

## Feed health

Feed freshness is the age of the GTFS-Realtime publisher timestamp when a snapshot is collected:

| Status | Rule |
| --- | --- |
| `FRESH` | Age ≤ 90 seconds |
| `DELAYED` | 90 seconds < age ≤ 300 seconds |
| `STALE` | Age > 300 seconds |
| `UNKNOWN` | Publisher timestamp unavailable |

The latest snapshot was collected on 12 October 2026 at 16:32:02 UTC. Its publisher timestamp was 16:31:55 UTC, giving an age of seven seconds and a `FRESH` status. Across the latest 24 hours, 85 of 86 snapshots were fresh (98.8%). Across the full history, 1,429 of 1,436 were fresh (99.5%) and seven were delayed.

## Limitations

- TripUpdates are published realtime updates, not guaranteed ground-truth arrival measurements.
- Results are not passenger-weighted; each canonical matched trip-stop contributes one observation.
- Schedule comparison requires static GTFS history compatible with the realtime service date.
- Coverage depends on upstream TripUpdate completeness, identifier compatibility, and collection cadence.
- Local rebuilds scan a growing history, although expensive canonical intermediates are materialized and execution is bounded to one thread, 2 GB of DuckDB memory, and disk spilling.
