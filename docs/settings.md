# Runtime Settings

Settings are loaded through Pydantic Settings. Environment variables prefixed with `MCT_` override defaults and YAML source configuration remains supported for transport feeds.

| Setting | Environment variable | Default |
| --- | --- | --- |
| GTFS source | `MCT_GTFS_SOURCE` | `tisseo` |
| source config path | `MCT_CONFIG_PATH` | `config/sources.yml` |
| storage backend | `MCT_STORAGE_BACKEND` | `local` |
| local storage root | `MCT_STORAGE_ROOT` | `data` |
| S3 bucket | `MCT_S3_BUCKET` | empty |
| S3 prefix | `MCT_S3_PREFIX` | empty |
| AWS region | `MCT_AWS_REGION` | `eu-west-3` |
| explicit DuckDB path | `MCT_DUCKDB_PATH` | empty; API resolves `data/serving/<source>/current.json` |
| serving root | `MCT_SERVING_ROOT` | `data/serving` |
| history path | `MCT_HISTORY_PATH` / `MCT_HISTORY_ROOT` | `data/realtime_history` |
| watermark root | `MCT_WATERMARK_ROOT` | `data/watermarks` |
| collection interval | `MCT_COLLECTION_INTERVAL_SECONDS` | `60` |
| refresh interval | `MCT_REFRESH_INTERVAL_SECONDS` | `600` |
| incremental lookback | `MCT_INCREMENTAL_LOOKBACK_COUNT` | `1` |
| feed age warning/critical | `MCT_FEED_AGE_WARNING_SECONDS` / `MCT_FEED_AGE_CRITICAL_SECONDS` | `600` / `1800` |
| API version | `MCT_API_VERSION` | `v1` |
| log level | `MCT_LOG_LEVEL` | `INFO` |
| benchmark output | `MCT_BENCHMARK_OUTPUT_DIR` | `data/benchmarks` |
