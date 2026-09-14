# Immutable Realtime History

Each successful poll stores raw bytes and parsed Parquet tables under
source/feed/date/hour/snapshot partitions. Content-derived snapshot identifiers,
checksums, collection time, source header time, and a `_SUCCESS` marker make the
commit boundary explicit. Readers ignore incomplete partitions.

An identical committed payload is idempotent; a conflicting payload cannot
overwrite an existing snapshot. This document covers persistence only.
Trend and reliability models are introduced separately.
