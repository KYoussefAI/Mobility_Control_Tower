"""Honest local performance benchmarks for existing Mobility Control Tower artifacts."""

from __future__ import annotations

import json
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import duckdb

from mobility_control_tower.api.app import create_app
from mobility_control_tower.serving.duckdb_loader import query_serving_database


def _measure(name: str, fn: Callable[[], int | None]) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    rows = fn()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "name": name,
        "duration_seconds": round(time.perf_counter() - started, 4),
        "rows_processed": rows,
        "peak_memory_mb": round(peak / (1024 * 1024), 3),
    }


def _count_csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _count_parquet_rows(root: Path) -> int:
    files = sorted(root.glob("date=*/hour=*/snapshot_timestamp=*/stop_time_updates.parquet"))
    if not files:
        return 0
    with duckdb.connect() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM read_parquet(?)", [[str(path) for path in files]]).fetchone()[0])


def run_benchmarks(
    *,
    raw_run: Path | None = None,
    bronze_run: Path | None = None,
    silver_run: Path | None = None,
    gold_run: Path | None = None,
    history_run: Path | None = None,
    db_path: Path | None = None,
    output_dir: Path = Path("data/benchmarks"),
) -> Path:
    """Benchmark readable local artifacts without mutating the pipeline."""
    results: list[dict[str, Any]] = []
    if raw_run:
        results.append(_measure("gtfs_ingestion_artifact_scan", lambda: len(list(raw_run.glob("*")))))
    if bronze_run:
        results.append(_measure("bronze_build_artifact_scan", lambda: sum(_count_csv_rows(path) for path in bronze_run.glob("*.csv"))))
    if silver_run:
        results.append(_measure("silver_build_artifact_scan", lambda: sum(_count_csv_rows(path) for path in silver_run.glob("*.csv"))))
    if gold_run:
        results.append(_measure("gold_build_artifact_scan", lambda: sum(_count_csv_rows(path) for path in gold_run.glob("*.csv"))))
    if history_run:
        results.append(_measure("historical_polling_parquet_scan", lambda: _count_parquet_rows(history_run)))
    if db_path and db_path.is_file():
        results.append(_measure("duckdb_query_top_routes", lambda: len(query_serving_database(db_path, "top-routes", 10))))

        def api_latency() -> int:
            app = create_app(db_path)
            app.openapi()
            return 1

        results.append(_measure("api_latency_openapi_generation", api_latency))

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    markdown_path = output_dir / f"benchmark_{run_id}.md"
    summary = {"generated_timestamp": datetime.now(timezone.utc).isoformat(), "benchmarks": results}
    (output_dir / f"benchmark_{run_id}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = ["# Mobility Control Tower Benchmark", "", "| Benchmark | Duration seconds | Rows processed | Peak memory MB |", "| --- | ---: | ---: | ---: |"]
    for result in results:
        lines.append(f"| {result['name']} | {result['duration_seconds']} | {result['rows_processed']} | {result['peak_memory_mb']} |")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return markdown_path
