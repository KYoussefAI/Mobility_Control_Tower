"""Verify PostgreSQL incident backup, destructive reset, restore, and deduplication."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import requests

from mobility_control_tower.incidents import IncidentEvaluationEngine, IncidentStore, evaluation_result_to_dict
from mobility_control_tower.security import create_access_token

TABLES = ["schema_versions", "incidents", "incident_events", "incident_evaluation_runs"]


def _database_url() -> str:
    url = os.getenv("MCT_INCIDENT_DATABASE_URL")
    if not url:
        raise RuntimeError("MCT_INCIDENT_DATABASE_URL is required for PostgreSQL restore verification")
    return url


def _connect() -> Any:
    return psycopg2.connect(_database_url(), cursor_factory=psycopg2.extras.RealDictCursor)


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _pg_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return psycopg2.extras.Json(value)
    return value


def _backup(path: Path) -> dict[str, Any]:
    with _connect() as connection, connection.cursor() as cursor:
        payload = {}
        for table in TABLES:
            cursor.execute(f"SELECT * FROM {table} ORDER BY 1")
            payload[table] = [dict(row) for row in cursor.fetchall()]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    return payload


def _restore(payload: dict[str, list[dict[str, Any]]]) -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute("TRUNCATE incident_events, incident_evaluation_runs, incident_evaluation_locks, incidents, schema_versions")
        for table in TABLES:
            for row in payload.get(table, []):
                columns = list(row)
                placeholders = ", ".join(["%s"] * len(columns))
                cursor.execute(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                    [_pg_value(row[column]) for column in columns],
                )
        connection.commit()


def _counts() -> dict[str, int]:
    with _connect() as connection, connection.cursor() as cursor:
        counts = {}
        for table in TABLES:
            cursor.execute(f"SELECT count(*) AS count FROM {table}")
            counts[table] = int(cursor.fetchone()["count"])
        return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=f"http://127.0.0.1:{os.getenv('API_PORT', '8000')}")
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/restore-report.json"))
    parser.add_argument("--backup", type=Path, default=Path("artifacts/runtime/incident-postgres-backup.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if os.getenv("MCT_INCIDENT_BACKEND") != "postgres":
        raise RuntimeError("restore verification requires MCT_INCIDENT_BACKEND=postgres")
    store = IncidentStore()
    before_incidents = store.list_incidents(limit=200)
    before_events = store.list_events(limit=1000)
    if not before_incidents or not before_events:
        raise AssertionError("incident state is empty before restore test")
    if not any(incident["status"] == "ACKNOWLEDGED" for incident in before_incidents):
        raise AssertionError("expected acknowledged incident before restore")
    if not any(incident["status"] == "SUPPRESSED" for incident in before_incidents):
        raise AssertionError("expected suppressed incident before restore")
    backup_payload = _backup(args.backup)
    counts_before = _counts()
    _restore(backup_payload)
    counts_after = _counts()

    restored_store = IncidentStore()
    restored_incidents = restored_store.list_incidents(limit=200)
    restored_events = restored_store.list_events(limit=1000)
    if counts_before != counts_after:
        raise AssertionError(f"restore counts changed: before={counts_before} after={counts_after}")
    if len(restored_events) != len(before_events):
        raise AssertionError("event history count changed after restore")
    if not any(incident["status"] == "ACKNOWLEDGED" for incident in restored_incidents):
        raise AssertionError("acknowledged state was not restored")
    if not any(incident["status"] == "SUPPRESSED" and incident.get("suppression_expires_at") for incident in restored_incidents):
        raise AssertionError("suppression expiry was not restored")

    before_ids = {incident["incident_id"] for incident in restored_incidents}
    result = IncidentEvaluationEngine(repository=restored_store.repository).evaluate(
        evaluation_time=datetime.fromisoformat("2026-07-19T15:00:00+00:00"),
        correlation_id="restore-proof",
    )
    after_ids = {incident["incident_id"] for incident in restored_store.list_incidents(limit=200)}
    if not before_ids.issubset(after_ids):
        raise AssertionError("evaluation after restore removed incident records")

    token = create_access_token("restore-proof", {"operations:read"}, expires_in_seconds=900)
    api_response = requests.get(f"{args.api_url}/v1/incidents?limit=5", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    api_ready = requests.get(f"{args.api_url}/health/ready", timeout=15)
    api_response.raise_for_status()
    api_ready.raise_for_status()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend": "postgres",
        "counts_before": counts_before,
        "counts_after": counts_after,
        "incident_count": len(restored_incidents),
        "event_count": len(restored_events),
        "backup_file": str(args.backup),
        "evaluation_after_restore": evaluation_result_to_dict(result),
        "api_incident_status": api_response.status_code,
        "api_ready_status": api_ready.status_code,
        "status": "ok",
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
