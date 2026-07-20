"""Verify that backup and restore preserve key operational state."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from mobility_control_tower.api.app import create_app
from mobility_control_tower.incidents import IncidentStore
from mobility_control_tower.security import create_access_token


def seed_incident_state() -> dict[str, str]:
    store = IncidentStore()
    active = store.open_or_update(
        incident_type="STALE_FEED",
        source="restore_check",
        entity_type="feed",
        entity_id="trip_updates",
        severity="WARNING",
        title="Restore check active incident",
        summary="Seeded incident for backup and restore verification.",
        evidence={"metric_name": "feed_age_seconds", "metric_value": 120, "evidence_key": "restore-active"},
        rule_id="stale_feed",
        rule_version="stale_feed_v1",
        deduplication_key="stale_feed:restore_check:trip_updates",
    )
    acknowledged = store.open_or_update(
        incident_type="LOW_COVERAGE",
        source="restore_check",
        entity_type="network",
        entity_id="network",
        severity="CRITICAL",
        title="Restore check acknowledged incident",
        summary="Seeded acknowledged incident for backup and restore verification.",
        evidence={"metric_name": "coverage_percentage", "metric_value": 40, "evidence_key": "restore-ack"},
        rule_id="low_realtime_coverage",
        rule_version="low_coverage_v1",
        deduplication_key="low_coverage:restore_check:network:2026-01-01:am_peak",
    )
    store.transition(acknowledged["incident_id"], status="ACKNOWLEDGED", operator="restore-verifier", note="Seed acknowledgement")
    suppressed = store.open_or_update(
        incident_type="STALE_SERVING_ARTIFACT",
        source="restore_check",
        entity_type="serving_artifact",
        entity_id="current",
        severity="WARNING",
        title="Restore check suppressed incident",
        summary="Seeded suppressed incident for backup and restore verification.",
        evidence={"metric_name": "artifact_age_seconds", "metric_value": 1300, "evidence_key": "restore-suppressed"},
        rule_id="stale_serving_artifact",
        rule_version="stale_serving_v1",
        deduplication_key="stale_serving:restore_check",
    )
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    store.transition(suppressed["incident_id"], status="SUPPRESSED", operator="restore-verifier", note="Seed suppression", suppress_until=expiry)
    return {"active": active["incident_id"], "acknowledged": acknowledged["incident_id"], "suppressed": suppressed["incident_id"], "suppression_expiry": expiry}


def main() -> int:
    seeded = seed_incident_state()
    result = subprocess.run([sys.executable, "scripts/backup.py"], check=True, capture_output=True, text=True)
    backup_dir = Path(result.stdout.strip().splitlines()[-1])
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "restore"
        target.mkdir()
        subprocess.run([sys.executable, "scripts/restore.py", str(backup_dir), str(target)], check=True)
        manifest = json.loads((backup_dir / "backup_manifest.json").read_text(encoding="utf-8"))
        if "config/sources.yml" not in manifest.get("copied", []):
            print("restore verification failed: source registry was not backed up")
            return 1
        if not (target / "config/sources.yml").is_file():
            print("restore verification failed: source registry not restored")
            return 1
        if (target / "data/serving").exists():
            current_files = list((target / "data/serving").glob("*/current.json"))
            for pointer in current_files:
                json.loads(pointer.read_text(encoding="utf-8"))
        restored_store = IncidentStore(target / "data/incidents")
        active = restored_store.get_by_id(seeded["active"])
        acknowledged = restored_store.get_by_id(seeded["acknowledged"])
        suppressed = restored_store.get_by_id(seeded["suppressed"])
        if active is None or active["status"] not in {"OPEN", "ACKNOWLEDGED", "MONITORING"}:
            print("restore verification failed: active incident was not restored")
            return 1
        if acknowledged is None or acknowledged["status"] != "ACKNOWLEDGED":
            print("restore verification failed: acknowledged incident state was not preserved")
            return 1
        if len(restored_store.list_events(seeded["acknowledged"])) < 2:
            print("restore verification failed: incident event history was incomplete")
            return 1
        if suppressed is None or suppressed["suppression_expires_at"] != seeded["suppression_expiry"]:
            print("restore verification failed: suppression expiry was not preserved")
            return 1
        before_count = len(restored_store.list_incidents(source="restore_check", limit=100))
        restored_store.open_or_update(
            incident_type="STALE_FEED",
            source="restore_check",
            entity_type="feed",
            entity_id="trip_updates",
            severity="WARNING",
            title="Restore check active incident",
            summary="Repeated evidence after restore.",
            evidence={"metric_name": "feed_age_seconds", "metric_value": 120, "evidence_key": "restore-active"},
            rule_id="stale_feed",
            rule_version="stale_feed_v1",
            deduplication_key="stale_feed:restore_check:trip_updates",
        )
        after_count = len(restored_store.list_incidents(source="restore_check", limit=100))
        if before_count != after_count:
            print("restore verification failed: evaluation after restore did not deduplicate")
            return 1
        import mobility_control_tower.api.routes as route_module

        route_module.IncidentStore = lambda: restored_store
        token = create_access_token("restore-verifier", {"operations:read"}, expires_in_seconds=60)
        response = TestClient(create_app(None)).get(f"/v1/incidents/{seeded['active']}", headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            print("restore verification failed: API could not read restored incident state")
            return 1
    if Path("data/backups").is_dir():
        for temp_backup in Path("data/backups").glob("backup_*"):
            if temp_backup == backup_dir:
                shutil.rmtree(temp_backup, ignore_errors=True)
    print("backup/restore verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
