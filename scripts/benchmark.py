"""Run deterministic diagnostic performance checks for legacy reliability helpers.

Authoritative reliability KPIs are dbt Gold models. This script only exercises
small in-memory helper functions used for diagnostics and migration checks.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from mobility_control_tower.reliability import delay_distribution, headway_reliability, on_time_performance, realtime_coverage


def main() -> None:
    output_dir = Path("data/benchmarks")
    output_dir.mkdir(parents=True, exist_ok=True)
    eligible = pd.DataFrame({"trip_id": [f"T{i}" for i in range(1000)], "route_id": ["R1"] * 1000})
    observed = pd.DataFrame({"trip_id": [f"T{i}" for i in range(850)] + ["UNMATCHED"], "route_id": ["R1"] * 851})
    stops = pd.DataFrame({"trip_id": [f"T{i}" for i in range(850)], "route_id": ["R1"] * 850, "delay_seconds": [i % 600 - 120 for i in range(850)]})
    checks = {}
    started = time.perf_counter()
    checks["coverage"] = realtime_coverage(eligible, observed, source="tisseo", service_date="2026-01-01", route_id="R1")
    checks["on_time"] = on_time_performance(stops, source="tisseo", route_id="R1")
    checks["delay"] = delay_distribution(stops, source="tisseo", route_id="R1")
    checks["headway"] = headway_reliability([28800, 29400, 30000, 30600, 31500, 31800], [600, 600, 600, 600, 600], source="tisseo", route_id="R1")
    duration = round(time.perf_counter() - started, 4)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": duration, "checks": checks}
    (output_dir / "benchmark.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "benchmark.md").write_text(
        "# Diagnostic Benchmark\n\n"
        "Authoritative reliability KPIs are produced by dbt Gold models; this "
        "benchmark exercises only legacy diagnostic helpers.\n\n"
        f"Generated at: {payload['generated_at']}\n\n"
        f"Duration: {duration} seconds\n\n"
        f"Coverage helper output: {checks['coverage']['coverage_percentage']}%\n",
        encoding="utf-8",
    )
    print(f"benchmark passed in {duration} seconds")


if __name__ == "__main__":
    main()
