"""Run the dbt project with explicit input paths."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import PROJECT_ROOT, db_path, load_source


def build_dbt(static_run: Path, root: Path, *, database: Path | None = None) -> Path:
    database_path = database or db_path(root)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temp_directory = (root / "duckdb_tmp").resolve()
    temp_directory.mkdir(parents=True, exist_ok=True)
    realtime_root = root / "silver" / "realtime"
    source = load_source()
    variables = {
        "static_path": static_run.resolve().as_posix(),
        "realtime_path": realtime_root.resolve().as_posix(),
        "on_time_early_seconds": -60,
        "on_time_late_seconds": 300,
        "max_abs_delay_seconds": 7200,
        "min_reliable_sample_size": 5,
        "fresh_realtime_seconds": source.expected_realtime_freshness_seconds,
        "stale_realtime_seconds": source.stale_realtime_after_seconds,
    }
    environment = os.environ.copy()
    environment["MCT_DBT_DATABASE_PATH"] = str(database_path)
    environment["MCT_DBT_TEMP_DIRECTORY"] = temp_directory.as_posix()
    executable = shutil.which("dbt")
    if executable is None:
        candidate = Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
        if not candidate.is_file():
            raise FileNotFoundError("dbt executable not found; install the analytics dependency group")
        executable = str(candidate)
    subprocess.run(
        [
            executable,
            "build",
            "--threads",
            "1",
            "--project-dir",
            str(PROJECT_ROOT / "dbt"),
            "--profiles-dir",
            str(PROJECT_ROOT / "dbt"),
            "--vars",
            json.dumps(variables),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
    )
    return database_path
