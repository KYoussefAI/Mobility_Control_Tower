"""Validate Grafana dashboard PromQL references against known MCT metrics."""

from __future__ import annotations

import json
import re
from pathlib import Path

KNOWN_METRICS = {
    "mct_api_requests_total",
    "mct_duckdb_query_duration_seconds_bucket",
    "mct_pipeline_last_status",
    "mct_quality_failed_expectations",
    "mct_quality_last_success",
    "mct_realtime_committed_snapshots_total",
    "mct_realtime_feed_age_seconds",
    "mct_realtime_unprocessed_snapshots",
    "mct_serving_artifact_age_seconds",
    "mct_serving_artifact_ready",
    "mct_analytics_watermark_age_seconds",
    "mct_incident_evaluation_candidates",
    "mct_incident_evaluation_last_success_timestamp_seconds",
    "mct_incident_evaluation_transitions",
    "mct_incidents_active",
    "mct_incidents_suppressed",
}
PROMQL_FUNCTIONS = {"by", "histogram_quantile", "label_values", "rate", "sum"}


def main() -> None:
    dashboard = json.loads(Path("observability/grafana/dashboards/mct-operations.json").read_text(encoding="utf-8"))
    expressions: list[str] = []
    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            if target.get("expr"):
                expressions.append(target["expr"])
    referenced: set[str] = set()
    for expr in expressions:
        for token in re.findall(r"\b[a-zA-Z_:][a-zA-Z0-9_:]*\b", expr):
            if token.startswith("mct_"):
                referenced.add(token)
    missing = sorted(referenced - KNOWN_METRICS)
    if missing:
        raise SystemExit(f"Grafana dashboard references unknown metrics: {', '.join(missing)}")
    print(f"Validated {len(expressions)} Grafana expressions.")


if __name__ == "__main__":
    main()
