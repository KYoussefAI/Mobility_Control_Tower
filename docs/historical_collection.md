# Historical GTFS-Realtime Collection

## Why Snapshots Are Insufficient

The original real-time MVP preserved and parsed one GTFS-Realtime protobuf snapshot. That is useful for validating the feed, checking identifier compatibility, and computing point-in-time delay indicators, but it cannot answer historical questions:

- Is delay getting better or worse over the day?
- Which routes are repeatedly delayed?
- How fresh is the producer feed over time?
- How many trip updates are collected per polling window?

A single snapshot is evidence for one moment. Historical analytics require many immutable observations.

## Scheduled Polling Model

The historical collector uses APScheduler for local runs and Airflow for scheduled operation. It is intentionally not Kafka, Spark, Kubernetes, or cloud infrastructure.

Example:

```bash
python -m mobility_control_tower.cli collect-gtfs-rt \
  --source tisseo \
  --feed-type trip_updates \
  --interval 30
```

Each poll performs the same deterministic sequence:

1. Fetch the configured GTFS-Realtime protobuf.
2. Preserve the raw `feed.pb`.
3. Parse trip updates and stop time updates.
4. Add historical metadata columns.
5. Write Parquet files into a temporary snapshot directory.
6. Validate required files and row counts.
7. Write `_SUCCESS` last.
8. Atomically rename the snapshot into the final date/hour partition.
9. Append one JSON line to the collection log.

Stop the collector with `CTRL+C`. The scheduler shuts down gracefully and keeps all snapshots collected so far.

## Storage Layout

Raw snapshots are immutable:

```text
data/raw_realtime/historical/
  tisseo/
    trip_updates/
      date=YYYY-MM-DD/
        hour=HH/
          <snapshot_id>/
            feed.pb
            metadata.json
            _SUCCESS
```

Parsed history is partitioned by collection date and hour, with one snapshot directory per poll:

```text
data/realtime_history/
  tisseo/
    trip_updates/
      collection_log.jsonl
      date=YYYY-MM-DD/
        hour=HH/
          snapshot_timestamp=<snapshot_id>/
            trip_updates.parquet
            stop_time_updates.parquet
            feed_summary.parquet
            metadata.json
            _SUCCESS
```

The collector never writes one huge file and never deletes prior snapshots. Snapshot identity is deterministic from source, feed type, feed header timestamp when available, and payload checksum. Repeating the same snapshot is a no-op. Reusing an existing snapshot id with a different checksum is a hard failure. Incomplete directories without `_SUCCESS` are invisible to analytics.

## Watermarks

Incremental analytics use durable watermark JSON under `data/watermarks/<source>/<feed_type>/incremental_refresh.json`. The refresh DAG reads the prior watermark, selects committed snapshots beyond it with a bounded lookback, runs dbt and quality, publishes serving atomically, and advances the watermark last. The watermark is never advanced on dbt, quality, or serving failure.

## Historical Metadata

Every parsed row receives operational metadata:

- `snapshot_timestamp`
- `collection_time`
- `feed_age_seconds`
- `poll_number`
- `collection_date`
- `collection_hour`

These columns make the dataset auditable and allow downstream KPIs to group by poll, date, and hour.

## Parquet Advantages

Parquet is used for parsed history because it is columnar, compressed, typed, and efficient for analytical reads. DuckDB can query partitioned Parquet files directly with predicate pushdown, so the serving layer does not need to copy all historical rows into a database table.

## Historical KPIs

Build historical gold tables after collecting snapshots:

```bash
python -m mobility_control_tower.cli build-history-kpis \
  --history-run data/realtime_history/tisseo/trip_updates
```

Outputs are written under:

```text
data/history_gold/tisseo/trip_updates/YYYY-MM-DD_HHMMSS/
```

Generated tables include route delay history, stop delay history, delay evolution by hour, feed freshness trend, trip match trend, and daily summary.

## DuckDB Serving

Build a serving database with historical Parquet views:

```bash
python -m mobility_control_tower.cli build-serving-db \
  --gold-run data/gold/tisseo/<static_run> \
  --history-run data/realtime_history/tisseo/trip_updates \
  --history-gold-run data/history_gold/tisseo/trip_updates/<history_gold_run>
```

Historical views:

- `v_delay_history`
- `v_route_delay_history`
- `v_feed_health_history`
- `v_collection_summary`

## Future Streaming Migration

This design is deliberately compatible with a future streaming phase. The raw archive already acts as an immutable event log, parsed Parquet partitions provide replayable analytical storage, and metadata columns preserve collection timing. A future Kafka-based collector could write to the same historical contracts while replacing only the polling/fetch layer.
