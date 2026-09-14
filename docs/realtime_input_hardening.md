# Realtime Input Hardening

The parser distinguishes structural rejection from graceful degradation:

- malformed, truncated, or missing-required-field protobufs are rejected before
  an output directory is created;
- valid empty feeds, absent timestamps, stale timestamps, and implausibly future
  timestamps produce diagnostic summaries but are ineligible for operational
  delay metrics;
- duplicate non-empty entity IDs keep the first entity and report the remainder;
- entities without a usable update and stop updates without both a stop reference
  and event evidence are skipped with counts;
- explicit cancellation relationships remain usable without stop updates;
- unknown trip IDs and conflicting trip/route pairs remain explicit compatibility
  warnings.

Thresholds default to 30 minutes stale and five minutes future-clock tolerance.
They protect snapshot metrics from silently treating bad timing evidence as
current service state; they are not universal GTFS-Realtime requirements.
