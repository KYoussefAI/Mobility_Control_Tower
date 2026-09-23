from pathlib import Path

import yaml


def test_release_proof_workflow_and_recovery_gates_are_real() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert "release-proof" in jobs
    rendered = str(jobs["release-proof"])
    for command in ("docker build", "verify_production_overlay.py", "promtool", "verify_restore.py"):
        assert command in rendered
    for path in ("scripts/backup.py", "scripts/restore.py", "docs/backup_recovery.md", "deploy/production.compose.yml"):
        assert Path(path).is_file()
