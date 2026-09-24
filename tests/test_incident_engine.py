import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from mobility_control_tower.api.app import create_app
from mobility_control_tower.incidents import (
    CandidateState,
    EvaluationResult,
    IncidentCandidate,
    IncidentEvaluationEngine,
    IncidentStore,
    Severity,
    default_rule_config,
    migrate_incident_store,
)
from mobility_control_tower.security import create_access_token

FIXED_TIME = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def candidate(
    key: str,
    *,
    state: CandidateState = CandidateState.UNHEALTHY,
    severity: Severity | None = Severity.WARNING,
    value: float | None = 100.0,
    rule_id: str = "stale_feed",
    entity_type: str = "feed",
    entity_id: str = "trip_updates",
) -> IncidentCandidate:
    return IncidentCandidate(
        candidate_key=key,
        rule_id=rule_id,
        rule_version=f"{rule_id}_v1",
        source="tisseo",
        feed_type="trip_updates" if entity_type == "feed" else None,
        entity_type=entity_type,
        entity_id=entity_id,
        service_date="2026-01-01",
        period_start="2026-01-01T08:00:00+00:00",
        period_end="2026-01-01T09:00:00+00:00",
        observed_at=FIXED_TIME.isoformat(),
        metric_name="metric",
        metric_value=value,
        warning_threshold=80.0,
        critical_threshold=300.0,
        healthy_threshold=50.0,
        candidate_state=state,
        suggested_severity=severity,
        confidence="HIGH",
        coverage=100.0,
        calculation_version="reliability_v1",
        serving_run_id="serving-fixed",
        evidence={"metric_value": value, "evidence_key": key, "calculation_version": "reliability_v1", "serving_run_id": "serving-fixed"},
    )


def test_migration_creates_clean_store(tmp_path: Path) -> None:
    migrate_incident_store(tmp_path / "incidents")
    store = IncidentStore(tmp_path / "incidents")

    assert store.list_incidents() == []
    assert store.list_events() == []


def test_open_escalate_acknowledge_monitor_resolve_and_reopen_are_audited(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)

    opened = engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")
    repeated = engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")
    escalated = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates", severity=Severity.CRITICAL, value=400.0), now=FIXED_TIME, correlation_id="corr-2"
    )
    acknowledged = store.transition(opened.incident_id or "", status="ACKNOWLEDGED", operator="operator", note="Seen")
    first_healthy = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates", state=CandidateState.HEALTHY, severity=None, value=10.0),
        now=FIXED_TIME + timedelta(minutes=10),
        correlation_id="corr-3",
    )
    resolved = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates", state=CandidateState.HEALTHY, severity=None, value=9.0),
        now=FIXED_TIME + timedelta(minutes=20),
        correlation_id="corr-4",
    )
    reopened = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates", severity=Severity.WARNING, value=200.0),
        now=FIXED_TIME + timedelta(minutes=30),
        correlation_id="corr-5",
    )

    row = store.get_by_id(opened.incident_id or "")
    events = [event["event_type"] for event in store.list_events(opened.incident_id)]

    assert opened.action == "opened"
    assert repeated.action == "skipped"
    assert escalated.action == "escalated"
    assert acknowledged["status"] == "ACKNOWLEDGED"
    assert first_healthy.event_type == "MONITORING_STARTED"
    assert resolved.event_type == "AUTO_RESOLVED"
    assert reopened.event_type == "REOPENED"
    assert row is not None
    assert row["status"] == "OPEN"
    assert row["recurrence_count"] == 1
    assert events[0] == "OPENED"
    assert {
        "SEVERITY_ESCALATED",
        "ACKNOWLEDGED",
        "MONITORING_STARTED",
        "AUTO_RESOLVED",
        "REOPENED",
    }.issubset(events)


def test_suppression_preserves_evidence_and_expiry_reopens_when_unhealthy(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    opened = engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")
    store.transition(
        opened.incident_id or "",
        status="SUPPRESSED",
        operator="operator",
        note="Maintenance",
        suppress_until=(FIXED_TIME + timedelta(minutes=5)).isoformat(),
    )

    suppressed = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates", value=200.0),
        now=FIXED_TIME + timedelta(minutes=1),
        correlation_id="corr-2",
    )
    expired = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates", value=201.0),
        now=FIXED_TIME + timedelta(minutes=6),
        correlation_id="corr-3",
    )
    row = store.get_by_id(opened.incident_id or "")

    assert suppressed.action == "suppressed"
    assert expired.action == "updated"
    assert row is not None
    assert row["status"] == "OPEN"
    assert row["suppression_expires_at"] is None
    assert any(event["event_type"] == "SUPPRESSION_EXPIRED" for event in store.list_events(opened.incident_id))


