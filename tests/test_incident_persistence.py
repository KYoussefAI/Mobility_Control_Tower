from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mobility_control_tower.incidents import (
    CandidateState,
    IncidentCandidate,
    IncidentEvaluationEngine,
    IncidentStore,
    Severity,
    default_rule_config,
    migrate_incident_store,
)

FIXED_TIME = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def candidate(
    key: str,
    *,
    state: CandidateState = CandidateState.UNHEALTHY,
    severity: Severity | None = Severity.WARNING,
    value: float | None = 100.0,
) -> IncidentCandidate:
    return IncidentCandidate(
        candidate_key=key,
        rule_id="stale_feed",
        rule_version="stale_feed_v1",
        source="tisseo",
        feed_type="trip_updates",
        entity_type="feed",
        entity_id="trip_updates",
        service_date="2026-01-01",
        period_start="2026-01-01T08:00:00+00:00",
        period_end="2026-01-01T09:00:00+00:00",
        observed_at=FIXED_TIME.isoformat(),
        metric_name="feed_age_seconds",
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
        evidence={"metric_value": value, "evidence_key": key},
    )


def test_incident_store_migration_is_durable_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "incidents"
    first = migrate_incident_store(root)
    second = migrate_incident_store(root)
    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert second["ending_schema_version"] == first["ending_schema_version"]
    assert IncidentStore(root).list_incidents() == []
    assert (root / "incidents.sqlite").is_file()


