"""Restore a local backup bundle into a target root."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def restore(backup_dir: Path, target_root: Path = Path(".")) -> None:
    manifest_path = backup_dir / "backup_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Backup manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("copied", []):
        source = backup_dir / item
        if not source.exists():
            source = backup_dir / Path(item).name
        target = target_root / item
        if source.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(source, target)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/restore.py <backup-dir> [target-root]")
    restore(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else Path("."))
    print("restore complete")


if __name__ == "__main__":
    main()