def test_invalid_transition_and_manual_resolution_reason_fail(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    opened = engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")

    with pytest.raises(ValueError, match="Manual resolution requires"):
        store.transition(opened.incident_id or "", status="RESOLVED", operator="operator", note="")

    store.transition(opened.incident_id or "", status="RESOLVED", operator="operator", note="Fixed")
    with pytest.raises(ValueError, match="Invalid incident transition"):
        store.transition(opened.incident_id or "", status="ACKNOWLEDGED", operator="operator", note="late")


def test_identical_evaluation_is_idempotent_and_dry_run_does_not_mutate(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")

    class FixedEngine(IncidentEvaluationEngine):
        def load_candidates(self, *, source, evaluation_time, correlation_id):  # type: ignore[no-untyped-def]
            return [candidate("low_coverage:tisseo:network:2026-01-01:am_peak", rule_id="low_realtime_coverage", entity_type="network", entity_id="network")]

    engine = FixedEngine(repository=store.repository)
    first = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="retry")
    second = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="retry")
    dry = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="dry", dry_run=True)

    assert first.opened_count == 1
    assert second.opened_count == 0
    assert second.skipped_count == 1
    assert dry.dry_run is True
    assert len(store.list_incidents()) == 1
    assert len(store.list_events()) == 1


def test_lock_conflict_is_recorded_and_released_after_failure(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    assert store.repository.acquire_evaluation_lock("incidents:tisseo", "owner-a", FIXED_TIME)
    engine = IncidentEvaluationEngine(repository=store.repository)

    result = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="locked")
    store.repository.release_evaluation_lock("incidents:tisseo", "owner-a")
    assert store.repository.acquire_evaluation_lock("incidents:tisseo", "owner-b", FIXED_TIME)

    assert result.status == "SKIPPED_LOCKED"
    assert result.skipped_count == 1


def test_rule_configuration_validation() -> None:
    config = default_rule_config()
    assert config.stale_feed.version == "stale_feed_v1"
    assert config.low_realtime_coverage.healthy_at_or_above_percentage > config.low_realtime_coverage.warning_below_percentage


def test_v1_incident_api_authorization_and_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "incident-api-secret")
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    opened = engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")

    import mobility_control_tower.api.routes as route_module

    monkeypatch.setattr(route_module, "IncidentStore", lambda: store)
    client = TestClient(create_app(None, source="tisseo", serving_root=tmp_path / "serving"))
    reader = create_access_token("reader", {"operations:read"}, expires_in_seconds=60)
    writer = create_access_token("writer", {"incidents:write"}, expires_in_seconds=60)

    assert client.get("/v1/incidents").status_code == 401
    assert client.get("/v1/incidents", headers={"Authorization": f"Bearer {reader}"}).status_code == 200
    assert client.post(f"/v1/incidents/{opened.incident_id}/resolve", headers={"Authorization": f"Bearer {writer}"}, json={}).status_code == 422
    ack = client.post(f"/v1/incidents/{opened.incident_id}/acknowledge", headers={"Authorization": f"Bearer {writer}"}, json={"reason": "checking"})
    events = client.get(f"/v1/incidents/{opened.incident_id}/events", headers={"Authorization": f"Bearer {reader}"})

    assert ack.status_code == 200
    assert ack.json()["data"][0]["acknowledged_by"] == "writer"
    assert [event["event_type"] for event in events.json()["data"]] == ["OPENED", "ACKNOWLEDGED"]


def test_v1_admin_can_trigger_incident_evaluation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "incident-api-secret")

    class FakeEngine:
        def evaluate(self, *, source=None, correlation_id=None, dry_run=False):  # type: ignore[no-untyped-def]
            return EvaluationResult(
                evaluation_run_id="eval-api",
                correlation_id=correlation_id or "eval-api",
                status="SUCCESS",
                source_filter=source,
                serving_run_id="serving-api",
                rule_versions={"stale_feed": "stale_feed_v1"},
                candidate_count=1,
                skipped_count=1,
                dry_run=dry_run,
            )

    import mobility_control_tower.api.routes as route_module

    monkeypatch.setattr(route_module, "IncidentEvaluationEngine", FakeEngine)
    client = TestClient(create_app(None, source="tisseo", serving_root=tmp_path / "serving"))
    reader = create_access_token("reader", {"operations:read"}, expires_in_seconds=60)
    admin = create_access_token("admin", {"admin"}, expires_in_seconds=60)

    assert client.post("/v1/incidents/evaluate", headers={"Authorization": f"Bearer {reader}"}).status_code == 401
    response = client.post("/v1/incidents/evaluate?source=tisseo&dry_run=true", headers={"Authorization": f"Bearer {admin}", "Idempotency-Key": "api-key"})

    assert response.status_code == 200
    assert response.json()["data"][0]["dry_run"] is True
    assert response.json()["data"][0]["correlation_id"] == "api-key"