def test_incident_lifecycle_is_deduplicated_and_audited(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    key = "stale_feed:tisseo:trip_updates"

    opened = engine.apply_candidate(candidate(key), now=FIXED_TIME, correlation_id="corr-1")
    repeated = engine.apply_candidate(candidate(key), now=FIXED_TIME, correlation_id="corr-1")
    escalated = engine.apply_candidate(
        candidate(key, severity=Severity.CRITICAL, value=400.0),
        now=FIXED_TIME,
        correlation_id="corr-2",
    )
    acknowledged = store.transition(
        opened.incident_id or "",
        status="ACKNOWLEDGED",
        operator="operator",
        note="Seen",
    )
    monitoring = engine.apply_candidate(
        candidate(key, state=CandidateState.HEALTHY, severity=None, value=10.0),
        now=FIXED_TIME + timedelta(minutes=10),
        correlation_id="corr-3",
    )
    resolved = engine.apply_candidate(
        candidate(key, state=CandidateState.HEALTHY, severity=None, value=9.0),
        now=FIXED_TIME + timedelta(minutes=20),
        correlation_id="corr-4",
    )
    reopened = engine.apply_candidate(
        candidate(key, value=200.0),
        now=FIXED_TIME + timedelta(minutes=30),
        correlation_id="corr-5",
    )

    assert opened.action == "opened"
    assert repeated.action == "skipped"
    assert escalated.action == "escalated"
    assert acknowledged["status"] == "ACKNOWLEDGED"
    assert monitoring.event_type == "MONITORING_STARTED"
    assert resolved.event_type == "AUTO_RESOLVED"
    assert reopened.event_type == "REOPENED"
    assert store.get_by_id(opened.incident_id or "")["recurrence_count"] == 1
    assert (
        len(
            store.list_incidents(
                status="OPEN",
                source="tisseo",
                rule_id="stale_feed",
                severity="WARNING",
            )
        )
        == 1
    )
    assert store.list_incidents(status="RESOLVED") == []
    assert len(store.list_events(limit=2)) == 2


def test_suppression_expiry_reopens_an_unhealthy_incident(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    key = "stale_feed:tisseo:trip_updates"
    opened = engine.apply_candidate(candidate(key), now=FIXED_TIME, correlation_id="corr-1")
    store.transition(
        opened.incident_id or "",
        status="SUPPRESSED",
        operator="operator",
        note="Maintenance",
        suppress_until=(FIXED_TIME + timedelta(minutes=5)).isoformat(),
    )

    suppressed = engine.apply_candidate(
        candidate(key, value=200.0),
        now=FIXED_TIME + timedelta(minutes=1),
        correlation_id="corr-2",
    )
    expired = engine.apply_candidate(
        candidate(key, value=201.0),
        now=FIXED_TIME + timedelta(minutes=6),
        correlation_id="corr-3",
    )

    assert suppressed.action == "suppressed"
    assert expired.action == "updated"
    assert store.get_by_id(opened.incident_id or "")["status"] == "OPEN"
    assert any(event["event_type"] == "SUPPRESSION_EXPIRED" for event in store.list_events(opened.incident_id))


def test_invalid_transitions_and_missing_resolution_reason_fail(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)
    opened = engine.apply_candidate(
        candidate("stale_feed:tisseo:trip_updates"),
        now=FIXED_TIME,
        correlation_id="corr-1",
    )

    with pytest.raises(ValueError, match="Manual resolution requires"):
        store.transition(opened.incident_id or "", status="RESOLVED", operator="operator", note="")

    store.transition(
        opened.incident_id or "",
        status="RESOLVED",
        operator="operator",
        note="Fixed",
    )
    with pytest.raises(ValueError, match="Invalid incident transition"):
        store.transition(
            opened.incident_id or "",
            status="ACKNOWLEDGED",
            operator="operator",
            note="late",
        )


def test_evaluation_is_idempotent_and_dry_run_does_not_mutate(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")

    class FixedEngine(IncidentEvaluationEngine):
        def load_candidates(self, *, source, evaluation_time, correlation_id):  # type: ignore[no-untyped-def]
            return [candidate("stale_feed:tisseo:trip_updates")]

    engine = FixedEngine(repository=store.repository)
    first = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="retry")
    second = engine.evaluate(source="tisseo", evaluation_time=FIXED_TIME, correlation_id="retry")
    dry_run = engine.evaluate(
        source="tisseo",
        evaluation_time=FIXED_TIME,
        correlation_id="dry",
        dry_run=True,
    )

    assert first.opened_count == 1
    assert second.skipped_count == 1
    assert dry_run.dry_run is True
    assert len(store.list_incidents()) == 1
    assert len(store.list_evaluation_runs(source="tisseo")) == 2


def test_non_actionable_candidates_are_skipped_without_mutation(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(repository=store.repository)

    not_enough_data = engine.apply_candidate(
        candidate(
            "stale_feed:tisseo:trip_updates",
            state=CandidateState.NOT_ENOUGH_DATA,
            severity=None,
            value=None,
        ),
        now=FIXED_TIME,
        correlation_id="not-enough-data",
    )
    not_applicable = engine.apply_candidate(
        candidate(
            "stale_feed:tisseo:trip_updates",
            state=CandidateState.NOT_APPLICABLE,
            severity=None,
            value=None,
        ),
        now=FIXED_TIME,
        correlation_id="not-applicable",
    )

    assert not_enough_data.action == "skipped"
    assert not_applicable.action == "skipped"
    assert store.list_incidents() == []


def test_evaluation_lock_conflict_and_rule_configuration(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    assert store.repository.acquire_evaluation_lock("incidents:tisseo", "owner-a", FIXED_TIME)
    result = IncidentEvaluationEngine(repository=store.repository).evaluate(
        source="tisseo",
        evaluation_time=FIXED_TIME,
        correlation_id="locked",
    )
    store.repository.release_evaluation_lock("incidents:tisseo", "owner-a")

    config = default_rule_config()
    assert result.status == "SKIPPED_LOCKED"
    assert config.stale_feed.version == "stale_feed_v1"
    assert config.low_realtime_coverage.healthy_at_or_above_percentage > config.low_realtime_coverage.warning_below_percentage


def test_unknown_source_failure_is_recorded_and_releases_the_lock(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    engine = IncidentEvaluationEngine(
        repository=store.repository,
        sources_config=Path("config/sources.yml"),
    )

    with pytest.raises(ValueError, match="Unknown source"):
        engine.evaluate(
            source="missing",
            evaluation_time=FIXED_TIME,
            correlation_id="unknown-source",
        )

    runs = store.list_evaluation_runs(source="missing")
    assert len(runs) == 1
    assert runs[0]["status"] == "FAILED"
    assert "Unknown source" in runs[0]["error_summary"]
    assert store.repository.acquire_evaluation_lock("incidents:missing", "new-owner", FIXED_TIME)
