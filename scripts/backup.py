"""Create a local backup bundle for operational state."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

BACKUP_ITEMS = [
    Path("config/sources.yml"),
    Path("data/incidents"),
    Path("data/watermarks"),
    Path("data/serving"),
    Path("data/quality/latest_validation_summary.json"),
    Path("data/lineage/status.json"),
]


def copy_item(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    if source.is_dir():
        shutil.copytree(source, destination / source.name, dirs_exist_ok=True)
    else:
        target = destination / source.parent / source.name if source.parent != Path(".") else destination / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return True


def main() -> None:
    run_id = datetime.now(timezone.utc).strftime("backup_%Y%m%dT%H%M%SZ")
    backup_dir = Path("data/backups") / run_id
    backup_dir.mkdir(parents=True, exist_ok=False)
    copied = []
    missing = []
    for item in BACKUP_ITEMS:
        if copy_item(item, backup_dir):
            copied.append(str(item))
        else:
            missing.append(str(item))
    manifest = {
        "schema_version": 1,
        "backup_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "copied": copied,
        "missing_optional": missing,
        "restore_command": f"python scripts/restore.py {backup_dir}",
    }
    (backup_dir / "backup_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(backup_dir))


if __name__ == "__main__":
    main()
