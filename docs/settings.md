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
| DuckDB path | `MCT_DUCKDB_PATH` | `data/serving/tisseo/2026-07-17_160355/mobility_control_tower.duckdb` |
| history path | `MCT_HISTORY_PATH` | `data/realtime_history` |
| API version | `MCT_API_VERSION` | `v1` |
| log level | `MCT_LOG_LEVEL` | `INFO` |
| benchmark output | `MCT_BENCHMARK_OUTPUT_DIR` | `data/benchmarks` |

