# Real-time snapshot KPI definitions

These indicators are computed from one parsed GTFS-Realtime Trip Updates snapshot and one static silver GTFS run.

## Feed health

`rt_feed_health_snapshot.csv` describes the snapshot itself: feed type, fetch time, header timestamp, feed age, entity counts, identifier counts, and whether delay fields are present.

Freshness status:

- PASS: feed age is 90 seconds or less;
- WARN: feed age is over 90 seconds and up to 300 seconds;
- FAIL: feed age is over 300 seconds;
- UNKNOWN: feed age cannot be computed.

This is a snapshot health indicator, not a service-level guarantee.

## Identifier compatibility

`rt_identifier_compatibility_snapshot.csv` compares distinct `route_id`, `trip_id`, and `stop_id` values from the real-time snapshot with static silver GTFS tables.

Status:

- PASS: match percentage is at least 95%;
- WARN: match percentage is at least 50% and below 95%;
- FAIL: match percentage is below 50%;
- NOT_APPLICABLE: no values are available.

This helps explain whether static/live joins are safe enough for later phases.

## Enriched trip updates

`rt_trip_update_enriched.csv` keeps every parsed trip update row and adds route names, route match flags, trip match flags, and a compatibility note. Rows with unmatched `trip_id` values are preserved for diagnosis.

## Route delay snapshot

`rt_route_delay_snapshot.csv` groups stop-time updates by route. Delay uses `arrival_delay` when available, otherwise `departure_delay`. It reports average, median, min, max, five-minute delay counts, early update counts, and missing-delay counts.

This is not route reliability. It is only delay observed in one snapshot.

## Stop delay snapshot

`rt_stop_delay_snapshot.csv` groups stop-time updates by stop and adds static stop names when available. It reports the same delay logic at stop level.

## Limitations of single-snapshot metrics

A single snapshot cannot prove recurring delay patterns, punctuality, cancellation behavior, or passenger waiting time. It can only show what was visible at one fetch time.

## What continuous reliability would need

Continuous reliability indicators would require repeated snapshots over time, stable scheduling of fetches, storage design, deduplication rules, temporal windows, stronger static/live matching, and clear definitions for delay, cancellation, and headway reliability.

Those concerns are intentionally outside this snapshot-only phase.
