"""Prometheus metrics for the Mobility Control Tower."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

PIPELINE_DURATION = Histogram("mct_pipeline_duration_seconds", "Pipeline task duration in seconds", ["pipeline", "task"])
PIPELINE_SUCCESS = Counter("mct_pipeline_success_total", "Successful pipeline tasks", ["pipeline", "task"])
PIPELINE_FAILURES = Counter("mct_pipeline_failures_total", "Failed pipeline tasks", ["pipeline", "task"])
ROWS_PROCESSED = Counter("mct_rows_processed_total", "Rows processed by pipeline tasks", ["pipeline", "task"])
API_REQUESTS = Counter("mct_api_requests_total", "API requests", ["method", "path", "status"])
HISTORICAL_POLLS = Counter("mct_historical_polls_total", "Historical realtime polls", ["source", "feed_type"])
FEED_FRESHNESS = Gauge("mct_feed_freshness_seconds", "GTFS-Realtime feed freshness", ["source", "feed_type"])
DUCKDB_QUERY_DURATION = Histogram("mct_duckdb_query_duration_seconds", "DuckDB query duration in seconds", ["query"])


def observe_duration(metric: Histogram, labels: dict[str, str], fn: Callable[[], Any]) -> Any:
    start = time.perf_counter()
    try:
        return fn()
    finally:
        metric.labels(**labels).observe(time.perf_counter() - start)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
