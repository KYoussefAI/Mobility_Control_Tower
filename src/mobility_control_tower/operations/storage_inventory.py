"""Operational storage inventory and safe temporary cleanup helpers."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def inventory_storage(
    *,
    raw_history_root: Path = Path("data/raw_realtime/historical"),
    parsed_history_root: Path = Path("data/realtime_history"),
    serving_root: Path = Path("data/serving"),
) -> dict[str, Any]:
    committed = list(parsed_history_root.glob("*/trip_updates/date=*/hour=*/snapshot_timestamp=*/_SUCCESS"))
    incomplete = [
        path for path in parsed_history_root.glob("*/trip_updates/date=*/hour=*/snapshot_timestamp=*") if path.is_dir() and not (path / "_SUCCESS").is_file()
    ]
    snapshots = sorted(path.parent for path in committed)
    return {
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_history_size_bytes": _bytes(raw_history_root),
        "parsed_history_size_bytes": _bytes(parsed_history_root),
        "serving_size_bytes": _bytes(serving_root),
        "committed_snapshots": len(snapshots),
        "incomplete_snapshots": len(incomplete),
        "oldest_snapshot": str(snapshots[0]) if snapshots else None,
        "newest_snapshot": str(snapshots[-1]) if snapshots else None,
        "stale_temp_dirs": [str(path) for path in serving_root.glob("*/runs/.*.tmp")],
    }


def cleanup_stale_temp_dirs(root: Path, older_than_hours: int = 24) -> list[Path]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, older_than_hours))
    removed: list[Path] = []
    for temp_dir in root.glob("*/runs/.*.tmp"):
        if temp_dir.is_dir() and datetime.fromtimestamp(temp_dir.stat().st_mtime, timezone.utc) < cutoff:
            shutil.rmtree(temp_dir)
            removed.append(temp_dir)
    return removed