def test_metrics_labels_are_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")

    import mobility_control_tower.observability_exporter as exporter

    monkeypatch.setattr(exporter, "IncidentStore", lambda: store)
    metrics = exporter.collect_operational_metrics(
        serving_root=tmp_path / "serving", history_root=tmp_path / "history", quality_root=tmp_path / "quality"
    ).decode()

    assert 'mct_incidents_active{rule="stale_feed",severity="WARNING",source="tisseo",status="OPEN"} 1.0' in metrics
    assert "incident_id" not in metrics
    assert "entity_id" not in metrics


def test_event_jsonl_is_append_only_compatibility_mirror(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    opened = engine.apply_candidate(candidate("stale_feed:tisseo:trip_updates"), now=FIXED_TIME, correlation_id="corr-1")
    store.transition(opened.incident_id or "", status="ACKNOWLEDGED", operator="operator", note="Seen")

    events = (tmp_path / "incidents" / "incident_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    payloads = [json.loads(line) for line in events]

    assert [payload["event_type"] for payload in payloads] == ["OPENED", "ACKNOWLEDGED"]


def write_sources_config(path: Path) -> None:
    path.write_text(
        """
sources:
  tisseo:
    name: Tisseo
    city: Toulouse
    country: FR
    timezone: Europe/Paris
    language: fr
    static_gtfs:
      enabled: true
      url: https://example.test/static.zip
    realtime:
      trip_updates:
        enabled: true
        url: https://example.test/trips.pb
      vehicle_positions:
        enabled: true
        url: https://example.test/vehicles.pb
      service_alerts:
        enabled: false
        url:
""",
        encoding="utf-8",
    )


def write_snapshot(history_root: Path, *, feed_type: str, collection_time: str, feed_age_seconds: int) -> None:
    snapshot = history_root / "tisseo" / feed_type / "date=2026-01-01" / "hour=07" / "snapshot_timestamp=s1"
    snapshot.mkdir(parents=True)
    (snapshot / "metadata.json").write_text(
        json.dumps(
            {
                "source": "tisseo",
                "feed_type": feed_type,
                "snapshot_id": f"{feed_type}-s1",
                "collection_time": collection_time,
                "feed_header_timestamp": 1767250800,
                "feed_age_seconds": feed_age_seconds,
            }
        ),
        encoding="utf-8",
    )
    files = {
        "trip_updates": ("trip_updates.parquet", "stop_time_updates.parquet", "feed_summary.parquet"),
        "vehicle_positions": ("vehicle_positions.parquet", "feed_summary.parquet"),
        "service_alerts": ("alerts.parquet", "alert_informed_entities.parquet", "feed_summary.parquet"),
    }[feed_type]
    for name in files:
        pd.DataFrame([]).to_parquet(snapshot / name)
    (snapshot / "_SUCCESS").write_text("", encoding="utf-8")


def write_serving_db(serving_root: Path) -> None:
    run = serving_root / "tisseo" / "runs" / "serving-fixed"
    run.mkdir(parents=True)
    db_path = run / "mobility_control_tower.duckdb"
    with duckdb.connect(str(db_path)) as connection:
        connection.execute(
            """
            create table realtime_trip_coverage as
            select 'tisseo' as source, date '2026-01-01' as service_date, 'R1' as route_id,
                   'am_peak' as service_period, 'trip_updates' as feed_type,
                   'reliability_v1' as calculation_version, 10 as eligible_scheduled_trip_count,
                   4 as observed_eligible_trip_count, 6 as unobserved_eligible_trip_count,
                   1 as unmatched_realtime_trip_count, 0 as ambiguous_realtime_trip_count,
                   0 as explicit_cancellation_count, 40.0 as coverage_percentage,
                   'OBSERVED' as coverage_status, 'HIGH' as confidence_status
            union all
            select 'tisseo', date '2026-01-01', 'R2', 'am_peak', 'trip_updates',
                   'reliability_v1', 2, 0, 2, 0, 0, 0, 0.0, 'NO_REALTIME_EVIDENCE', 'NO_COVERAGE'
            """
        )
        connection.execute("create view v_realtime_trip_coverage as select * from realtime_trip_coverage")
        connection.execute(
            """
            create table fct_headway_reliability_events as
            select 'tisseo' as source, '2026-01-01' as service_date, 'R1' as route_id,
                   '0' as direction_id, 'S1' as reference_stop_id,
                   '2026-01-01T08:05:00+00:00' as event_timestamp,
                   'SERVICE_GAP' as event_type, '300' as planned_headway_seconds,
                   '1000' as observed_headway_seconds, '3.33' as headway_ratio,
                   '2.0' as threshold_ratio, 'VEHICLE_POSITION_PASSAGE' as observation_method,
                   'CRITICAL' as severity, 'gap-1' as evidence_key, 'reliability_v1' as calculation_version
            union all
            select 'tisseo', '2026-01-01', 'R1', '0', 'S1', '2026-01-01T08:06:00+00:00',
                   'BUNCHING', '300', '100', '0.33', '0.5', 'VEHICLE_POSITION_PASSAGE',
                   'INFO', 'bunch-1', 'reliability_v1'
            """
        )
        connection.execute("create view v_headway_reliability_events as select * from fct_headway_reliability_events")
    pointer = {
        "schema_version": 1,
        "source": "tisseo",
        "serving_run_id": "serving-fixed",
        "database_path": "runs/serving-fixed/mobility_control_tower.duckdb",
        "serving_manifest_path": "runs/serving-fixed/serving_manifest.json",
        "dbt_gold_run_id": "dbt-fixed",
        "latest_included_realtime_snapshot": "snapshot-fixed",
        "quality_status": "passed",
        "generated_timestamp": "2026-01-01T07:55:00+00:00",
        "contract_version": 1,
    }
    (serving_root / "tisseo" / "current.json").write_text(json.dumps(pointer), encoding="utf-8")


def test_rule_loaders_generate_five_rule_families(tmp_path: Path) -> None:
    sources_config = tmp_path / "sources.yml"
    history_root = tmp_path / "history"
    serving_root = tmp_path / "serving"
    quality_root = tmp_path / "quality"
    write_sources_config(sources_config)
    write_snapshot(history_root, feed_type="trip_updates", collection_time="2026-01-01T07:59:00+00:00", feed_age_seconds=30)
    write_snapshot(history_root, feed_type="vehicle_positions", collection_time="2026-01-01T07:00:00+00:00", feed_age_seconds=3600)
    write_serving_db(serving_root)
    quality_root.mkdir()
    (quality_root / "latest_validation_summary.json").write_text(
        json.dumps(
            {
                "generated_timestamp": "2026-01-01T07:58:00+00:00",
                "success": False,
                "suite": "gold",
                "expectations_evaluated": 3,
                "expectations_failed": 1,
                "failed_expectations": [{"expectation_type": "expect_table_row_count_to_be_between"}],
            }
        ),
        encoding="utf-8",
    )
    engine = IncidentEvaluationEngine(
        repository=IncidentStore(tmp_path / "incidents").repository,
        serving_root=serving_root,
        history_root=history_root,
        quality_root=quality_root,
        sources_config=sources_config,
    )

    candidates = engine.load_candidates(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="rules")
    by_key = {item.candidate_key: item for item in candidates}

    assert by_key["stale_feed:tisseo:trip_updates"].candidate_state == CandidateState.HEALTHY
    assert by_key["stale_feed:tisseo:vehicle_positions"].suggested_severity == Severity.CRITICAL
    assert by_key["stale_feed:tisseo:service_alerts"].candidate_state == CandidateState.NOT_APPLICABLE
    assert by_key["stale_serving:tisseo"].candidate_state == CandidateState.HEALTHY
    assert by_key["quality_failure:tisseo:all"].suggested_severity == Severity.CRITICAL
    assert by_key["low_coverage:tisseo:route:R1:2026-01-01:am_peak"].suggested_severity == Severity.CRITICAL
    assert by_key["low_coverage:tisseo:route:R2:2026-01-01:am_peak"].candidate_state == CandidateState.NOT_ENOUGH_DATA
    assert "service_gap:tisseo:R1:0:S1:20260101T0805" in by_key
    assert all("bunch" not in key for key in by_key)


def test_evaluate_opens_rule_loader_candidates_and_second_run_is_noop(tmp_path: Path) -> None:
    sources_config = tmp_path / "sources.yml"
    history_root = tmp_path / "history"
    serving_root = tmp_path / "serving"
    quality_root = tmp_path / "quality"
    write_sources_config(sources_config)
    write_snapshot(history_root, feed_type="trip_updates", collection_time="2026-01-01T07:59:00+00:00", feed_age_seconds=30)
    write_snapshot(history_root, feed_type="vehicle_positions", collection_time="2026-01-01T07:00:00+00:00", feed_age_seconds=3600)
    write_serving_db(serving_root)
    quality_root.mkdir()
    (quality_root / "latest_validation_summary.json").write_text(
        json.dumps(
            {"generated_timestamp": "2026-01-01T07:58:00+00:00", "success": True, "suite": "all", "expectations_evaluated": 3, "expectations_failed": 0}
        ),
        encoding="utf-8",
    )
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(
        repository=store.repository,
        serving_root=serving_root,
        history_root=history_root,
        quality_root=quality_root,
        sources_config=sources_config,
    )

    first = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="same")
    second = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="same")

    assert first.opened_count == 4
    assert second.opened_count == 0
    assert len(store.list_incidents()) == 4
