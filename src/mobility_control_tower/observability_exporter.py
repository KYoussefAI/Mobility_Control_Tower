"""Durable operational metrics exporter for Prometheus."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST
from starlette.responses import Response

from mobility_control_tower.incidents import IncidentStore
from mobility_control_tower.operations.watermarks import read_watermark
from mobility_control_tower.realtime.historical_storage import discover_committed_snapshots
from mobility_control_tower.serving.duckdb_loader import resolve_current_database, validate_serving_database


def _parse_time(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _status_value(status: str | None) -> float:
    return 1.0 if status in {"success", "ready", "ok", "passed"} else 0.0


def _incomplete_snapshots(history_root: Path, source: str, feed_type: str) -> int:
    run = history_root / source / feed_type
    if not run.is_dir():
        return 0
    count = 0
    for directory in run.glob("date=*/hour=*/snapshot_timestamp=*"):
        if directory.is_dir() and not (directory / "_SUCCESS").is_file():
            count += 1
    return count


def collect_operational_metrics(
    *,
    source: str = "tisseo",
    feed_type: str = "trip_updates",
    serving_root: Path = Path("data/serving"),
    history_root: Path = Path("data/realtime_history"),
    watermark_root: Path = Path("data/watermarks"),
    quality_root: Path = Path("data/quality"),
) -> bytes:
    registry = CollectorRegistry()
    labels = ["source", "feed_type"]
    last_collection = Gauge("mct_realtime_last_collection_timestamp_seconds", "Last committed realtime collection timestamp.", labels, registry=registry)
    feed_age = Gauge("mct_realtime_feed_age_seconds", "Latest committed feed age in seconds.", labels, registry=registry)
    committed = Gauge("mct_realtime_committed_snapshots_total", "Committed realtime snapshots visible to analytics.", labels, registry=registry)
    incomplete = Gauge("mct_realtime_incomplete_snapshots", "Incomplete snapshot directories ignored by analytics.", labels, registry=registry)
    unprocessed = Gauge("mct_realtime_unprocessed_snapshots", "Committed snapshots beyond the analytical watermark.", labels, registry=registry)
    watermark_age = Gauge("mct_analytics_watermark_age_seconds", "Age of the latest analytical watermark update.", labels, registry=registry)
    serving_ready = Gauge("mct_serving_artifact_ready", "Whether the current serving artifact is queryable.", ["source"], registry=registry)
    serving_publish = Gauge("mct_serving_last_publish_timestamp_seconds", "Last serving publication timestamp.", ["source"], registry=registry)
    serving_age = Gauge("mct_serving_artifact_age_seconds", "Age of current serving publication.", ["source"], registry=registry)
    quality_success = Gauge("mct_quality_last_success", "Whether the latest quality-contract validation succeeded.", ["source", "suite"], registry=registry)
    quality_failed = Gauge("mct_quality_failed_expectations", "Failed quality-contract expectation count.", ["source", "suite"], registry=registry)
    pipeline_status = Gauge("mct_pipeline_last_status", "Last pipeline status as 1 for success and 0 otherwise.", ["source", "pipeline"], registry=registry)
    incidents_active = Gauge(
        "mct_incidents_active", "Active application incidents from durable incident state.", ["source", "rule", "severity", "status"], registry=registry
    )
    incidents_suppressed = Gauge(
        "mct_incidents_suppressed", "Suppressed application incidents from durable incident state.", ["source", "rule"], registry=registry
    )
    incident_last_success = Gauge(
        "mct_incident_evaluation_last_success_timestamp_seconds",
        "Timestamp of the last successful incident evaluation.",
        ["source"],
        registry=registry,
    )
    incident_last_failure = Gauge(
        "mct_incident_evaluation_last_failure_timestamp_seconds",
        "Timestamp of the last failed incident evaluation.",
        ["source"],
        registry=registry,
    )
    incident_candidates = Gauge("mct_incident_evaluation_candidates", "Candidates seen by incident evaluations.", ["source", "result"], registry=registry)
    incident_transitions = Gauge(
        "mct_incident_evaluation_transitions", "Incident transitions by bounded transition type.", ["source", "transition"], registry=registry
    )

    now = datetime.now(timezone.utc).timestamp()
    snapshots = discover_committed_snapshots(history_root / source / feed_type)
    committed.labels(source=source, feed_type=feed_type).set(len(snapshots))
    incomplete.labels(source=source, feed_type=feed_type).set(_incomplete_snapshots(history_root, source, feed_type))
    if snapshots:
        latest = snapshots[-1]
        latest_ts = _parse_time(latest.get("collection_time"))
        if latest_ts is not None:
            last_collection.labels(source=source, feed_type=feed_type).set(latest_ts)
        if latest.get("feed_age_seconds") is not None:
            feed_age.labels(source=source, feed_type=feed_type).set(float(latest["feed_age_seconds"]))

    watermark = read_watermark(watermark_root, source, feed_type, "incremental_refresh")
    processed = watermark.get("latest_successfully_processed_snapshot")
    processed_index = next((index for index, snapshot in enumerate(snapshots) if snapshot.get("snapshot_id") == processed), None)
    unprocessed_count = len(snapshots) if processed_index is None else max(0, len(snapshots) - processed_index - 1)
    unprocessed.labels(source=source, feed_type=feed_type).set(unprocessed_count)
    updated = _parse_time(watermark.get("updated_timestamp"))
    if updated is not None:
        watermark_age.labels(source=source, feed_type=feed_type).set(max(0.0, now - updated))
    pipeline_status.labels(source=source, pipeline="incremental_refresh").set(_status_value(watermark.get("status")))

    try:
        db_path = resolve_current_database(source, serving_root)
        validate_serving_database(db_path)
        serving_ready.labels(source=source).set(1)
        pointer = json.loads((serving_root / source / "current.json").read_text(encoding="utf-8"))
        published = _parse_time(pointer.get("generated_timestamp"))
        if published is not None:
            serving_publish.labels(source=source).set(published)
            serving_age.labels(source=source).set(max(0.0, now - published))
    except Exception:
        serving_ready.labels(source=source).set(0)

    quality_summary = quality_root / "latest_validation_summary.json"
    if quality_summary.is_file():
        payload = json.loads(quality_summary.read_text(encoding="utf-8"))
        suite = str(payload.get("suite", "all"))
        success = bool(payload.get("success", False))
        quality_success.labels(source=source, suite=suite).set(1 if success else 0)
        failed_value = payload.get("failed_expectations", payload.get("expectations_failed", 0))
        failed_count = len(failed_value) if isinstance(failed_value, list) else int(failed_value or 0)
        quality_failed.labels(source=source, suite=suite).set(float(failed_count))
        pipeline_status.labels(source=source, pipeline="quality_contracts").set(1 if success else 0)

    store = IncidentStore()
    active_counts: dict[tuple[str, str, str, str], int] = {}
    suppressed_counts: dict[tuple[str, str], int] = {}
    for incident in store.list_incidents(limit=500):
        status = str(incident.get("status"))
        if status in {"OPEN", "ACKNOWLEDGED", "MONITORING", "SUPPRESSED"}:
            key = (str(incident.get("source") or source), str(incident.get("rule_id") or "unknown"), str(incident.get("severity") or "INFO"), status)
            active_counts[key] = active_counts.get(key, 0) + 1
        if status == "SUPPRESSED":
            key2 = (str(incident.get("source") or source), str(incident.get("rule_id") or "unknown"))
            suppressed_counts[key2] = suppressed_counts.get(key2, 0) + 1
    for (metric_source, rule, severity, status), count in active_counts.items():
        incidents_active.labels(source=metric_source, rule=rule, severity=severity, status=status).set(count)
    for (metric_source, rule), count in suppressed_counts.items():
        incidents_suppressed.labels(source=metric_source, rule=rule).set(count)
    for run in store.list_evaluation_runs(source=source, limit=25):
        completed = _parse_time(run.get("completed_at") or run.get("started_at"))
        if completed is None:
            continue
        status = str(run.get("status"))
        if status == "SUCCESS":
            incident_last_success.labels(source=source).set(completed)
        if status == "FAILED":
            incident_last_failure.labels(source=source).set(completed)
        incident_candidates.labels(source=source, result=status.lower()).set(float(run.get("candidate_count") or 0))
        for transition in ("opened", "updated", "escalated", "resolved", "reopened", "suppressed", "skipped"):
            incident_transitions.labels(source=source, transition=transition).set(float(run.get(f"{transition}_count") or 0))
        break

    return generate_latest(registry)


def create_metrics_exporter_app(
    *,
    source: str = "tisseo",
    feed_type: str = "trip_updates",
    serving_root: Path = Path("data/serving"),
    history_root: Path = Path("data/realtime_history"),
    watermark_root: Path = Path("data/watermarks"),
    quality_root: Path = Path("data/quality"),
) -> FastAPI:
    app = FastAPI(title="MCT Metrics Exporter", version="0.1.0")

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        collect_operational_metrics(
            source=source,
            feed_type=feed_type,
            serving_root=serving_root,
            history_root=history_root,
            watermark_root=watermark_root,
            quality_root=quality_root,
        )
        return {"status": "ready"}

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(
            collect_operational_metrics(
                source=source,
                feed_type=feed_type,
                serving_root=serving_root,
                history_root=history_root,
                watermark_root=watermark_root,
                quality_root=quality_root,
            ),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app
