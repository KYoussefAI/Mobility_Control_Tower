# Mobility Control Tower

## Overview

Incremental historical processing uses persisted watermarks and storage inventory checks. A refresh selects observations beyond the committed watermark, performs downstream work, and advances state only after successful completion. Repeated processing is therefore recoverable and testable for idempotency.

## Processing Semantics

```text
discover committed snapshots -> filter by watermark -> build/test/publish -> advance watermark last
```

The watermark records processing progress; it does not alter immutable historical snapshots. The project deliberately retains bounded polling rather than introducing a distributed event platform. See [`docs/adr/0002-polling-over-kafka.md`](docs/adr/0002-polling-over-kafka.md).

## Verification and Limitations

`scripts/assert_incremental_idempotency.py` checks repeated incremental behavior. Execution remains manually initiated, local, and single-platform; no scheduler coordinates retries or dependencies yet.
