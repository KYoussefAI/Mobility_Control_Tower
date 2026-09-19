from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from mobility_control_tower.incidents import PostgresIncidentRepository, _normalize_incident_payload

pytestmark = pytest.mark.skipif(not os.getenv("MCT_TEST_POSTGRES_URL"), reason="MCT_TEST_POSTGRES_URL is required")


def _clean(repository: PostgresIncidentRepository) -> None:
    with repository.transaction() as connection:
        connection.execute("TRUNCATE incident_events, incident_evaluation_runs, incident_evaluation_locks, incidents, schema_versions")
    repository.migrate()


def _incident(status: str = "OPEN") -> dict[str, object]:
    now = datetime(2026, 7, 19, 15, tzinfo=timezone.utc).isoformat()
    return {
        "incident_id": "pg-contract-incident",
        "deduplication_key": "pg-contract:tisseo:route:42",
        "rule_id": "low_realtime_coverage",
        "rule_version": "low_coverage_v1",
        "incident_type": "coverage",
        "source": "tisseo",
        "entity_type": "route",
        "entity_id": "42",
        "status": status,
        "severity": "WARNING",
        "title": "PostgreSQL contract incident",
        "summary": "Contract test incident.",
        "opened_at": now,
        "first_observed_at": now,
        "last_observed_at": now,
        "last_evaluated_at": now,
        "latest_evidence": {"metric_name": "coverage_percentage", "metric_value": 42},
        "created_at": now,
        "updated_at": now,
    }


def test_postgres_repository_contract() -> None:
    repository = PostgresIncidentRepository(os.environ["MCT_TEST_POSTGRES_URL"])
    _clean(repository)
    incident = _incident()
    with repository.transaction() as connection:
        repository.upsert_incident(connection, _normalize_incident_payload(incident))
        repository.append_event(
            connection,
            {
                "event_id": "pg-contract-opened",
                "incident_id": "pg-contract-incident",
                "event_type": "OPENED",
                "previous_status": None,
                "new_status": "OPEN",
                "previous_severity": None,
                "new_severity": "WARNING",
                "actor_type": "system",
                "actor_id": "contract",
                "reason": None,
                "evidence": {"metric_name": "coverage_percentage", "metric_value": 42},
                "rule_id": "low_realtime_coverage",
                "rule_version": "low_coverage_v1",
                "correlation_id": "pg-contract",
                "created_at": incident["created_at"],
            },
        )
    assert repository.schema_version() == 2
    assert repository.get_by_id("pg-contract-incident")["latest_evidence"]["metric_value"] == 42
    assert repository.get_active_by_deduplication_key("pg-contract:tisseo:route:42")["incident_id"] == "pg-contract-incident"
    assert len(repository.list_events("pg-contract-incident")) == 1

    with pytest.raises(RuntimeError):
        with repository.transaction() as connection:
            updated = dict(repository.get_by_id("pg-contract-incident"))
            updated["severity"] = "CRITICAL"
            repository.upsert_incident(connection, _normalize_incident_payload(updated))
            raise RuntimeError("force rollback")
    assert repository.get_by_id("pg-contract-incident")["severity"] == "WARNING"

    now = datetime(2026, 7, 19, 15, tzinfo=timezone.utc)
    assert repository.acquire_evaluation_lock("incidents:tisseo", "owner-a", now)
    assert not repository.acquire_evaluation_lock("incidents:tisseo", "owner-b", now)
    repository.release_evaluation_lock("incidents:tisseo", "owner-a")
    assert repository.acquire_evaluation_lock("incidents:tisseo", "owner-b", now)
