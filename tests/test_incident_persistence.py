from pathlib import Path

from mobility_control_tower.incidents import IncidentStore, migrate_incident_store


def test_incident_store_migration_is_durable_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "incidents"
    first = migrate_incident_store(root)
    second = migrate_incident_store(root)
    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert second["ending_schema_version"] == first["ending_schema_version"]
    assert IncidentStore(root).list_incidents() == []
    assert (root / "incidents.sqlite").is_file()
