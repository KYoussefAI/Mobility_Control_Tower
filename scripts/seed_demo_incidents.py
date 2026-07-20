"""Seed deterministic operator incident states for runtime demos.

The evaluator remains authoritative for automated rule transitions. This script
adds stable operator-state examples so browser, backup, restore, and screenshot
evidence always have active, acknowledged, resolved, and suppressed incidents.
It is idempotent by deterministic incident IDs and event IDs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from mobility_control_tower.incidents import IncidentStore, _normalize_incident_payload

FIXTURE_TIME = "2026-07-19T15:00:00+00:00"
FIXTURE_END = "2026-07-19T16:00:00+00:00"
SUPPRESSION_EXPIRY = "2026-07-20T15:00:00+00:00"


def _incident(
    *,
    incident_id: str,
    deduplication_key: str,
    rule_id: str,
    incident_type: str,
    status: str,
    severity: str,
    title: str,
    summary: str,
    entity_type: str,
    entity_id: str | None = None,
    acknowledged_by: str | None = None,
    resolved_by: str | None = None,
    suppressed_by: str | None = None,
    suppression_expires_at: str | None = None,
) -> dict[str, Any]:
    evidence = {
        "fixture_version": "release-proof-v1",
        "source": "tisseo",
        "metric_name": rule_id,
        "metric_value": 1,
        "serving_run_id": "deterministic-demo-serving",
        "calculation_version": "fixture_v1",
    }
    return {
        "incident_id": incident_id,
        "deduplication_key": deduplication_key,
        "rule_id": rule_id,
        "rule_version": f"{rule_id}_v1",
        "incident_type": incident_type,
        "source": "tisseo",
        "feed_type": None,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "service_date": "2024-01-15",
        "operational_period_start": FIXTURE_TIME,
        "operational_period_end": FIXTURE_END,
        "status": status,
        "severity": severity,
        "title": title,
        "summary": summary,
        "opened_at": FIXTURE_TIME,
        "first_observed_at": FIXTURE_TIME,
        "last_observed_at": FIXTURE_TIME,
        "last_evaluated_at": FIXTURE_TIME,
        "healthy_since": FIXTURE_TIME if status == "RESOLVED" else None,
        "healthy_observation_count": 2 if status == "RESOLVED" else 0,
        "acknowledged_at": FIXTURE_TIME if acknowledged_by else None,
        "acknowledged_by": acknowledged_by,
        "resolved_at": FIXTURE_TIME if resolved_by else None,
        "resolved_by": resolved_by,
        "suppressed_at": FIXTURE_TIME if suppressed_by else None,
        "suppressed_by": suppressed_by,
        "suppression_expires_at": suppression_expires_at,
        "manual_resolution": bool(resolved_by),
        "manual_resolution_note": "Demo route recovered after validation." if resolved_by else None,
        "occurrence_count": 1,
        "recurrence_count": 0,
        "evidence_version": 1,
        "latest_evidence": evidence,
        "evidence_fingerprint": json.dumps(evidence, sort_keys=True),
        "calculation_version": "fixture_v1",
        "serving_run_id": "deterministic-demo-serving",
        "correlation_id": "demo-seed",
        "created_at": FIXTURE_TIME,
        "updated_at": FIXTURE_TIME,
    }


def _event(
    incident: dict[str, Any], event_type: str, suffix: str, *, previous_status: str | None, new_status: str, reason: str | None = None
) -> dict[str, Any]:
    return {
        "event_id": f"{incident['incident_id']}-{suffix}",
        "incident_id": incident["incident_id"],
        "event_type": event_type,
        "previous_status": previous_status,
        "new_status": new_status,
        "previous_severity": incident["severity"],
        "new_severity": incident["severity"],
        "actor_type": "operator" if event_type in {"ACKNOWLEDGED", "MANUALLY_RESOLVED", "SUPPRESSED"} else "system",
        "actor_id": "demo-operator" if event_type in {"ACKNOWLEDGED", "MANUALLY_RESOLVED", "SUPPRESSED"} else "incident-evaluator",
        "reason": reason,
        "evidence": json.dumps(incident["latest_evidence"], sort_keys=True),
        "rule_id": incident["rule_id"],
        "rule_version": incident["rule_version"],
        "correlation_id": "demo-seed",
        "created_at": FIXTURE_TIME,
    }


def main() -> None:
    store = IncidentStore()
    repository = store.repository
    incidents = [
        _incident(
            incident_id="demo-active-low-coverage",
            deduplication_key="low_coverage:tisseo:route:demo-low-coverage:2024-01-15:day",
            rule_id="low_realtime_coverage",
            incident_type="coverage",
            status="OPEN",
            severity="WARNING",
            title="Route 42 realtime coverage below target",
            summary="Deterministic route coverage fixture is below the warning threshold.",
            entity_type="route",
            entity_id="demo-low-coverage",
        ),
        _incident(
            incident_id="demo-ack-stale-feed",
            deduplication_key="stale_feed:tisseo:trip_updates",
            rule_id="stale_feed",
            incident_type="feed_freshness",
            status="ACKNOWLEDGED",
            severity="CRITICAL",
            title="Trip Updates feed is critically stale",
            summary="Demo operator has acknowledged the stale Trip Updates condition.",
            entity_type="feed",
            entity_id="trip_updates",
            acknowledged_by="demo-operator",
        ),
        _incident(
            incident_id="demo-resolved-service-gap",
            deduplication_key="service_gap:tisseo:demo-route:0:demo-stop:2026-07-19T15",
            rule_id="severe_service_gap",
            incident_type="service_gap",
            status="RESOLVED",
            severity="CRITICAL",
            title="Severe service gap recovered",
            summary="A deterministic severe service gap has a complete resolution audit trail.",
            entity_type="route",
            entity_id="demo-route",
            resolved_by="demo-operator",
        ),
        _incident(
            incident_id="demo-suppressed-serving",
            deduplication_key="stale_serving:tisseo",
            rule_id="stale_serving_artifact",
            incident_type="serving_freshness",
            status="SUPPRESSED",
            severity="WARNING",
            title="Serving artifact freshness suppressed for maintenance",
            summary="A deterministic serving freshness incident is temporarily suppressed.",
            entity_type="source",
            entity_id="tisseo",
            suppressed_by="demo-operator",
            suppression_expires_at=SUPPRESSION_EXPIRY,
        ),
    ]
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for incident in incidents:
        if repository.get_by_id(incident["incident_id"]):
            continue
        with repository.transaction() as connection:
            repository.upsert_incident(connection, _normalize_incident_payload(incident))
            repository.append_event(connection, _event(incident, "OPENED", "opened", previous_status=None, new_status="OPEN"))
            if incident["status"] == "ACKNOWLEDGED":
                repository.append_event(
                    connection, _event(incident, "ACKNOWLEDGED", "ack", previous_status="OPEN", new_status="ACKNOWLEDGED", reason="Demo acknowledgement.")
                )
            if incident["status"] == "RESOLVED":
                repository.append_event(
                    connection,
                    _event(
                        incident,
                        "MANUALLY_RESOLVED",
                        "resolved",
                        previous_status="OPEN",
                        new_status="RESOLVED",
                        reason="Demo route recovered after validation.",
                    ),
                )
            if incident["status"] == "SUPPRESSED":
                repository.append_event(
                    connection, _event(incident, "SUPPRESSED", "suppressed", previous_status="OPEN", new_status="SUPPRESSED", reason="Demo maintenance window.")
                )
        inserted += 1
    print(json.dumps({"status": "ok", "inserted": inserted, "generated_at": now}, sort_keys=True))


if __name__ == "__main__":
    main()
