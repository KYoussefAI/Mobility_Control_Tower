# mct_solo — Complete Project Context

> GPT/LLM-oriented snapshot of the project’s real software system.
> Included files are reproduced as text below. Generated data, dependencies,
> secrets, caches, binaries, package metadata, and runtime artifacts are intentionally omitted.

## Snapshot Metadata

- **Project:** `mct_solo`
- **Generated:** `2026-09-25T13:40:46+00:00`
- **Exporter:** `to_md v2.1`
- **Included files:** `88`
- **Included source size:** `116,728 bytes`
- **Approximate source tokens:** `~29,182` (very rough estimate)
- **Snapshot file:** `mct_solo.md`

## How GPT Should Interpret This Snapshot

- Treat included source/config/test files as the primary evidence of actual behavior.
- Documentation may be stale; compare documentation claims against implementation and tests.
- Omitted paths are primarily generated/runtime/dependency/data noise, not hidden application logic.
- The repository tree below shows only files whose contents are embedded in this snapshot.

## Detected Architecture Signals

- Docker / Compose
- Airflow / DAG orchestration
- dbt / analytical modelling
- Dashboard / UI
- CI/CD
- SQL
- Automated tests

## Included Repository Tree

```text
mct_solo/
├── .dockerignore
├── .env.example
├── .github
│   └── workflows
│       └── ci.yml
├── .gitignore
├── airflow
│   └── dags
│       ├── realtime_pipeline.py
│       └── static_gtfs_pipeline.py
├── config
│   └── source.yml
├── dashboard
│   └── app.py
├── data
│   ├── ci
│   │   ├── bronze
│   │   │   └── static
│   │   │       └── 20260101T120000000000Z
│   │   │           ├── calendar.txt
│   │   │           ├── calendar_dates.txt
│   │   │           ├── manifest.json
│   │   │           ├── routes.txt
│   │   │           ├── stop_times.txt
│   │   │           ├── stops.txt
│   │   │           └── trips.txt
│   │   ├── raw
│   │   │   ├── realtime
│   │   │   │   └── date=2026-01-01
│   │   │   │       └── 1767268770-7f86c755c925
│   │   │   │           └── _SUCCESS
│   │   │   └── static
│   │   │       └── 20260101T120000000000Z
│   │   │           └── _SUCCESS
│   │   └── silver
│   │       └── static
│   │           └── 20260101T120000000000Z
│   │               └── manifest.json
│   ├── ci-dbt111
│   │   ├── bronze
│   │   │   └── static
│   │   │       └── 20260101T120000000000Z
│   │   │           ├── calendar.txt
│   │   │           ├── calendar_dates.txt
│   │   │           ├── manifest.json
│   │   │           ├── routes.txt
│   │   │           ├── stop_times.txt
│   │   │           ├── stops.txt
│   │   │           └── trips.txt
│   │   ├── raw
│   │   │   ├── realtime
│   │   │   │   └── date=2026-01-01
│   │   │   │       └── 1767268770-7f86c755c925
│   │   │   │           └── _SUCCESS
│   │   │   └── static
│   │   │       └── 20260101T120000000000Z
│   │   │           └── _SUCCESS
│   │   └── silver
│   │       └── static
│   │           └── 20260101T120000000000Z
│   │               └── manifest.json
│   └── real-smoke
│       ├── bronze
│       │   └── static
│       │       └── 20260923T225641454289Z
│       │           ├── calendar.txt
│       │           ├── manifest.json
│       │           └── routes.txt
│       ├── raw
│       │   ├── realtime
│       │   │   └── date=2026-09-23
│       │   │       ├── 1790204219-865715567f81
│       │   │       │   └── _SUCCESS
│       │   │       └── 1790204350-9631d56a7f41
│       │   │           └── _SUCCESS
│       │   └── static
│       │       └── 20260923T225641454289Z
│       │           └── _SUCCESS
│       └── silver
│           └── static
│               └── 20260923T225641454289Z
│                   └── manifest.json
├── dbt
│   ├── dbt_project.yml
│   ├── models
│   │   ├── intermediate
│   │   │   ├── int_delay_observations.sql
│   │   │   ├── int_scheduled_trips.sql
│   │   │   ├── int_service_dates.sql
│   │   │   ├── schema.yml
│   │   │   └── unit_tests.yml
│   │   ├── marts
│   │   │   ├── feed_freshness.sql
│   │   │   ├── hourly_delay_summary.sql
│   │   │   ├── network_on_time_performance.sql
│   │   │   ├── realtime_coverage.sql
│   │   │   ├── route_daily_service.sql
│   │   │   ├── route_delay_summary.sql
│   │   │   └── schema.yml
│   │   └── staging
│   │       ├── schema.yml
│   │       ├── stg_calendar.sql
│   │       ├── stg_calendar_dates.sql
│   │       ├── stg_feed_snapshots.sql
│   │       ├── stg_realtime_updates.sql
│   │       ├── stg_routes.sql
│   │       ├── stg_stop_times.sql
│   │       └── stg_trips.sql
│   ├── profiles.yml
│   └── tests
│       ├── assert_coverage_reconciles.sql
│       ├── assert_delay_within_sanity_bound.sql
│       ├── assert_known_observations_reconcile.sql
│       ├── assert_percentages_in_range.sql
│       └── assert_sample_size_status_matches_count.sql
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── PROJECT_PLAN.md
├── pyproject.toml
├── README.md
├── scripts
│   └── create_ci_fixture.py
├── src
│   └── mct_solo
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── dbt.py
│       ├── io.py
│       ├── quality.py
│       ├── realtime_pipeline.py
│       └── static_pipeline.py
└── tests
    ├── conftest.py
    ├── fixtures
    │   └── static
    │       ├── calendar.txt
    │       ├── calendar_dates.txt
    │       ├── routes.txt
    │       ├── stop_times.txt
    │       ├── stops.txt
    │       └── trips.txt
    ├── test_cli_and_dbt.py
    ├── test_quality.py
    ├── test_realtime_pipeline.py
    └── test_static_pipeline.py
```

## File Index

### Project Root / Configuration

- `.dockerignore`
- `.env.example`
- `.gitignore`
- `Makefile`
- `pyproject.toml`

### Configuration

- `config/source.yml`

### Application Source

- `src/mct_solo/__init__.py`
- `src/mct_solo/cli.py`
- `src/mct_solo/config.py`
- `src/mct_solo/dbt.py`
- `src/mct_solo/io.py`
- `src/mct_solo/quality.py`
- `src/mct_solo/realtime_pipeline.py`
- `src/mct_solo/static_pipeline.py`

### Data Models / SQL / dbt

- `dbt/dbt_project.yml`
- `dbt/models/intermediate/int_delay_observations.sql`
- `dbt/models/intermediate/int_scheduled_trips.sql`
- `dbt/models/intermediate/int_service_dates.sql`
- `dbt/models/intermediate/schema.yml`
- `dbt/models/intermediate/unit_tests.yml`
- `dbt/models/marts/feed_freshness.sql`
- `dbt/models/marts/hourly_delay_summary.sql`
- `dbt/models/marts/network_on_time_performance.sql`
- `dbt/models/marts/realtime_coverage.sql`
- `dbt/models/marts/route_daily_service.sql`
- `dbt/models/marts/route_delay_summary.sql`
- `dbt/models/marts/schema.yml`
- `dbt/models/staging/schema.yml`
- `dbt/models/staging/stg_calendar.sql`
- `dbt/models/staging/stg_calendar_dates.sql`
- `dbt/models/staging/stg_feed_snapshots.sql`
- `dbt/models/staging/stg_realtime_updates.sql`
- `dbt/models/staging/stg_routes.sql`
- `dbt/models/staging/stg_stop_times.sql`
- `dbt/models/staging/stg_trips.sql`
- `dbt/profiles.yml`
- `dbt/tests/assert_coverage_reconciles.sql`
- `dbt/tests/assert_delay_within_sanity_bound.sql`
- `dbt/tests/assert_known_observations_reconcile.sql`
- `dbt/tests/assert_percentages_in_range.sql`
- `dbt/tests/assert_sample_size_status_matches_count.sql`

### Orchestration

- `airflow/dags/realtime_pipeline.py`
- `airflow/dags/static_gtfs_pipeline.py`

### Infrastructure / CI / Deployment / Observability

- `.github/workflows/ci.yml`
- `docker-compose.yml`
- `Dockerfile`

### Tests

- `tests/conftest.py`
- `tests/fixtures/static/calendar.txt`
- `tests/fixtures/static/calendar_dates.txt`
- `tests/fixtures/static/routes.txt`
- `tests/fixtures/static/stop_times.txt`
- `tests/fixtures/static/stops.txt`
- `tests/fixtures/static/trips.txt`
- `tests/test_cli_and_dbt.py`
- `tests/test_quality.py`
- `tests/test_realtime_pipeline.py`
- `tests/test_static_pipeline.py`

### Scripts / Tooling

- `scripts/create_ci_fixture.py`

### Documentation

- `PROJECT_PLAN.md`
- `README.md`

### Other System Files

- `dashboard/app.py`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/calendar.txt`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/calendar_dates.txt`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/manifest.json`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/routes.txt`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/stop_times.txt`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/stops.txt`
- `data/ci-dbt111/bronze/static/20260101T120000000000Z/trips.txt`
- `data/ci-dbt111/raw/realtime/date=2026-01-01/1767268770-7f86c755c925/_SUCCESS`
- `data/ci-dbt111/raw/static/20260101T120000000000Z/_SUCCESS`
- `data/ci-dbt111/silver/static/20260101T120000000000Z/manifest.json`
- `data/ci/bronze/static/20260101T120000000000Z/calendar.txt`
- `data/ci/bronze/static/20260101T120000000000Z/calendar_dates.txt`
- `data/ci/bronze/static/20260101T120000000000Z/manifest.json`
- `data/ci/bronze/static/20260101T120000000000Z/routes.txt`
- `data/ci/bronze/static/20260101T120000000000Z/stop_times.txt`
- `data/ci/bronze/static/20260101T120000000000Z/stops.txt`
- `data/ci/bronze/static/20260101T120000000000Z/trips.txt`
- `data/ci/raw/realtime/date=2026-01-01/1767268770-7f86c755c925/_SUCCESS`
- `data/ci/raw/static/20260101T120000000000Z/_SUCCESS`
- `data/ci/silver/static/20260101T120000000000Z/manifest.json`
- `data/real-smoke/bronze/static/20260923T225641454289Z/calendar.txt`
- `data/real-smoke/bronze/static/20260923T225641454289Z/manifest.json`
- `data/real-smoke/bronze/static/20260923T225641454289Z/routes.txt`
- `data/real-smoke/raw/realtime/date=2026-09-23/1790204219-865715567f81/_SUCCESS`
- `data/real-smoke/raw/realtime/date=2026-09-23/1790204350-9631d56a7f41/_SUCCESS`
- `data/real-smoke/raw/static/20260923T225641454289Z/_SUCCESS`
- `data/real-smoke/silver/static/20260923T225641454289Z/manifest.json`

# Complete File Contents

## Project Root / Configuration

### 1. `.dockerignore`

**File size:** `110` bytes

```
.git
.venv
__pycache__
.pytest_cache
.ruff_cache
.mypy_cache
.coverage
data
dbt/target
dbt/logs
airflow/logs
```

### 2. `.env.example`

**File size:** `165` bytes

```
MCT_DATA_ROOT=/opt/mct/data
MCT_DBT_DATABASE_PATH=/opt/mct/data/mart/mobility_control_tower.duckdb
AIRFLOW_HOME=/opt/mct/airflow
AIRFLOW__CORE__LOAD_EXAMPLES=False
```

### 3. `.gitignore`

**File size:** `228` bytes

```
.venv/
*.egg-info/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/
.env
data/
dbt/target/
dbt/logs/
dbt/dbt_packages/
dbt/.user.yml
airflow/logs/
airflow/airflow.db
airflow/webserver_config.py
```

### 4. `Makefile`

**File size:** `556` bytes

```makefile
.PHONY: install format lint test fixture dbt-build dashboard compose-up

install:
	python -m pip install -e ".[dev,analytics]"

format:
	isort .
	black .
	ruff check . --fix

lint:
	ruff check .
	black --check .
	isort --check-only .
	mypy src

test:
	coverage run -m pytest
	coverage report --fail-under=80

fixture:
	python scripts/create_ci_fixture.py data/ci

dbt-build:
	mct --data-root data/ci dbt-build --static-run data/ci/silver/static/20260101T120000000000Z

dashboard:
	streamlit run dashboard/app.py

compose-up:
	docker compose up --build -d
```

### 5. `pyproject.toml`

**File size:** `1,456` bytes

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "mct-solo"
version = "0.1.0"
description = "A compact Tisséo schedule-versus-realtime data engineering portfolio project"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "duckdb>=1.1,<2",
  "gtfs-realtime-bindings>=1.0,<2",
  "pandas>=2.2,<3",
  "pyarrow>=17,<22",
  "PyYAML>=6,<7",
  "requests>=2.32,<3",
  "streamlit>=1.40,<2",
]

[project.optional-dependencies]
analytics = ["dbt-core>=1.11,<1.12", "dbt-duckdb>=1.11,<1.12"]
orchestration = ["apache-airflow>=2.10,<3"]
dev = [
  "black>=24.10,<26",
  "coverage[toml]>=7.6,<8",
  "isort>=5.13,<7",
  "mypy>=1.13,<2",
  "pytest>=8.3,<9",
  "ruff>=0.8,<1",
  "types-PyYAML>=6",
  "types-requests>=2",
]

[project.scripts]
mct = "mct_solo.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.black]
line-length = 120
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 120

[tool.ruff]
line-length = 120
target-version = "py311"
exclude = ["data", "dbt/target", "airflow/logs"]

[tool.ruff.lint]
select = ["B", "E", "F", "I", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
check_untyped_defs = true
packages = ["mct_solo"]

[tool.coverage.run]
branch = true
source = ["mct_solo"]

[tool.coverage.report]
show_missing = true
skip_empty = true
```

## Configuration

### 6. `config/source.yml`

**File size:** `461` bytes

```yaml
source:
  id: tisseo
  name: "Tisséo — Toulouse"
  timezone: Europe/Paris
  licence: ODbL
  source_page: https://transport.data.gouv.fr/datasets/tisseo-reseau-transport-urbain-toulousain
  gtfs_url: https://data.toulouse-metropole.fr/explore/dataset/tisseo-gtfs/files/fc1dda89077cf37e4f7521760e0ef4e9/download/
  trip_updates_url: https://api.tisseo.fr/opendata/gtfsrt/GtfsRt.pb
  expected_realtime_freshness_seconds: 90
  stale_realtime_after_seconds: 300
```

## Application Source

### 7. `src/mct_solo/__init__.py`

**File size:** `66` bytes

```python
"""Mobility Control Tower solo project."""

__version__ = "0.1.0"
```

### 8. `src/mct_solo/cli.py`

**File size:** `3,985` bytes

```python
"""Small command-line interface used by developers and Airflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import data_root, latest_run, load_source
from .dbt import build_dbt
from .quality import require_pass, validate_realtime, validate_static
from .realtime_pipeline import download_realtime, ensure_empty_realtime_tables
from .static_pipeline import download_static, transform_static


def _static_pipeline(root: Path, *, run_dbt: bool = True) -> dict[str, str]:
    source = load_source()
    raw = download_static(source, root)
    silver = transform_static(raw, root)
    ensure_empty_realtime_tables(root)
    report_path = root / "quality" / f"static-{silver.name}.json"
    require_pass(validate_static(silver, report_path))
    database = build_dbt(silver, root) if run_dbt else None
    return {"raw_run": str(raw), "silver_run": str(silver), "database": str(database) if database else "not-run"}


def _realtime_pipeline(root: Path, *, run_dbt: bool = True) -> dict[str, object]:
    source = load_source()
    metadata = download_realtime(source, root)
    report_path = root / "quality" / "realtime-latest.json"
    require_pass(validate_realtime(root, report_path))
    static_run = latest_run(root / "silver" / "static")
    database = build_dbt(static_run, root) if run_dbt else None
    return {**metadata, "database": str(database) if database else "not-run"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="mct", description="Tisséo Mobility Control Tower pipelines")
    result.add_argument("--data-root", type=Path, default=data_root())
    subparsers = result.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ingest-static", help="Download and preserve one GTFS archive")
    transform = subparsers.add_parser("transform-static", help="Build Bronze and Silver from a raw run")
    transform.add_argument("raw_run", type=Path)
    subparsers.add_parser("collect-realtime", help="Fetch and preserve one Trip Updates snapshot")
    quality = subparsers.add_parser("quality", help="Run focused Python checks")
    quality.add_argument("layer", choices=("static", "realtime"))
    build = subparsers.add_parser("dbt-build", help="Build and test dbt Gold marts")
    build.add_argument("--static-run", type=Path)
    static = subparsers.add_parser("static-pipeline", help="Run the complete static workflow")
    static.add_argument("--skip-dbt", action="store_true")
    realtime = subparsers.add_parser("realtime-pipeline", help="Run one complete realtime poll")
    realtime.add_argument("--skip-dbt", action="store_true")
    return result


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    root: Path = args.data_root.resolve()
    source = load_source()
    if args.command == "ingest-static":
        output: object = {"raw_run": str(download_static(source, root))}
    elif args.command == "transform-static":
        output = {"silver_run": str(transform_static(args.raw_run.resolve(), root))}
    elif args.command == "collect-realtime":
        output = download_realtime(source, root)
    elif args.command == "quality":
        report = (
            validate_static(latest_run(root / "silver" / "static"))
            if args.layer == "static"
            else validate_realtime(root)
        )
        require_pass(report)
        output = report
    elif args.command == "dbt-build":
        static_run = args.static_run.resolve() if args.static_run else latest_run(root / "silver" / "static")
        ensure_empty_realtime_tables(root)
        output = {"database": str(build_dbt(static_run, root))}
    elif args.command == "static-pipeline":
        output = _static_pipeline(root, run_dbt=not args.skip_dbt)
    else:
        output = _realtime_pipeline(root, run_dbt=not args.skip_dbt)
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
```

### 9. `src/mct_solo/config.py`

**File size:** `1,321` bytes

```python
"""Small, single-source project configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    timezone: str
    licence: str
    source_page: str
    gtfs_url: str
    trip_updates_url: str
    expected_realtime_freshness_seconds: int
    stale_realtime_after_seconds: int


def load_source(path: Path | None = None) -> SourceConfig:
    config_path = path or PROJECT_ROOT / "config" / "source.yml"
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))["source"]
    return SourceConfig(**raw)


def data_root() -> Path:
    return Path(os.environ.get("MCT_DATA_ROOT", PROJECT_ROOT / "data")).resolve()


def db_path(root: Path | None = None) -> Path:
    default = (root or data_root()) / "mart" / "mobility_control_tower.duckdb"
    return Path(os.environ.get("MCT_DBT_DATABASE_PATH", default)).resolve()


def latest_run(parent: Path) -> Path:
    runs = sorted(path for path in parent.glob("*") if path.is_dir() and (path / "manifest.json").is_file())
    if not runs:
        raise FileNotFoundError(f"No completed run found under {parent}")
    return runs[-1]
```

### 10. `src/mct_solo/dbt.py`

**File size:** `1,541` bytes

```python
"""Run the compact dbt project with explicit input paths."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import PROJECT_ROOT, db_path


def build_dbt(static_run: Path, root: Path, *, database: Path | None = None) -> Path:
    database_path = database or db_path(root)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    realtime_root = root / "silver" / "realtime"
    variables = {
        "static_path": static_run.resolve().as_posix(),
        "realtime_path": realtime_root.resolve().as_posix(),
        "on_time_early_seconds": -60,
        "on_time_late_seconds": 300,
        "min_reliable_sample_size": 5,
    }
    environment = os.environ.copy()
    environment["MCT_DBT_DATABASE_PATH"] = str(database_path)
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
```

### 11. `src/mct_solo/io.py`

**File size:** `1,169` bytes

```python
"""Shared, deliberately small filesystem helpers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def utc_now() -> datetime:
    return datetime.now(UTC)


def run_id(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_parquet_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    temporary_path = Path(temporary_name)
    try:
        frame.to_parquet(temporary_path, index=False, compression="zstd")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
```

### 12. `src/mct_solo/quality.py`

**File size:** `5,001` bytes

```python
"""Focused checks before dbt; SQL business assertions remain in dbt."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .io import utc_now, write_json


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    problem_count: int
    detail: str


def _check(name: str, problems: int, detail: str) -> Check:
    return Check(name, "PASS" if problems == 0 else "FAIL", int(problems), detail)


def _warning_check(name: str, problems: int, detail: str) -> Check:
    return Check(name, "PASS" if problems == 0 else "WARN", int(problems), detail)


def validate_static(silver_run: Path, report_path: Path | None = None) -> dict[str, Any]:
    tables = {
        name: pd.read_parquet(silver_run / f"{name}.parquet")
        for name in ("routes", "trips", "stops", "stop_times", "calendar", "calendar_dates")
    }
    routes, trips, stops, stop_times = (tables[name] for name in ("routes", "trips", "stops", "stop_times"))
    checks = [
        _check("route_id_not_null", routes["route_id"].isna().sum(), "Every route needs an identifier."),
        _check("route_id_unique", routes["route_id"].duplicated().sum(), "Route identifiers must be unique."),
        _check("trip_id_not_null", trips["trip_id"].isna().sum(), "Every trip needs an identifier."),
        _check("trip_id_unique", trips["trip_id"].duplicated().sum(), "Trip identifiers must be unique."),
        _check("stop_id_unique", stops["stop_id"].duplicated().sum(), "Stop identifiers must be unique."),
        _check(
            "trips_reference_routes",
            (~trips["route_id"].isin(routes["route_id"])).sum(),
            "Trips must reference known routes.",
        ),
        _check(
            "stop_times_reference_trips",
            (~stop_times["trip_id"].isin(trips["trip_id"])).sum(),
            "Stop times must reference known trips.",
        ),
        _check(
            "stop_times_reference_stops",
            (~stop_times["stop_id"].isin(stops["stop_id"])).sum(),
            "Stop times must reference known stops.",
        ),
        _check(
            "stop_time_key_unique",
            stop_times.duplicated(["trip_id", "stop_sequence"]).sum(),
            "A trip can have only one row per stop sequence.",
        ),
    ]
    report = _report("static", checks)
    if report_path:
        write_json(report_path, report)
    return report


def validate_realtime(
    root: Path, report_path: Path | None = None, *, max_abs_delay_seconds: int = 7200
) -> dict[str, Any]:
    stop_files = list((root / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    trip_files = list((root / "silver" / "realtime" / "trip_updates").glob("date=*/*.parquet"))
    stops = (
        pd.concat([pd.read_parquet(path) for path in stop_files], ignore_index=True)
        if stop_files
        else pd.DataFrame(columns=["snapshot_id", "entity_id", "stop_sequence", "observed_delay"])
    )
    trips = (
        pd.concat([pd.read_parquet(path) for path in trip_files], ignore_index=True)
        if trip_files
        else pd.DataFrame(columns=["snapshot_id", "entity_id", "trip_id"])
    )
    delay = pd.to_numeric(stops["observed_delay"], errors="coerce")
    checks = [
        _check(
            "snapshot_id_not_null",
            stops["snapshot_id"].isna().sum() + trips["snapshot_id"].isna().sum(),
            "Parsed rows retain snapshot lineage.",
        ),
        _check("trip_id_not_null", trips["trip_id"].isna().sum(), "Tisséo Trip Updates should identify trips."),
        _check(
            "trip_update_key_unique",
            trips.duplicated(["snapshot_id", "entity_id"]).sum(),
            "A snapshot/entity pair must be unique.",
        ),
        _check(
            "stop_update_key_unique",
            stops.duplicated(["snapshot_id", "entity_id", "stop_sequence"]).sum(),
            "A snapshot/entity/stop-sequence observation must be unique.",
        ),
        _warning_check(
            "delay_sanity",
            delay.abs().gt(max_abs_delay_seconds).sum(),
            f"Published delays outside ±{max_abs_delay_seconds} seconds are retained but excluded from reliability KPIs.",
        ),
    ]
    report = _report("realtime", checks)
    if report_path:
        write_json(report_path, report)
    return report


def _report(layer: str, checks: list[Check]) -> dict[str, Any]:
    statuses = {check.status for check in checks}
    return {
        "layer": layer,
        "checked_at": utc_now().isoformat(),
        "status": "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS",
        "checks": [asdict(check) for check in checks],
    }


def require_pass(report: dict[str, Any]) -> None:
    if report["status"] == "FAIL":
        failed = [check["name"] for check in report["checks"] if check["status"] == "FAIL"]
        raise ValueError(f"Quality checks failed: {', '.join(failed)}")
```

### 13. `src/mct_solo/realtime_pipeline.py`

**File size:** `7,729` bytes

```python
"""Preserve and normalize one GTFS-Realtime Trip Updates snapshot."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2

from .config import SourceConfig
from .io import sha256_bytes, utc_now, write_json, write_parquet_atomic

TRIP_COLUMNS = [
    "snapshot_id",
    "collected_at",
    "service_date",
    "entity_id",
    "trip_id",
    "route_id",
    "direction_id",
    "schedule_relationship",
    "update_timestamp",
]
STOP_COLUMNS = TRIP_COLUMNS + ["stop_id", "stop_sequence", "arrival_delay", "departure_delay", "observed_delay"]
SNAPSHOT_COLUMNS = [
    "snapshot_id",
    "collected_at",
    "collection_date",
    "source_url",
    "sha256",
    "size_bytes",
    "feed_version",
    "header_timestamp",
    "feed_age_seconds",
    "entity_count",
    "trip_update_count",
    "stop_time_update_count",
]


def _enum_name(wrapper: Any, value: int) -> str:
    try:
        return str(wrapper.Name(value))
    except ValueError:
        return f"UNKNOWN_{value}"


def parse_trip_updates(content: bytes, collected_at: datetime) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    if not feed.header.gtfs_realtime_version:
        raise ValueError("GTFS-Realtime feed header has no version")

    checksum = sha256_bytes(content)
    header_timestamp = int(feed.header.timestamp) if feed.header.HasField("timestamp") else None
    identity_time = str(header_timestamp) if header_timestamp is not None else collected_at.strftime("%Y%m%dT%H%M%S")
    snapshot_id = f"{identity_time}-{checksum[:12]}"
    trip_rows: list[dict[str, Any]] = []
    stop_rows: list[dict[str, Any]] = []
    relationship = gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        update = entity.trip_update
        descriptor = update.trip
        base = {
            "snapshot_id": snapshot_id,
            "collected_at": collected_at,
            "service_date": descriptor.start_date or None,
            "entity_id": entity.id,
            "trip_id": descriptor.trip_id or None,
            "route_id": descriptor.route_id or None,
            "direction_id": int(descriptor.direction_id) if descriptor.HasField("direction_id") else None,
            "schedule_relationship": _enum_name(relationship, descriptor.schedule_relationship),
            "update_timestamp": datetime.fromtimestamp(update.timestamp, tz=UTC) if update.timestamp else None,
        }
        trip_rows.append(base)
        for stop_update in update.stop_time_update:
            arrival_delay = (
                int(stop_update.arrival.delay)
                if stop_update.HasField("arrival") and stop_update.arrival.HasField("delay")
                else None
            )
            departure_delay = (
                int(stop_update.departure.delay)
                if stop_update.HasField("departure") and stop_update.departure.HasField("delay")
                else None
            )
            stop_rows.append(
                {
                    **base,
                    "stop_id": stop_update.stop_id or None,
                    "stop_sequence": int(stop_update.stop_sequence) if stop_update.HasField("stop_sequence") else None,
                    "arrival_delay": arrival_delay,
                    "departure_delay": departure_delay,
                    "observed_delay": arrival_delay if arrival_delay is not None else departure_delay,
                }
            )

    trips = pd.DataFrame(trip_rows, columns=TRIP_COLUMNS)
    stops = pd.DataFrame(stop_rows, columns=STOP_COLUMNS)
    metadata = {
        "snapshot_id": snapshot_id,
        "collected_at": collected_at.isoformat(),
        "collection_date": collected_at.date().isoformat(),
        "sha256": checksum,
        "size_bytes": len(content),
        "feed_version": feed.header.gtfs_realtime_version,
        "header_timestamp": (
            datetime.fromtimestamp(header_timestamp, tz=UTC).isoformat() if header_timestamp is not None else None
        ),
        "feed_age_seconds": int(collected_at.timestamp() - header_timestamp) if header_timestamp is not None else None,
        "entity_count": len(feed.entity),
        "trip_update_count": len(trips),
        "stop_time_update_count": len(stops),
    }
    return trips, stops, metadata


def preserve_realtime_bytes(
    content: bytes,
    source: SourceConfig,
    root: Path,
    *,
    source_url: str | None = None,
    collected_at: datetime | None = None,
    http_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    moment = (collected_at or utc_now()).astimezone(UTC)
    trips, stops, metadata = parse_trip_updates(content, moment)
    metadata.update(
        {"source_id": source.id, "source_url": source_url or source.trip_updates_url, "http": http_metadata or {}}
    )
    date = metadata["collection_date"]
    snapshot_id = metadata["snapshot_id"]
    raw_dir = root / "raw" / "realtime" / f"date={date}" / snapshot_id
    silver_files = {
        "trip_updates": root / "silver" / "realtime" / "trip_updates" / f"date={date}" / f"{snapshot_id}.parquet",
        "stop_time_updates": root
        / "silver"
        / "realtime"
        / "stop_time_updates"
        / f"date={date}"
        / f"{snapshot_id}.parquet",
        "feed_snapshots": root / "silver" / "realtime" / "feed_snapshots" / f"date={date}" / f"{snapshot_id}.parquet",
    }
    if (raw_dir / "_SUCCESS").is_file() and all(path.is_file() for path in silver_files.values()):
        saved = json.loads((raw_dir / "metadata.json").read_text(encoding="utf-8"))
        return {**saved, "duplicate": True}

    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "feed.pb"
    if raw_file.exists() and sha256_bytes(raw_file.read_bytes()) != metadata["sha256"]:
        raise ValueError(f"Snapshot collision at {raw_dir}")
    raw_file.write_bytes(content)
    metadata["raw_path"] = str(raw_file.resolve())
    write_json(raw_dir / "metadata.json", metadata)

    snapshot_row = pd.DataFrame(
        [{column: metadata.get(column) for column in SNAPSHOT_COLUMNS}],
        columns=SNAPSHOT_COLUMNS,
    )
    write_parquet_atomic(trips, silver_files["trip_updates"])
    write_parquet_atomic(stops, silver_files["stop_time_updates"])
    write_parquet_atomic(snapshot_row, silver_files["feed_snapshots"])
    (raw_dir / "_SUCCESS").write_text("ok\n", encoding="utf-8")
    return {**metadata, "duplicate": False}


def download_realtime(source: SourceConfig, root: Path, *, timeout_seconds: int = 30) -> dict[str, Any]:
    response = requests.get(source.trip_updates_url, timeout=timeout_seconds)
    response.raise_for_status()
    return preserve_realtime_bytes(
        response.content,
        source,
        root,
        source_url=response.url,
        http_metadata={"status_code": response.status_code, "content_type": response.headers.get("content-type")},
    )


def ensure_empty_realtime_tables(root: Path) -> None:
    """Create schema-only files so a static-only dbt build remains reproducible."""
    base = root / "silver" / "realtime"
    empty_tables = {
        "trip_updates": pd.DataFrame(columns=TRIP_COLUMNS),
        "stop_time_updates": pd.DataFrame(columns=STOP_COLUMNS),
        "feed_snapshots": pd.DataFrame(columns=SNAPSHOT_COLUMNS),
    }
    for name, frame in empty_tables.items():
        path = base / name / "_empty.parquet"
        if not path.exists():
            write_parquet_atomic(frame, path)
```

### 14. `src/mct_solo/static_pipeline.py`

**File size:** `9,837` bytes

```python
"""Download, preserve, extract, and normalize Tisséo GTFS Schedule data."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
import requests

from .config import SourceConfig
from .io import run_id, sha256_bytes, utc_now, write_json, write_parquet_atomic

GTFS_FILES = ("routes.txt", "trips.txt", "stops.txt", "stop_times.txt", "calendar.txt", "calendar_dates.txt")
REQUIRED_FILES = {"routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}


def _validate_archive(content: bytes) -> list[str]:
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise ValueError("Downloaded static source is not a valid ZIP archive")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
    missing = REQUIRED_FILES - set(names)
    if missing:
        raise ValueError(f"GTFS archive is missing required files: {sorted(missing)}")
    return names


def preserve_static_bytes(
    content: bytes,
    source: SourceConfig,
    root: Path,
    *,
    source_url: str | None = None,
    ingested_at: datetime | None = None,
    http_metadata: dict[str, Any] | None = None,
) -> Path:
    names = _validate_archive(content)
    moment = ingested_at or utc_now()
    destination = root / "raw" / "static" / run_id(moment)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        archive_path = destination / "gtfs.zip"
        archive_path.write_bytes(content)
        metadata = {
            "source_id": source.id,
            "source_name": source.name,
            "source_page": source.source_page,
            "source_url": source_url or source.gtfs_url,
            "licence": source.licence,
            "ingested_at": moment.isoformat(),
            "sha256": sha256_bytes(content),
            "size_bytes": len(content),
            "archive_members": names,
            "http": http_metadata or {},
        }
        write_json(destination / "metadata.json", metadata)
        (destination / "_SUCCESS").write_text("ok\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination


def download_static(source: SourceConfig, root: Path, *, timeout_seconds: int = 60) -> Path:
    response = requests.get(source.gtfs_url, timeout=timeout_seconds)
    response.raise_for_status()
    return preserve_static_bytes(
        response.content,
        source,
        root,
        source_url=response.url,
        http_metadata={
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "etag": response.headers.get("etag"),
            "last_modified": response.headers.get("last-modified"),
        },
    )


def extract_bronze(raw_run: Path, root: Path) -> Path:
    archive_path = raw_run / "gtfs.zip"
    if not archive_path.is_file():
        raise FileNotFoundError(f"Raw GTFS archive not found: {archive_path}")
    destination = root / "bronze" / "static" / raw_run.name
    if (destination / "manifest.json").is_file():
        return destination
    temporary = destination.parent / f".{destination.name}.tmp"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            available = set(archive.namelist())
            for filename in GTFS_FILES:
                if filename not in available:
                    continue
                member = PurePosixPath(filename)
                if member.name != filename:
                    raise ValueError(f"Unsafe GTFS member path: {filename}")
                (temporary / filename).write_bytes(archive.read(filename))
        metadata = json.loads((raw_run / "metadata.json").read_text(encoding="utf-8"))
        write_json(
            temporary / "manifest.json",
            {"run_id": raw_run.name, "raw_run": str(raw_run.resolve()), "source_sha256": metadata["sha256"]},
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def _read_gtfs(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype="string", keep_default_na=False)


def _columns(frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for name in names:
        if name not in result:
            result[name] = pd.NA
    return result[names]


def gtfs_time_to_seconds(value: object) -> int | None:
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    parts = str(value).split(":")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid GTFS time: {value}")
    hour, minute, second = (int(part) for part in parts)
    if hour > 47 or minute > 59 or second > 59:
        raise ValueError(f"Invalid GTFS time: {value}")
    return hour * 3600 + minute * 60 + second


def _date_column(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series.replace("", pd.NA), format="%Y%m%d", errors="raise")
    return parsed.dt.date


def _normalise_tables(bronze_run: Path) -> dict[str, pd.DataFrame]:
    routes = _columns(
        _read_gtfs(bronze_run / "routes.txt"),
        ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
    )
    routes["route_type"] = pd.to_numeric(routes["route_type"], errors="coerce").astype("Int64")

    trips = _columns(
        _read_gtfs(bronze_run / "trips.txt"),
        ["trip_id", "route_id", "service_id", "trip_headsign", "direction_id"],
    )
    trips["direction_id"] = pd.to_numeric(trips["direction_id"], errors="coerce").astype("Int64")

    stops = _columns(_read_gtfs(bronze_run / "stops.txt"), ["stop_id", "stop_name", "stop_lat", "stop_lon"])
    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")

    stop_times = _columns(
        _read_gtfs(bronze_run / "stop_times.txt"),
        ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"],
    )
    stop_times["stop_sequence"] = pd.to_numeric(stop_times["stop_sequence"], errors="raise").astype("int64")
    stop_times["arrival_seconds"] = stop_times["arrival_time"].map(gtfs_time_to_seconds).astype("Int64")
    stop_times["departure_seconds"] = stop_times["departure_time"].map(gtfs_time_to_seconds).astype("Int64")

    if (bronze_run / "calendar.txt").is_file():
        calendar = _columns(
            _read_gtfs(bronze_run / "calendar.txt"),
            [
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ],
        )
        for weekday in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            calendar[weekday] = pd.to_numeric(calendar[weekday], errors="raise").astype("int8")
        calendar["start_date"] = _date_column(calendar["start_date"])
        calendar["end_date"] = _date_column(calendar["end_date"])
    else:
        calendar = pd.DataFrame(
            columns=[
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ]
        )

    if (bronze_run / "calendar_dates.txt").is_file():
        calendar_dates = _columns(
            _read_gtfs(bronze_run / "calendar_dates.txt"), ["service_id", "date", "exception_type"]
        )
        calendar_dates["date"] = _date_column(calendar_dates["date"])
        calendar_dates["exception_type"] = pd.to_numeric(calendar_dates["exception_type"], errors="raise").astype(
            "int8"
        )
    else:
        calendar_dates = pd.DataFrame(columns=["service_id", "date", "exception_type"])

    return {
        "routes": routes,
        "trips": trips,
        "stops": stops,
        "stop_times": stop_times,
        "calendar": calendar,
        "calendar_dates": calendar_dates,
    }


def transform_static(raw_run: Path, root: Path) -> Path:
    bronze_run = extract_bronze(raw_run, root)
    destination = root / "silver" / "static" / raw_run.name
    if (destination / "manifest.json").is_file():
        return destination
    temporary = destination.parent / f".{destination.name}.tmp"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    try:
        tables = _normalise_tables(bronze_run)
        for name, frame in tables.items():
            write_parquet_atomic(frame, temporary / f"{name}.parquet")
        raw_metadata = json.loads((raw_run / "metadata.json").read_text(encoding="utf-8"))
        write_json(
            temporary / "manifest.json",
            {
                "run_id": raw_run.name,
                "source_id": raw_metadata["source_id"],
                "source_url": raw_metadata["source_url"],
                "source_sha256": raw_metadata["sha256"],
                "transformed_at": utc_now().isoformat(),
                "row_counts": {name: len(frame) for name, frame in tables.items()},
            },
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination
```

## Data Models / SQL / dbt

### 15. `dbt/dbt_project.yml`

**File size:** `495` bytes

```yaml
name: mct_solo
version: "0.1.0"
config-version: 2
profile: mct_solo

model-paths: ["models"]
test-paths: ["tests"]
target-path: target
clean-targets: [target, dbt_packages]

vars:
  static_path: ../data/silver/static/fixture
  realtime_path: ../data/silver/realtime
  on_time_early_seconds: -60
  on_time_late_seconds: 300
  min_reliable_sample_size: 5

models:
  mct_solo:
    staging:
      +materialized: view
    intermediate:
      +materialized: view
    marts:
      +materialized: table
```

### 16. `dbt/models/intermediate/int_delay_observations.sql`

**File size:** `1,744` bytes

```sql
with deduplicated as (
    select * exclude (_row_number)
    from (
        select
            updates.*,
            row_number() over (
                partition by snapshot_id, entity_id, stop_sequence
                order by collected_at desc
            ) as _row_number
        from {{ ref('stg_realtime_updates') }} updates
    )
    where _row_number = 1
)
select
    updates.snapshot_id,
    updates.collected_at,
    coalesce(
        updates.service_date,
        cast(timezone('Europe/Paris', updates.collected_at) as date)
    ) as service_date,
    updates.entity_id,
    updates.trip_id,
    coalesce(updates.route_id, trips.route_id) as route_id,
    routes.route_short_name,
    routes.route_long_name,
    updates.stop_id,
    updates.stop_sequence,
    stop_times.departure_seconds,
    updates.observed_delay as delay_seconds,
    updates.schedule_relationship,
    trips.trip_id is not null as static_trip_match,
    updates.observed_delay is not null as raw_delay_present,
    updates.observed_delay is not null and abs(updates.observed_delay) <= 7200 as has_known_delay,
    case
        when updates.observed_delay is null then 'MISSING'
        when abs(updates.observed_delay) > 7200 then 'OUT_OF_RANGE'
        else 'VALID'
    end as delay_quality_status,
    updates.observed_delay between {{ var('on_time_early_seconds') }} and {{ var('on_time_late_seconds') }} as is_on_time
from deduplicated updates
left join {{ ref('stg_trips') }} trips using (trip_id)
left join {{ ref('stg_routes') }} routes on coalesce(updates.route_id, trips.route_id) = routes.route_id
left join {{ ref('stg_stop_times') }} stop_times
    on updates.trip_id = stop_times.trip_id
    and updates.stop_sequence = stop_times.stop_sequence
```

### 17. `dbt/models/intermediate/int_scheduled_trips.sql`

**File size:** `324` bytes

```sql
select
    service.service_date,
    trips.trip_id,
    trips.service_id,
    trips.route_id,
    routes.route_short_name,
    routes.route_long_name,
    routes.route_type
from {{ ref('stg_trips') }} trips
join {{ ref('int_service_dates') }} service using (service_id)
join {{ ref('stg_routes') }} routes using (route_id)
```

### 18. `dbt/models/intermediate/int_service_dates.sql`

**File size:** `965` bytes

```sql
with regular as (
    select c.service_id, cast(day.service_date as date) as service_date
    from {{ ref('stg_calendar') }} c,
    generate_series(c.start_date, c.end_date, interval 1 day) as day(service_date)
    where case extract(isodow from day.service_date)
        when 1 then c.monday
        when 2 then c.tuesday
        when 3 then c.wednesday
        when 4 then c.thursday
        when 5 then c.friday
        when 6 then c.saturday
        when 7 then c.sunday
    end = 1
),
added as (
    select service_id, service_date
    from {{ ref('stg_calendar_dates') }}
    where exception_type = 1
),
removed as (
    select service_id, service_date
    from {{ ref('stg_calendar_dates') }}
    where exception_type = 2
),
candidates as (
    select * from regular
    union
    select * from added
)
select candidates.service_id, candidates.service_date
from candidates
left join removed using (service_id, service_date)
where removed.service_id is null
```

### 19. `dbt/models/intermediate/schema.yml`

**File size:** `843` bytes

```yaml
version: 2

models:
  - name: int_service_dates
    description: GTFS regular service dates after applying added and removed exceptions.
    columns:
      - name: service_id
        tests: [not_null]
      - name: service_date
        tests: [not_null]
  - name: int_scheduled_trips
    columns:
      - name: trip_id
        tests: [not_null]
      - name: service_date
        tests: [not_null]
  - name: int_delay_observations
    description: Deduplicated Trip Update observations enriched with static schedule matches. Published delays beyond ±7200 seconds are retained as OUT_OF_RANGE but are not KPI-eligible.
    columns:
      - name: snapshot_id
        tests: [not_null]
      - name: delay_quality_status
        tests:
          - accepted_values:
              arguments:
                values: [VALID, MISSING, OUT_OF_RANGE]
```

### 20. `dbt/models/intermediate/unit_tests.yml`

**File size:** `3,963` bytes

```yaml
version: 2

unit_tests:
  - name: service_date_fallback_uses_paris_local_date
    description: A missing GTFS-RT start_date falls back to the Europe/Paris observation date.
    model: int_delay_observations
    given:
      - input: ref('stg_realtime_updates')
        format: sql
        rows: |
          select
              'snapshot-midnight'::varchar as snapshot_id,
              timestamptz '2026-01-01 23:30:00+00' as collected_at,
              null::date as service_date,
              'entity-1'::varchar as entity_id,
              'T1'::varchar as trip_id,
              'R1'::varchar as route_id,
              'S1'::varchar as stop_id,
              1::integer as stop_sequence,
              0::integer as observed_delay,
              'SCHEDULED'::varchar as schedule_relationship
      - input: ref('stg_trips')
        format: sql
        rows: |
          select 'T1'::varchar as trip_id, 'R1'::varchar as route_id
      - input: ref('stg_routes')
        format: sql
        rows: |
          select
              'R1'::varchar as route_id,
              'A'::varchar as route_short_name,
              'Airport'::varchar as route_long_name
      - input: ref('stg_stop_times')
        format: sql
        rows: |
          select
              'T1'::varchar as trip_id,
              1::integer as stop_sequence,
              84600::integer as departure_seconds
    expect:
      format: dict
      rows:
        - {snapshot_id: snapshot-midnight, service_date: '2026-01-02'}

  - name: delay_quality_status_respects_sanity_boundary
    description: Delays at exactly +/-7200 seconds remain valid while missing and beyond-boundary values are classified.
    model: int_delay_observations
    given:
      - input: ref('stg_realtime_updates')
        format: sql
        rows: |
          select
              'snapshot-boundary'::varchar as snapshot_id,
              timestamptz '2026-01-01 12:00:00+00' as collected_at,
              date '2026-01-01' as service_date,
              test_case.entity_id::varchar as entity_id,
              'T1'::varchar as trip_id,
              'R1'::varchar as route_id,
              'S1'::varchar as stop_id,
              test_case.stop_sequence::integer as stop_sequence,
              test_case.observed_delay::integer as observed_delay,
              'SCHEDULED'::varchar as schedule_relationship
          from (
              values
                  ('missing', 1, null::integer),
                  ('negative-out', 2, -7201),
                  ('negative-edge', 3, -7200),
                  ('positive-edge', 4, 7200),
                  ('positive-out', 5, 7201)
          ) as test_case(entity_id, stop_sequence, observed_delay)
      - input: ref('stg_trips')
        format: sql
        rows: |
          select 'T1'::varchar as trip_id, 'R1'::varchar as route_id
      - input: ref('stg_routes')
        format: sql
        rows: |
          select
              'R1'::varchar as route_id,
              'A'::varchar as route_short_name,
              'Airport'::varchar as route_long_name
      - input: ref('stg_stop_times')
        format: sql
        rows: |
          select
              'T1'::varchar as trip_id,
              stop_sequence::integer as stop_sequence,
              43200::integer as departure_seconds
          from range(1, 6) as stop_times(stop_sequence)
    expect:
      format: dict
      rows:
        - {entity_id: missing, delay_seconds: null, has_known_delay: false, delay_quality_status: MISSING}
        - {entity_id: negative-out, delay_seconds: -7201, has_known_delay: false, delay_quality_status: OUT_OF_RANGE}
        - {entity_id: negative-edge, delay_seconds: -7200, has_known_delay: true, delay_quality_status: VALID}
        - {entity_id: positive-edge, delay_seconds: 7200, has_known_delay: true, delay_quality_status: VALID}
        - {entity_id: positive-out, delay_seconds: 7201, has_known_delay: false, delay_quality_status: OUT_OF_RANGE}
```

### 21. `dbt/models/marts/feed_freshness.sql`

**File size:** `426` bytes

```sql
select
    snapshot_id,
    collected_at,
    collection_date,
    header_timestamp,
    feed_age_seconds,
    entity_count,
    trip_update_count,
    stop_time_update_count,
    case
        when feed_age_seconds is null then 'UNKNOWN'
        when feed_age_seconds <= 90 then 'FRESH'
        when feed_age_seconds <= 300 then 'DELAYED'
        else 'STALE'
    end as freshness_status
from {{ ref('stg_feed_snapshots') }}
```

### 22. `dbt/models/marts/hourly_delay_summary.sql`

**File size:** `635` bytes

```sql
select
    service_date,
    cast(floor((departure_seconds % 86400) / 3600) as integer) as service_hour,
    count(*) as observed_stop_updates,
    case
        when count(*) >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
        else 'LOW_SAMPLE'
    end as sample_size_status,
    round(avg(delay_seconds), 1) as average_delay_seconds,
    round(median(delay_seconds), 1) as median_delay_seconds,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage
from {{ ref('int_delay_observations') }}
where static_trip_match and has_known_delay and departure_seconds is not null
group by 1, 2
```

### 23. `dbt/models/marts/network_on_time_performance.sql`

**File size:** `504` bytes

```sql
select
    service_date,
    count(*) as observed_stop_updates,
    count(distinct trip_id) as observed_trips,
    count(*) filter (where is_on_time) as on_time_observations,
    count(*) filter (where not is_on_time) as outside_on_time_window_observations,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage,
    round(avg(delay_seconds), 1) as average_delay_seconds
from {{ ref('int_delay_observations') }}
where static_trip_match and has_known_delay
group by 1
```

### 24. `dbt/models/marts/realtime_coverage.sql`

**File size:** `983` bytes

```sql
with monitored_dates as (
    select distinct collection_date as service_date
    from {{ ref('stg_feed_snapshots') }}
),
scheduled as (
    select service_date, count(distinct trip_id) as eligible_scheduled_trips
    from {{ ref('int_scheduled_trips') }}
    where service_date in (select service_date from monitored_dates)
    group by 1
),
observed as (
    select service_date, count(distinct trip_id) as observed_matched_trips
    from {{ ref('int_delay_observations') }}
    where static_trip_match
    group by 1
)
select
    scheduled.service_date,
    scheduled.eligible_scheduled_trips,
    coalesce(observed.observed_matched_trips, 0) as observed_matched_trips,
    scheduled.eligible_scheduled_trips - coalesce(observed.observed_matched_trips, 0) as trips_with_unknown_status,
    round(100.0 * coalesce(observed.observed_matched_trips, 0) / nullif(scheduled.eligible_scheduled_trips, 0), 2) as coverage_percentage
from scheduled
left join observed using (service_date)
```

### 25. `dbt/models/marts/route_daily_service.sql`

**File size:** `474` bytes

```sql
with departures as (
    select trip_id, count(*) as scheduled_departures
    from {{ ref('stg_stop_times') }}
    group by trip_id
)
select
    trips.service_date,
    trips.route_id,
    trips.route_short_name,
    trips.route_long_name,
    count(distinct trips.trip_id) as scheduled_trips,
    sum(coalesce(departures.scheduled_departures, 0)) as scheduled_departures
from {{ ref('int_scheduled_trips') }} trips
left join departures using (trip_id)
group by 1, 2, 3, 4
```

### 26. `dbt/models/marts/route_delay_summary.sql`

**File size:** `766` bytes

```sql
select
    service_date,
    route_id,
    route_short_name,
    route_long_name,
    count(*) as observed_stop_updates,
    case
        when count(*) >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
        else 'LOW_SAMPLE'
    end as sample_size_status,
    count(distinct trip_id) as observed_trips,
    round(avg(delay_seconds), 1) as average_delay_seconds,
    round(median(delay_seconds), 1) as median_delay_seconds,
    round(quantile_cont(delay_seconds, 0.90), 1) as p90_delay_seconds,
    count(*) filter (where is_on_time) as on_time_observations,
    round(100.0 * count(*) filter (where is_on_time) / count(*), 2) as on_time_percentage
from {{ ref('int_delay_observations') }}
where static_trip_match and has_known_delay
group by 1, 2, 3, 4
```

### 27. `dbt/models/marts/schema.yml`

**File size:** `2,180` bytes

```yaml
version: 2

models:
  - name: route_daily_service
    description: Planned service volume at route and GTFS service-date grain.
    columns:
      - name: service_date
        tests: [not_null]
      - name: route_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_routes')
                field: route_id
      - name: scheduled_trips
        tests: [not_null]
  - name: route_delay_summary
    description: Delay statistics over matched stop-time observations with a known delay; not passenger weighted.
    columns:
      - name: route_id
        tests: [not_null]
      - name: on_time_percentage
        tests: [not_null]
      - name: sample_size_status
        tests:
          - accepted_values:
              arguments:
                values: [RELIABLE, LOW_SAMPLE]
  - name: hourly_delay_summary
    description: Network delay by scheduled service hour. Times after 24:00 wrap to their clock hour.
    columns:
      - name: service_hour
        tests:
          - accepted_values:
              arguments:
                values: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
      - name: sample_size_status
        tests:
          - accepted_values:
              arguments:
                values: [RELIABLE, LOW_SAMPLE]
  - name: network_on_time_performance
    description: Daily OTP using matched observations with known delay only; unknown observations are excluded.
    columns:
      - name: service_date
        tests: [not_null, unique]
      - name: on_time_percentage
        tests: [not_null]
  - name: realtime_coverage
    description: Share of eligible scheduled trips observed in Trip Updates on dates when at least one snapshot was collected.
    columns:
      - name: service_date
        tests: [not_null, unique]
  - name: feed_freshness
    description: Feed age and status per unique polling snapshot.
    columns:
      - name: snapshot_id
        tests: [not_null, unique]
      - name: freshness_status
        tests:
          - accepted_values:
              arguments:
                values: [FRESH, DELAYED, STALE, UNKNOWN]
```

### 28. `dbt/models/staging/schema.yml`

**File size:** `1,365` bytes

```yaml
version: 2

models:
  - name: stg_routes
    description: One row per Tisséo route from the selected static feed.
    columns:
      - name: route_id
        tests: [not_null, unique]
  - name: stg_trips
    description: Scheduled trips with route and service identifiers.
    columns:
      - name: trip_id
        tests: [not_null, unique]
      - name: route_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_routes')
                field: route_id
  - name: stg_stop_times
    description: Scheduled stop calls with GTFS times represented as seconds after service-day midnight.
    columns:
      - name: trip_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_trips')
                field: trip_id
      - name: stop_sequence
        tests: [not_null]
  - name: stg_calendar_dates
    columns:
      - name: exception_type
        tests:
          - accepted_values:
              arguments:
                values: [1, 2]
  - name: stg_realtime_updates
    description: Stop-time updates from scheduled polling; rows without a delay remain unknown.
    columns:
      - name: snapshot_id
        tests: [not_null]
  - name: stg_feed_snapshots
    columns:
      - name: snapshot_id
        tests: [not_null, unique]
```

### 29. `dbt/models/staging/stg_calendar.sql`

**File size:** `490` bytes

```sql
select
    cast(service_id as varchar) as service_id,
    cast(monday as integer) as monday,
    cast(tuesday as integer) as tuesday,
    cast(wednesday as integer) as wednesday,
    cast(thursday as integer) as thursday,
    cast(friday as integer) as friday,
    cast(saturday as integer) as saturday,
    cast(sunday as integer) as sunday,
    cast(start_date as date) as start_date,
    cast(end_date as date) as end_date
from read_parquet('{{ var("static_path") }}/calendar.parquet')
```

### 30. `dbt/models/staging/stg_calendar_dates.sql`

**File size:** `218` bytes

```sql
select
    cast(service_id as varchar) as service_id,
    cast(date as date) as service_date,
    cast(exception_type as integer) as exception_type
from read_parquet('{{ var("static_path") }}/calendar_dates.parquet')
```

### 31. `dbt/models/staging/stg_feed_snapshots.sql`

**File size:** `695` bytes

```sql
select
    cast(snapshot_id as varchar) as snapshot_id,
    cast(collected_at as timestamptz) as collected_at,
    cast(collection_date as date) as collection_date,
    cast(source_url as varchar) as source_url,
    cast(sha256 as varchar) as sha256,
    cast(header_timestamp as timestamptz) as header_timestamp,
    cast(feed_age_seconds as integer) as feed_age_seconds,
    cast(entity_count as integer) as entity_count,
    cast(trip_update_count as integer) as trip_update_count,
    cast(stop_time_update_count as integer) as stop_time_update_count
from read_parquet(
    '{{ var("realtime_path") }}/feed_snapshots/**/*.parquet',
    union_by_name = true,
    hive_partitioning = false
)
```

### 32. `dbt/models/staging/stg_realtime_updates.sql`

**File size:** `827` bytes

```sql
select
    cast(snapshot_id as varchar) as snapshot_id,
    cast(collected_at as timestamptz) as collected_at,
    try_strptime(cast(service_date as varchar), '%Y%m%d')::date as service_date,
    cast(entity_id as varchar) as entity_id,
    nullif(cast(trip_id as varchar), '') as trip_id,
    nullif(cast(route_id as varchar), '') as route_id,
    cast(schedule_relationship as varchar) as schedule_relationship,
    nullif(cast(stop_id as varchar), '') as stop_id,
    cast(stop_sequence as integer) as stop_sequence,
    cast(arrival_delay as integer) as arrival_delay,
    cast(departure_delay as integer) as departure_delay,
    cast(observed_delay as integer) as observed_delay
from read_parquet(
    '{{ var("realtime_path") }}/stop_time_updates/**/*.parquet',
    union_by_name = true,
    hive_partitioning = false
)
```

### 33. `dbt/models/staging/stg_routes.sql`

**File size:** `298` bytes

```sql
select
    cast(route_id as varchar) as route_id,
    nullif(cast(route_short_name as varchar), '') as route_short_name,
    nullif(cast(route_long_name as varchar), '') as route_long_name,
    cast(route_type as integer) as route_type
from read_parquet('{{ var("static_path") }}/routes.parquet')
```

### 34. `dbt/models/staging/stg_stop_times.sql`

**File size:** `325` bytes

```sql
select
    cast(trip_id as varchar) as trip_id,
    cast(stop_id as varchar) as stop_id,
    cast(stop_sequence as integer) as stop_sequence,
    cast(arrival_seconds as integer) as arrival_seconds,
    cast(departure_seconds as integer) as departure_seconds
from read_parquet('{{ var("static_path") }}/stop_times.parquet')
```

### 35. `dbt/models/staging/stg_trips.sql`

**File size:** `314` bytes

```sql
select
    cast(trip_id as varchar) as trip_id,
    cast(route_id as varchar) as route_id,
    cast(service_id as varchar) as service_id,
    nullif(cast(trip_headsign as varchar), '') as trip_headsign,
    cast(direction_id as integer) as direction_id
from read_parquet('{{ var("static_path") }}/trips.parquet')
```

### 36. `dbt/profiles.yml`

**File size:** `180` bytes

```yaml
mct_solo:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('MCT_DBT_DATABASE_PATH', '../data/mart/mobility_control_tower.duckdb') }}"
      threads: 4
```

### 37. `dbt/tests/assert_coverage_reconciles.sql`

**File size:** `275` bytes

```sql
select service_date, eligible_scheduled_trips, observed_matched_trips, trips_with_unknown_status
from {{ ref('realtime_coverage') }}
where eligible_scheduled_trips != observed_matched_trips + trips_with_unknown_status
   or observed_matched_trips > eligible_scheduled_trips
```

### 38. `dbt/tests/assert_delay_within_sanity_bound.sql`

**File size:** `180` bytes

```sql
select snapshot_id, entity_id, stop_sequence, delay_seconds
from {{ ref('int_delay_observations') }}
where has_known_delay and (delay_seconds is null or abs(delay_seconds) > 7200)
```

### 39. `dbt/tests/assert_known_observations_reconcile.sql`

**File size:** `239` bytes

```sql
select service_date, observed_stop_updates, on_time_observations, outside_on_time_window_observations
from {{ ref('network_on_time_performance') }}
where observed_stop_updates != on_time_observations + outside_on_time_window_observations
```

### 40. `dbt/tests/assert_percentages_in_range.sql`

**File size:** `625` bytes

```sql
select 'route_delay_summary' as model_name, on_time_percentage as invalid_percentage
from {{ ref('route_delay_summary') }}
where on_time_percentage not between 0 and 100

union all

select 'hourly_delay_summary', on_time_percentage
from {{ ref('hourly_delay_summary') }}
where on_time_percentage not between 0 and 100

union all

select 'network_on_time_performance', on_time_percentage
from {{ ref('network_on_time_performance') }}
where on_time_percentage not between 0 and 100

union all

select 'realtime_coverage', coverage_percentage
from {{ ref('realtime_coverage') }}
where coverage_percentage not between 0 and 100
```

### 41. `dbt/tests/assert_sample_size_status_matches_count.sql`

**File size:** `697` bytes

```sql
select
    'route_delay_summary' as model_name,
    service_date,
    route_id as group_key,
    observed_stop_updates,
    sample_size_status
from {{ ref('route_delay_summary') }}
where sample_size_status != case
    when observed_stop_updates >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
    else 'LOW_SAMPLE'
end

union all

select
    'hourly_delay_summary' as model_name,
    service_date,
    cast(service_hour as varchar) as group_key,
    observed_stop_updates,
    sample_size_status
from {{ ref('hourly_delay_summary') }}
where sample_size_status != case
    when observed_stop_updates >= {{ var('min_reliable_sample_size', 5) }} then 'RELIABLE'
    else 'LOW_SAMPLE'
end
```

## Orchestration

### 42. `airflow/dags/realtime_pipeline.py`

**File size:** `1,293` bytes

```python
"""Five-minute GTFS-RT workflow: collect, validate, and refresh dbt marts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from airflow.decorators import dag, task

from mct_solo.config import data_root, latest_run, load_source
from mct_solo.dbt import build_dbt
from mct_solo.quality import require_pass, validate_realtime
from mct_solo.realtime_pipeline import download_realtime


@dag(
    dag_id="realtime_pipeline",
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["mct", "gtfs-rt"],
)
def realtime_pipeline():
    @task
    def fetch_parse_and_append() -> str:
        metadata = download_realtime(load_source(), data_root())
        return str(metadata["snapshot_id"])

    @task
    def quality_checks(snapshot_id: str) -> str:
        report_path = data_root() / "quality" / f"realtime-{snapshot_id}.json"
        require_pass(validate_realtime(data_root(), report_path))
        return snapshot_id

    @task
    def dbt_build(_: str) -> str:
        static_run = latest_run(data_root() / "silver" / "static")
        return str(build_dbt(Path(static_run), data_root()))

    dbt_build(quality_checks(fetch_parse_and_append()))


realtime_pipeline()
```

### 43. `airflow/dags/static_gtfs_pipeline.py`

**File size:** `1,483` bytes

```python
"""Daily static GTFS workflow: preserve, transform, validate, and build dbt."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from airflow.decorators import dag, task

from mct_solo.config import data_root, load_source
from mct_solo.dbt import build_dbt
from mct_solo.quality import require_pass, validate_static
from mct_solo.realtime_pipeline import ensure_empty_realtime_tables
from mct_solo.static_pipeline import download_static, transform_static


@dag(
    dag_id="static_gtfs_pipeline",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["mct", "gtfs"],
)
def static_gtfs_pipeline():
    @task
    def download_and_preserve() -> str:
        return str(download_static(load_source(), data_root()))

    @task
    def build_silver(raw_run: str) -> str:
        return str(transform_static(Path(raw_run), data_root()))

    @task
    def quality_checks(silver_run: str) -> str:
        run = Path(silver_run)
        report_path = data_root() / "quality" / f"static-{run.name}.json"
        report = validate_static(run, report_path)
        require_pass(report)
        return silver_run

    @task
    def dbt_build(silver_run: str) -> str:
        ensure_empty_realtime_tables(data_root())
        return str(build_dbt(Path(silver_run), data_root()))

    dbt_build(quality_checks(build_silver(download_and_preserve())))


static_gtfs_pipeline()
```

## Infrastructure / CI / Deployment / Observability

### 44. `.github/workflows/ci.yml`

**File size:** `849` bytes

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - name: Install project
        run: python -m pip install -e ".[dev,analytics]"
      - name: Python quality and tests
        run: |
          ruff check .
          black --check .
          isort --check-only .
          mypy src
          coverage run -m pytest
          coverage report --fail-under=80
      - name: Deterministic dbt build and tests
        run: |
          python scripts/create_ci_fixture.py data/ci
          mct --data-root data/ci dbt-build --static-run data/ci/silver/static/20260101T120000000000Z
      - name: Build container image
        run: docker build -t mct-solo:ci .
```

### 45. `docker-compose.yml`

**File size:** `1,313` bytes

```yaml
x-mct-common: &mct-common
  build: .
  environment: &mct-environment
    MCT_DATA_ROOT: /opt/mct/data
    MCT_DBT_DATABASE_PATH: /opt/mct/data/mart/mobility_control_tower.duckdb
    AIRFLOW__CORE__DAGS_FOLDER: /opt/mct/airflow/dags
    AIRFLOW__CORE__LOAD_EXAMPLES: "False"
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: sqlite:////opt/airflow/airflow.db
    AIRFLOW__WEBSERVER__SECRET_KEY: local-portfolio-only
  volumes:
    - ./data:/opt/mct/data
    - airflow-state:/opt/airflow

services:
  airflow-init:
    <<: *mct-common
    command: >
      bash -c "airflow db migrate &&
      if ! airflow users list --output plain | grep -q 'airflow'; then
      airflow users create --username airflow --password airflow
      --firstname Local --lastname User --role Admin --email local@example.test;
      fi"

  airflow-webserver:
    <<: *mct-common
    command: airflow webserver
    depends_on:
      airflow-init:
        condition: service_completed_successfully
    ports:
      - "8080:8080"

  airflow-scheduler:
    <<: *mct-common
    command: airflow scheduler
    depends_on:
      airflow-init:
        condition: service_completed_successfully

  dashboard:
    <<: *mct-common
    command: streamlit run dashboard/app.py --server.address=0.0.0.0
    ports:
      - "8501:8501"

volumes:
  airflow-state:
```

### 46. `Dockerfile`

**File size:** `346` bytes

```dockerfile
FROM apache/airflow:2.10.5-python3.11

WORKDIR /opt/mct
COPY --chown=airflow:root . /opt/mct
RUN pip install --no-cache-dir ".[analytics]"

ENV MCT_DATA_ROOT=/opt/mct/data \
    MCT_DBT_DATABASE_PATH=/opt/mct/data/mart/mobility_control_tower.duckdb \
    AIRFLOW__CORE__DAGS_FOLDER=/opt/mct/airflow/dags \
    AIRFLOW__CORE__LOAD_EXAMPLES=False
```

## Tests

### 47. `tests/conftest.py`

**File size:** `439` bytes

```python
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def gtfs_zip_bytes() -> bytes:
    fixture_dir = Path(__file__).parent / "fixtures" / "static"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(fixture_dir.glob("*.txt")):
            archive.write(path, path.name)
    return buffer.getvalue()
```

### 48. `tests/fixtures/static/calendar.txt`

**File size:** `124` bytes

```
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
WK,1,1,1,1,1,1,1,20260101,20260103
```

### 49. `tests/fixtures/static/calendar_dates.txt`

**File size:** `60` bytes

```
service_id,date,exception_type
WK,20260102,2
WK,20260104,1
```

### 50. `tests/fixtures/static/routes.txt`

**File size:** `124` bytes

```
route_id,agency_id,route_short_name,route_long_name,route_type
R1,TIS,A,Aéroport - Centre,3
R2,TIS,B,Gare - Université,3
```

### 51. `tests/fixtures/static/stop_times.txt`

**File size:** `215` bytes

```
trip_id,arrival_time,departure_time,stop_id,stop_sequence
T1,08:00:00,08:00:30,S1,1
T1,08:25:00,08:25:30,S2,2
T2,25:05:00,25:05:30,S2,1
T2,25:30:00,25:30:30,S1,2
T3,09:00:00,09:00:30,S2,1
T3,09:20:00,09:20:30,S3,2
```

### 52. `tests/fixtures/static/stops.txt`

**File size:** `122` bytes

```
stop_id,stop_name,stop_lat,stop_lon
S1,Aéroport,43.6293,1.3638
S2,Capitole,43.6044,1.4437
S3,Université,43.5601,1.4637
```

### 53. `tests/fixtures/static/trips.txt`

**File size:** `118` bytes

```
route_id,service_id,trip_id,trip_headsign,direction_id
R1,WK,T1,Centre,0
R1,WK,T2,Aéroport,1
R2,WK,T3,Université,0
```

### 54. `tests/test_cli_and_dbt.py`

**File size:** `4,967` bytes

```python
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mct_solo import cli
from mct_solo.config import db_path, latest_run
from mct_solo.dbt import build_dbt
from mct_solo.quality import require_pass

PASS_REPORT = {"status": "PASS", "checks": []}


def test_config_paths_and_latest_run(tmp_path, monkeypatch) -> None:
    older = tmp_path / "runs" / "a"
    newer = tmp_path / "runs" / "b"
    older.mkdir(parents=True)
    newer.mkdir()
    (older / "manifest.json").write_text("{}", encoding="utf-8")
    (newer / "manifest.json").write_text("{}", encoding="utf-8")

    assert latest_run(tmp_path / "runs") == newer
    assert db_path(tmp_path) == (tmp_path / "mart" / "mobility_control_tower.duckdb").resolve()
    monkeypatch.setenv("MCT_DBT_DATABASE_PATH", str(tmp_path / "custom.duckdb"))
    assert db_path(tmp_path) == (tmp_path / "custom.duckdb").resolve()

    with pytest.raises(FileNotFoundError):
        latest_run(tmp_path / "empty")


def test_dbt_runner_passes_explicit_paths(tmp_path, monkeypatch) -> None:
    static_run = tmp_path / "silver" / "static" / "run"
    static_run.mkdir(parents=True)
    calls: list[tuple[list[str], dict[str, str]]] = []

    monkeypatch.setattr("mct_solo.dbt.shutil.which", lambda _: "dbt")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs["env"]))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("mct_solo.dbt.subprocess.run", fake_run)
    database = build_dbt(static_run, tmp_path)

    command, environment = calls[0]
    variables = json.loads(command[command.index("--vars") + 1])
    assert command[:2] == ["dbt", "build"]
    assert variables["static_path"] == static_run.resolve().as_posix()
    assert variables["on_time_late_seconds"] == 300
    assert variables["min_reliable_sample_size"] == 5
    assert environment["MCT_DBT_DATABASE_PATH"] == str(database)


def test_require_pass_raises_with_failed_names() -> None:
    with pytest.raises(ValueError, match="bad_rows"):
        require_pass({"status": "FAIL", "checks": [{"name": "bad_rows", "status": "FAIL"}]})


def test_cli_dispatches_small_commands(tmp_path, monkeypatch, capsys) -> None:
    raw = tmp_path / "raw-run"
    silver = tmp_path / "silver-run"
    database = tmp_path / "mct.duckdb"
    monkeypatch.setattr(cli, "download_static", lambda source, root: raw)
    monkeypatch.setattr(cli, "transform_static", lambda raw_run, root: silver)
    monkeypatch.setattr(cli, "download_realtime", lambda source, root: {"snapshot_id": "snap-1"})
    monkeypatch.setattr(cli, "latest_run", lambda parent: silver)
    monkeypatch.setattr(cli, "validate_static", lambda run: PASS_REPORT)
    monkeypatch.setattr(cli, "validate_realtime", lambda root: PASS_REPORT)
    monkeypatch.setattr(cli, "ensure_empty_realtime_tables", lambda root: None)
    monkeypatch.setattr(cli, "build_dbt", lambda run, root: database)

    commands = [
        ["ingest-static"],
        ["transform-static", str(raw)],
        ["collect-realtime"],
        ["quality", "static"],
        ["quality", "realtime"],
        ["dbt-build"],
    ]
    for command in commands:
        cli.main(["--data-root", str(tmp_path), *command])
    assert capsys.readouterr().out.count("{") == len(commands)


def test_cli_complete_pipeline_helpers(tmp_path, monkeypatch) -> None:
    raw = tmp_path / "raw-run"
    silver = tmp_path / "silver-run"
    database = tmp_path / "mct.duckdb"
    monkeypatch.setattr(cli, "download_static", lambda source, root: raw)
    monkeypatch.setattr(cli, "transform_static", lambda raw_run, root: silver)
    monkeypatch.setattr(cli, "ensure_empty_realtime_tables", lambda root: None)
    monkeypatch.setattr(cli, "validate_static", lambda run, report: PASS_REPORT)
    monkeypatch.setattr(cli, "validate_realtime", lambda root, report: PASS_REPORT)
    monkeypatch.setattr(cli, "download_realtime", lambda source, root: {"snapshot_id": "snap-1"})
    monkeypatch.setattr(cli, "latest_run", lambda parent: silver)
    monkeypatch.setattr(cli, "build_dbt", lambda run, root: database)

    assert cli._static_pipeline(tmp_path)["database"] == str(database)
    assert cli._static_pipeline(tmp_path, run_dbt=False)["database"] == "not-run"
    assert cli._realtime_pipeline(tmp_path)["snapshot_id"] == "snap-1"
    assert cli._realtime_pipeline(tmp_path, run_dbt=False)["database"] == "not-run"


def test_cli_pipeline_commands(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_static_pipeline", lambda root, run_dbt: {"kind": "static", "dbt": run_dbt})
    monkeypatch.setattr(cli, "_realtime_pipeline", lambda root, run_dbt: {"kind": "realtime", "dbt": run_dbt})
    cli.main(["--data-root", str(tmp_path), "static-pipeline", "--skip-dbt"])
    cli.main(["--data-root", str(tmp_path), "realtime-pipeline"])
    output = capsys.readouterr().out
    assert '"kind": "static"' in output
    assert '"kind": "realtime"' in output
```

### 55. `tests/test_quality.py`

**File size:** `3,137` bytes

```python
from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from test_realtime_pipeline import trip_updates_payload

from mct_solo.config import load_source
from mct_solo.quality import validate_realtime, validate_static
from mct_solo.realtime_pipeline import preserve_realtime_bytes
from mct_solo.static_pipeline import preserve_static_bytes, transform_static


def test_static_quality_passes_fixture(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    silver = transform_static(raw, tmp_path)
    report = validate_static(silver)
    assert report["status"] == "PASS"


def test_static_quality_detects_unknown_route(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    silver = transform_static(raw, tmp_path)
    trips_path = silver / "trips.parquet"
    trips = pd.read_parquet(trips_path)
    trips.loc[0, "route_id"] = "NOT_A_ROUTE"
    trips.to_parquet(trips_path, index=False)

    report = validate_static(silver)
    failed = {check["name"] for check in report["checks"] if check["status"] == "FAIL"}
    assert "trips_reference_routes" in failed


def test_realtime_quality_passes_fixture(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    assert validate_realtime(tmp_path)["status"] == "PASS"


def test_realtime_outlier_is_warned_and_not_a_pipeline_failure(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    path = next((tmp_path / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(path)
    rows.loc[0, "observed_delay"] = -86400
    rows.to_parquet(path, index=False)

    report = validate_realtime(tmp_path)
    assert report["status"] == "WARN"
    assert next(check for check in report["checks"] if check["name"] == "delay_sanity")["problem_count"] == 1


def test_realtime_delay_sanity_boundary_is_inclusive(tmp_path) -> None:
    preserve_realtime_bytes(
        trip_updates_payload(),
        load_source(),
        tmp_path,
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    path = next((tmp_path / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(path)
    boundary_rows = pd.concat([rows.iloc[[0]]] * 5, ignore_index=True)
    boundary_rows["entity_id"] = ["missing", "negative-out", "negative-edge", "positive-edge", "positive-out"]
    boundary_rows["stop_sequence"] = range(101, 106)
    boundary_rows["observed_delay"] = pd.array([None, -7201, -7200, 7200, 7201], dtype="Int64")
    boundary_rows.to_parquet(path, index=False)

    report = validate_realtime(tmp_path)
    delay_check = next(check for check in report["checks"] if check["name"] == "delay_sanity")
    assert report["status"] == "WARN"
    assert delay_check["problem_count"] == 2
```

### 56. `tests/test_realtime_pipeline.py`

**File size:** `1,757` bytes

```python
from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from google.transit import gtfs_realtime_pb2

from mct_solo.config import load_source
from mct_solo.realtime_pipeline import preserve_realtime_bytes


def trip_updates_payload() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_767_268_770
    entity = feed.entity.add()
    entity.id = "update-1"
    update = entity.trip_update
    update.trip.trip_id = "T1"
    update.trip.route_id = "R1"
    update.trip.start_date = "20260101"
    update.timestamp = 1_767_268_775

    first = update.stop_time_update.add()
    first.stop_sequence = 1
    first.stop_id = "S1"
    first.arrival.delay = 120
    first.departure.delay = 999

    second = update.stop_time_update.add()
    second.stop_sequence = 2
    second.stop_id = "S2"
    second.departure.delay = 420
    return feed.SerializeToString()


def test_realtime_parse_preserve_and_retry_are_idempotent(tmp_path) -> None:
    collected_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    first = preserve_realtime_bytes(trip_updates_payload(), load_source(), tmp_path, collected_at=collected_at)
    second = preserve_realtime_bytes(trip_updates_payload(), load_source(), tmp_path, collected_at=collected_at)
    parquet = next((tmp_path / "silver" / "realtime" / "stop_time_updates").glob("date=*/*.parquet"))
    rows = pd.read_parquet(parquet).sort_values("stop_sequence")

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert len(list((tmp_path / "raw" / "realtime").glob("date=*/*/feed.pb"))) == 1
    assert rows["observed_delay"].tolist() == [120, 420]
    assert first["feed_age_seconds"] == 30
```

### 57. `tests/test_static_pipeline.py`

**File size:** `1,608` bytes

```python
from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from mct_solo.config import load_source
from mct_solo.static_pipeline import gtfs_time_to_seconds, preserve_static_bytes, transform_static


def test_gtfs_time_supports_after_midnight_service() -> None:
    assert gtfs_time_to_seconds("25:05:30") == 90330
    assert gtfs_time_to_seconds("") is None


def test_static_raw_bronze_and_silver(tmp_path, gtfs_zip_bytes: bytes) -> None:
    moment = datetime(2026, 1, 1, 12, tzinfo=UTC)
    raw = preserve_static_bytes(
        gtfs_zip_bytes, load_source(), tmp_path, source_url="https://example.test/gtfs.zip", ingested_at=moment
    )
    silver = transform_static(raw, tmp_path)

    raw_metadata = json.loads((raw / "metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((silver / "manifest.json").read_text(encoding="utf-8"))
    stop_times = pd.read_parquet(silver / "stop_times.parquet")

    assert (raw / "gtfs.zip").read_bytes() == gtfs_zip_bytes
    assert raw_metadata["source_url"] == "https://example.test/gtfs.zip"
    assert len(raw_metadata["sha256"]) == 64
    assert (tmp_path / "bronze" / "static" / raw.name / "routes.txt").is_file()
    assert manifest["row_counts"]["trips"] == 3
    assert stop_times.loc[stop_times["trip_id"] == "T2", "departure_seconds"].min() == 90330


def test_transform_is_idempotent_for_one_raw_run(tmp_path, gtfs_zip_bytes: bytes) -> None:
    raw = preserve_static_bytes(gtfs_zip_bytes, load_source(), tmp_path)
    assert transform_static(raw, tmp_path) == transform_static(raw, tmp_path)
```

## Scripts / Tooling

### 58. `scripts/create_ci_fixture.py`

**File size:** `2,220` bytes

```python
"""Create deterministic Parquet inputs for CI; this is not real-source evidence."""

from __future__ import annotations

import io
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from google.transit import gtfs_realtime_pb2

from mct_solo.config import load_source
from mct_solo.realtime_pipeline import ensure_empty_realtime_tables, preserve_realtime_bytes
from mct_solo.static_pipeline import preserve_static_bytes, transform_static

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def gtfs_fixture() -> bytes:
    buffer = io.BytesIO()
    fixture_dir = PROJECT_ROOT / "tests" / "fixtures" / "static"
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(fixture_dir.glob("*.txt")):
            archive.write(path, path.name)
    return buffer.getvalue()


def realtime_fixture() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_767_268_770
    entity = feed.entity.add()
    entity.id = "ci-update-1"
    update = entity.trip_update
    update.trip.trip_id = "T1"
    update.trip.route_id = "R1"
    update.trip.start_date = "20260101"
    update.timestamp = 1_767_268_775
    first = update.stop_time_update.add()
    first.stop_sequence = 1
    first.stop_id = "S1"
    first.arrival.delay = 120
    second = update.stop_time_update.add()
    second.stop_sequence = 2
    second.stop_id = "S2"
    second.departure.delay = 420
    return feed.SerializeToString()


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else PROJECT_ROOT / "data" / "ci").resolve()
    source = load_source()
    raw = preserve_static_bytes(
        gtfs_fixture(),
        source,
        root,
        source_url="fixture://tisseo-static",
        ingested_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    silver = transform_static(raw, root)
    ensure_empty_realtime_tables(root)
    preserve_realtime_bytes(
        realtime_fixture(),
        source,
        root,
        source_url="fixture://tisseo-trip-updates",
        collected_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    print(silver)


if __name__ == "__main__":
    main()
```

## Documentation

### 59. `PROJECT_PLAN.md`

**File size:** `10,667` bytes

````markdown
# Mobility Control Tower — Solo Rebuild Plan

## Goal and scope

Build a believable one-month Data Engineering portfolio project for one network: Tisséo in Toulouse. The project answers one question: **how does observed service compare with the published schedule, and how does reliability evolve over time?**

Only two public sources are in scope:

- GTFS Schedule (daily archive)
- GTFS-Realtime Trip Updates (scheduled polling)

Missing realtime updates remain unknown. They are never converted into cancellations or on-time observations.

## Final architecture

```text
Tisséo GTFS Schedule       Tisséo GTFS-RT Trip Updates
          |                              |
          +---------- Python ------------+
                         |
            immutable Raw + metadata
                         |
              normalized Silver Parquet
                         |
                   dbt + DuckDB
                         |
                  six Gold marts
                         |
             Streamlit (direct SQL reads)

Airflow: two small orchestration DAGs
Docker Compose: Airflow + dashboard
GitHub Actions: lint, unit tests, fixture dbt build
```

Python owns downloads, raw preservation, GTFS parsing, GTFS-RT protobuf parsing, Silver Parquet, and lightweight pre-dbt checks. dbt owns analytical joins, definitions, tests, and Gold marts. DuckDB stores dbt outputs. Streamlit is read-only and does not introduce an API layer.

## Concepts reused from the reference project

- Preserve source bytes before transforming them.
- Record source URL, UTC ingestion time, SHA-256 checksum, size, row counts, and feed header time where available.
- Keep static and realtime identifiers unchanged so compatibility can be measured.
- Partition historical realtime Parquet by collection date.
- Use arrival delay when present and departure delay as a documented fallback.
- Make feed freshness and realtime/static match coverage visible.
- Keep dbt authoritative for Gold analytics.
- Treat missing observations as unknown rather than as on-time service or cancellation evidence.

These are concepts, not copied subsystems. The new implementation uses a much smaller module and model surface.

## Deliberately removed

- Multi-city configuration and provider abstractions
- Vehicle Positions and Service Alerts
- FastAPI and all authentication, rate limiting, and mutation endpoints
- Incident detection, lifecycle, persistence, and operator workflows
- PostgreSQL application storage
- Prometheus, Grafana, and alerting infrastructure
- OpenLineage, S3 adapters, benchmarking, backup/restore, failure injection
- Reverse proxies, TLS, production Compose overlays, release-evidence automation
- Python-built Gold metrics and parallel KPI implementations
- Maintenance DAGs and broad command surfaces

## Proposed directory tree

```text
mct_solo/
├── PROJECT_PLAN.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── config/
│   └── source.yml
├── src/mct_solo/
│   ├── __init__.py
│   ├── config.py
│   ├── io.py
│   ├── static_pipeline.py
│   ├── realtime_pipeline.py
│   ├── quality.py
│   ├── dbt.py
│   └── cli.py
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/{staging,intermediate,marts}/
│   └── tests/
├── airflow/dags/
│   ├── static_gtfs_pipeline.py
│   └── realtime_pipeline.py
├── dashboard/app.py
├── scripts/create_ci_fixture.py
├── tests/
│   ├── fixtures/static/
│   ├── test_static_pipeline.py
│   ├── test_realtime_pipeline.py
│   └── test_quality.py
└── .github/workflows/ci.yml
```

Generated `data/`, dbt targets, local DuckDB files, Airflow logs, caches, and coverage output are ignored.

## Pipeline stages

### Static GTFS pipeline

1. Download the official GTFS ZIP with a timeout and HTTP validation.
2. Save the unchanged ZIP under `data/raw/static/<run_id>/`.
3. Write provenance metadata including URL, timestamp, SHA-256, byte size, and ZIP members.
4. Read required GTFS tables and normalize only types needed downstream.
5. Write `routes`, `trips`, `stops`, `stop_times`, `calendar`, and `calendar_dates` as Silver Parquet plus a manifest with row counts.
6. Run focused Python integrity checks.
7. Build and test dbt models in DuckDB.

### Realtime pipeline

1. Fetch one official GTFS-RT Trip Updates protobuf snapshot.
2. Derive an idempotent snapshot identifier from feed timestamp and content checksum.
3. Preserve the protobuf and provenance metadata under Raw.
4. Parse trip updates, stop-time updates, feed header time, schedule relationship, and delays.
5. Write append-only, date-partitioned Silver Parquet for snapshots, trip updates, and stop-time updates. A retry of the same snapshot does not append duplicate Silver rows.
6. Check delay sanity, required identifiers, feed age, and within-snapshot key uniqueness.
7. Rebuild/update dbt models and run dbt tests.

This is scheduled polling, not event streaming.

## dbt models

### Staging

- `stg_routes`: route names and type
- `stg_trips`: trip, route, service, and direction identifiers
- `stg_stop_times`: stop sequence and parsed scheduled time seconds
- `stg_calendar`: regular weekday service windows
- `stg_calendar_dates`: added/removed service exceptions
- `stg_realtime_updates`: normalized stop-time delay observations
- `stg_feed_snapshots`: collection and feed freshness metadata

### Intermediate

- `int_service_dates`: expands regular calendars and applies exceptions
- `int_scheduled_trips`: scheduled trips by route and service date
- `int_delay_observations`: deduplicated realtime observations matched to static trips and scheduled stop times

### Gold marts

- `route_daily_service`: scheduled trips and departures by route/day
- `route_delay_summary`: observed delay distribution and on-time percentage by route/day
- `hourly_delay_summary`: observed delays by scheduled service hour/day
- `network_on_time_performance`: daily network OTP over known delay observations
- `realtime_coverage`: observed matched trips divided by eligible scheduled trips by day
- `feed_freshness`: per-snapshot feed age and a documented freshness status

The on-time definition is delay between **-60 and +300 seconds inclusive**. Delay is arrival delay when available, otherwise departure delay. Percentages use only eligible known observations. Coverage is reported separately.

## Airflow DAGs

1. `static_gtfs_pipeline` (daily): download/preserve → transform to Silver → Python quality checks → dbt build/test.
2. `realtime_pipeline` (every five minutes): fetch/preserve/parse one snapshot → realtime quality checks → dbt build/test against the latest static Silver run.

No maintenance or platform-management DAGs are planned.

## Test strategy

- Unit tests build tiny deterministic GTFS ZIPs and GTFS-RT protobufs.
- Static tests verify raw immutability metadata, time parsing including values after 24:00, Silver schemas, and relationship failures.
- Realtime tests verify protobuf parsing, arrival/departure delay fallback inputs, freshness metadata, and idempotent writes.
- Quality tests cover identifier relationships, delay sanity bounds, and duplicate keys.
- dbt schema tests cover not-null, unique, relationships, and accepted values.
- Custom dbt assertions cover percentage bounds, delay bounds, coverage reconciliation, and the rule that unobserved service is not counted as on-time.
- CI creates deterministic Parquet fixtures and executes a real `dbt build`; fixture success is identified as CI evidence, not real-data evidence.
- Development includes separate real-source smoke commands. Any command not executed or component not available is reported as unverified.

## Dashboard scope

One Streamlit app with three pages:

1. **Network Overview** — scheduled service, known observations, network OTP, and hourly delay trend.
2. **Route Reliability** — route/date filter, delay distribution summary, observed sample size, and low-coverage warning.
3. **Data Quality / Feed Health** — feed age trend, latest freshness, match coverage, and explicit explanation of unknown observations.

The dashboard queries trusted dbt tables directly from DuckDB and performs no KPI recomputation.

## Implementation phases

1. **Scope and foundation** — plan, packaging, configuration, paths, CLI, ignores.
2. **Static pipeline** — raw preservation, Silver conversion, metadata, unit tests.
3. **Realtime history** — polling snapshot, protobuf parser, idempotent Parquet append, unit tests.
4. **Analytics engineering** — compact dbt graph, KPI definitions, schema/custom tests, deterministic fixture build.
5. **Presentation and orchestration** — three-page dashboard, two Airflow DAGs, Docker Compose.
6. **Evidence and documentation** — real-data smoke test where reachable, broad validation, README with honest limitations.

## Final acceptance criteria

- All authored files are inside `mct_solo/`; the reference project is unchanged.
- Exactly one network and two source feeds are configured.
- Raw GTFS and GTFS-RT bytes are retained with provenance and checksums.
- Static and realtime Silver data are Parquet and inspectable.
- A repeated realtime retry cannot duplicate a Silver snapshot.
- Six compact, documented dbt Gold marts answer the stated analytical question.
- dbt and Python checks keep unknown realtime observations out of OTP and cancellation claims.
- Two DAGs cover only the important static and realtime workflows.
- The dashboard has no more than three pages and reads DuckDB directly.
- Docker Compose documents reproducible local startup.
- One CI workflow runs lint, pytest, and a deterministic dbt build/test.
- A real Tisséo smoke test is attempted and its actual outcome is documented without conflating it with fixtures.
- README explains the problem, architecture, sources, KPI definitions, setup, example queries, limitations, and sensible future work.
- The project stays close to 30–60 meaningful files and remains explainable by a junior Data Engineer.

## Reference audit note

The requested `33.md` was not present in the repository at planning time. The existing source tree, its focused GTFS/GTFS-RT modules, documentation, dbt graph, and the large `Mobility_Control_Tower.md` project-history document were inspected as reference material. This absence does not change the deliberately smaller target scope.
````

### 60. `README.md`

**File size:** `10,870` bytes

````markdown
# Mobility Control Tower

A compact, local-first Data Engineering portfolio project that compares Tisséo’s planned public transport service in Toulouse with observations from scheduled GTFS-Realtime Trip Updates polling.

This project is intentionally sized for a Master’s student or junior Data Engineer. It demonstrates source ingestion, immutable raw storage, typed Parquet, analytics engineering with dbt, orchestration, data quality, and a small dashboard without presenting itself as an enterprise platform.

## Business question

> How does observed public transport service compare with the planned schedule, and how does reliability evolve over time?

The analytical contract is conservative: a trip without a realtime observation is **unknown**. It is not assumed cancelled and is not counted as on-time.

## Architecture

```text
Official Tisséo GTFS Schedule      GTFS-RT Trip Updates
               |                           |
               +-------- Python -----------+
                            |
                Raw bytes + provenance
                            |
          Bronze extraction / Silver Parquet
                            |
                      dbt + DuckDB
                            |
                     six Gold marts
                            |
                 three-page Streamlit app

        Airflow schedules two workflows locally
```

Python owns source collection and normalization. dbt owns all analytical KPI logic. Streamlit reads trusted dbt tables directly from DuckDB, so there is no API layer or second KPI implementation.

## Real public sources

- Dataset page: [Tisséo — Réseau transport urbain toulousain](https://transport.data.gouv.fr/datasets/tisseo-reseau-transport-urbain-toulousain)
- GTFS Schedule: configured official Toulouse Métropole download URL
- GTFS-Realtime Trip Updates: `https://api.tisseo.fr/opendata/gtfsrt/GtfsRt.pb`
- Licence recorded from the source: ODbL

The URLs and freshness thresholds live in `config/source.yml`. Only Tisséo is supported. Vehicle Positions and Service Alerts are deliberately out of scope.

## Pipeline

The daily static workflow downloads the ZIP, saves it unchanged with a SHA-256 checksum, extracts selected GTFS text files into Bronze, writes six typed Silver Parquet tables, checks identifiers and relationships, then runs dbt.

The five-minute realtime workflow fetches one protobuf snapshot, saves the original bytes and metadata, parses Trip Updates into partitioned Silver Parquet, checks keys and published delays, then refreshes dbt. Snapshot IDs combine the publisher header timestamp and content checksum, so a retry of identical content does not append duplicate Silver rows.

Each raw metadata file records the source URL, UTC ingestion time, checksum, byte size, HTTP metadata, feed timestamp where applicable, and row counts. Generated data is stored under `data/` and ignored by Git.

## Gold marts and KPI definitions

| Mart | Grain and definition |
| --- | --- |
| `route_daily_service` | Route/service date; distinct scheduled trips and scheduled stop departures. |
| `route_delay_summary` | Route/service date; distribution and on-time share over matched stop updates with a valid known delay, plus `sample_size_status`. |
| `hourly_delay_summary` | Service date/scheduled hour; delay and on-time trend plus `sample_size_status`. Times after 24:00 wrap to clock hour while staying on their GTFS service date. |
| `network_on_time_performance` | Service date; on-time observations divided by matched observations with a valid known delay. |
| `realtime_coverage` | Service date; distinct matched observed trips divided by eligible scheduled trips on a date with at least one collected snapshot. |
| `feed_freshness` | Snapshot; collection time minus the publisher’s feed-header timestamp. |

An observation is on-time when its delay is between **−60 and +300 seconds inclusive**. Arrival delay is preferred; departure delay is used only when arrival delay is absent. Published delay values outside ±7,200 seconds are preserved and flagged `OUT_OF_RANGE`, but excluded from reliability KPIs. Rows without delay remain `MISSING`. Neither category enters the OTP denominator.

Coverage and OTP answer different questions. Low coverage makes an OTP estimate less representative, which is why both are shown rather than filling missing values.

Route-day and hourly rows are marked `RELIABLE` when they contain at least `min_reliable_sample_size` observations
(5 by default); smaller groups remain visible and are marked `LOW_SAMPLE`. The dashboard warns about these rows rather
than hiding them.

## Data quality

Python checks the file-level and parsing boundary:

- required GTFS files and identifiers;
- unique route, trip, stop, and stop-sequence keys;
- trip-to-route and stop-time relationships;
- GTFS time syntax, including service times after 24:00;
- unique realtime entity/stop keys;
- delay sanity with explicit warnings for preserved outliers.

dbt adds `not_null`, `unique`, `relationships`, and `accepted_values` tests plus business assertions for percentage bounds, coverage reconciliation, delay eligibility, and OTP numerator/denominator reconciliation.

## Local setup

Python 3.11 is the supported local version.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev,analytics]"
```

Run the static workflow, collect several realtime snapshots over time, and refresh analytics:

```bash
mct static-pipeline
mct collect-realtime
mct dbt-build
```

For one full realtime poll including checks and dbt:

```bash
mct realtime-pipeline
```

Launch the dashboard after a dbt build:

```bash
streamlit run dashboard/app.py
```

Local URLs under Docker Compose are Streamlit at `http://localhost:8501` and Airflow at `http://localhost:8080` (`airflow` / `airflow` for local use).

## Deterministic development and CI

Fixture evidence is intentionally separate from live-source evidence:

```bash
python scripts/create_ci_fixture.py data/ci
mct --data-root data/ci dbt-build \
  --static-run data/ci/silver/static/20260101T120000000000Z
```

The one GitHub Actions workflow runs Ruff, Black, isort, MyPy, pytest with an 80% coverage floor, a real dbt build/test over generated deterministic Parquet fixtures, and a Docker image build. The nested `.github/workflows/ci.yml` is intended to move with `mct_solo/` when this independent project becomes its own repository root.

## Airflow and Docker Compose

There are exactly two DAGs:

- `static_gtfs_pipeline`: preserve → Silver → quality → dbt build/test
- `realtime_pipeline`: fetch/parse/append → quality → dbt build/test

Start the local environment with:

```bash
cp .env.example .env
docker compose up --build -d
```

Airflow uses SQLite and the SequentialExecutor inherited from its local default. That choice keeps the portfolio environment understandable; it is not a high-availability deployment design. The scheduler, webserver, and dashboard share the ignored local `data/` volume.

## Dashboard

The Streamlit app has three pages only:

1. **Network Overview** — scheduled service, known observations, network OTP, and hourly delay.
2. **Route Reliability** — route-level sample size, median/P90 delay, and on-time trend.
3. **Data Quality / Feed Health** — freshness history, realtime coverage, and unknown-status explanation.

The app displays empty-state messages when no eligible delay observations exist rather than inventing zero-valued performance.

## Real-data smoke evidence

A live smoke run was executed on **2026-09-23** against both configured Tisséo URLs:

- Static Raw → Bronze → Silver and Python checks completed.
- Static Silver contained 124 routes, 40,427 trips, 5,721 stops, and 902,869 stop-time rows.
- Two Trip Updates snapshots were fetched and parsed with feed ages of 4 and 2 seconds.
- The real-data dbt build completed successfully: 16 models and 38 tests, 54 operations total.
- Realtime/static coverage for the sampled service date was 32 matched trips out of 12,902 scheduled trips (0.25%).
- The two late-evening snapshots published no delay value eligible under the ±7,200-second sanity rule: 844 populated delays were approximately one day negative and were flagged `OUT_OF_RANGE`; 849 observations had no delay. Network OTP therefore correctly remained unknown/empty.

This is a short smoke test, not evidence of representative network reliability. It demonstrates that the real source can be collected, preserved, normalized, joined, tested, and served while invalid or absent observations remain explicit.

## Example analytical queries

```sql
-- Daily network reliability over eligible observations only
select *
from network_on_time_performance
order by service_date desc;

-- Routes with the worst observed P90 delay, keeping sample size visible
select route_short_name, observed_trips, p90_delay_seconds, on_time_percentage
from route_delay_summary
where service_date = current_date
order by p90_delay_seconds desc;

-- Coverage: unknown trips are explicit, not classified as on-time/cancelled
select service_date, eligible_scheduled_trips, observed_matched_trips,
       trips_with_unknown_status, coverage_percentage
from realtime_coverage
order by service_date desc;
```

## Limitations

- GTFS-RT is polled, not streamed. Results depend on poll cadence and collection duration.
- Trip Updates describe predictions/updates, not independently measured passenger arrivals.
- Tisséo’s sampled Trip Updates omitted `start_date` and showed low static trip-ID compatibility.
- When `start_date` is absent, the fallback uses the Europe/Paris observation date; this remains approximate because wall-clock observation time does not identify the trip’s actual scheduled service day.
- Source-published delay anomalies are excluded rather than guessed or silently corrected.
- OTP is observation-weighted, not passenger-weighted, and should be read alongside coverage.
- DuckDB and SQLite-backed local Airflow are appropriate for this portfolio scope, not concurrent production workloads.
- The dashboard and Docker Compose were designed for local demonstration; availability, authentication, and TLS are out of scope.

## Sensible future improvements

- Collect daytime and peak-period snapshots for several weeks before interpreting reliability trends.
- Investigate Tisséo trip-ID and service-day semantics with source documentation and retain any reconciliation rule as a tested, source-specific transformation.
- Add a small retention policy only if local history growth becomes a practical issue.
- Move this folder to its own repository so its included GitHub Actions workflow runs natively.

The detailed implementation boundary and acceptance criteria are in [PROJECT_PLAN.md](PROJECT_PLAN.md).
````

## Other System Files

### 61. `dashboard/app.py`

**File size:** `7,112` bytes

```python
"""Read-only Streamlit dashboard over dbt-owned DuckDB marts."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "mart" / "mobility_control_tower.duckdb"
DB_PATH = Path(os.environ.get("MCT_DBT_DATABASE_PATH", DEFAULT_DB))


@st.cache_data(ttl=60)
def query(sql: str, parameters: list[object] | None = None) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        return connection.execute(sql, parameters or []).fetchdf()


def network_overview() -> None:
    st.header("Network Overview")
    latest = query(
        """
        select * from network_on_time_performance
        order by service_date desc limit 1
        """
    )
    scheduled = query(
        """
        select service_date, sum(scheduled_trips) as scheduled_trips,
               sum(scheduled_departures) as scheduled_departures
        from route_daily_service group by 1 order by 1 desc limit 1
        """
    )
    columns = st.columns(4)
    columns[0].metric(
        "Latest service date", str(latest.iloc[0]["service_date"]) if not latest.empty else "No observations"
    )
    columns[1].metric("Scheduled trips", f"{scheduled.iloc[0]['scheduled_trips']:,.0f}" if not scheduled.empty else "—")
    columns[2].metric(
        "Known delay observations", f"{latest.iloc[0]['observed_stop_updates']:,.0f}" if not latest.empty else "—"
    )
    columns[3].metric("On-time", f"{latest.iloc[0]['on_time_percentage']:.1f}%" if not latest.empty else "—")

    hourly = query(
        """
        select service_date, service_hour, average_delay_seconds, on_time_percentage,
               observed_stop_updates, sample_size_status
        from hourly_delay_summary order by service_date, service_hour
        """
    )
    st.subheader("Delay by scheduled service hour")
    if hourly.empty:
        st.info("Collect Trip Updates and rebuild dbt to populate observed reliability charts.")
    else:
        date = st.selectbox("Service date", sorted(hourly["service_date"].unique(), reverse=True))
        selected = hourly[hourly["service_date"] == date].set_index("service_hour")
        low_sample_count = int((selected["sample_size_status"] == "LOW_SAMPLE").sum())
        if low_sample_count:
            st.warning(
                f"{low_sample_count} hourly row(s) are flagged LOW_SAMPLE because they are below the configured "
                "reliability threshold."
            )
        st.line_chart(selected[["average_delay_seconds", "on_time_percentage"]])
        st.caption(
            "The two series use different units: seconds and percent. Hover for exact values and sample sizes below."
        )
        st.dataframe(selected.reset_index(), use_container_width=True, hide_index=True)


def route_reliability() -> None:
    st.header("Route Reliability")
    routes = query(
        """
        select distinct route_id, coalesce(route_short_name, route_id) as route_label
        from route_delay_summary order by route_label
        """
    )
    if routes.empty:
        st.info("No matched delay observations are available yet.")
        return
    labels = dict(zip(routes["route_label"], routes["route_id"], strict=True))
    label = st.selectbox("Route", list(labels))
    summary = query(
        """
        select service_date, route_short_name, route_long_name, observed_trips,
               observed_stop_updates, average_delay_seconds, median_delay_seconds,
               p90_delay_seconds, on_time_percentage, sample_size_status
        from route_delay_summary where route_id = ? order by service_date
        """,
        [labels[label]],
    )
    latest = summary.iloc[-1]
    low_sample_count = int((summary["sample_size_status"] == "LOW_SAMPLE").sum())
    if low_sample_count:
        st.warning(
            f"{low_sample_count} route-day row(s) are flagged LOW_SAMPLE because they are below the configured "
            "reliability threshold."
        )
    columns = st.columns(5)
    columns[0].metric("Observed trips", f"{latest['observed_trips']:,.0f}")
    columns[1].metric("On-time", f"{latest['on_time_percentage']:.1f}%")
    columns[2].metric("Median delay", f"{latest['median_delay_seconds']:.0f} s")
    columns[3].metric("P90 delay", f"{latest['p90_delay_seconds']:.0f} s")
    columns[4].metric("Sample confidence", latest["sample_size_status"])
    st.line_chart(
        summary.set_index("service_date")[["average_delay_seconds", "median_delay_seconds", "p90_delay_seconds"]]
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption("Statistics cover matched stop-time updates with a known delay; they are not passenger-weighted.")


def feed_health() -> None:
    st.header("Data Quality / Feed Health")
    freshness = query(
        """
        select collected_at, feed_age_seconds, freshness_status, entity_count,
               trip_update_count, stop_time_update_count
        from feed_freshness order by collected_at
        """
    )
    coverage = query("select * from realtime_coverage order by service_date")
    if freshness.empty:
        st.warning("No realtime snapshots have been collected.")
    else:
        latest = freshness.iloc[-1]
        columns = st.columns(3)
        columns[0].metric("Latest feed status", latest["freshness_status"])
        columns[1].metric(
            "Feed age", f"{latest['feed_age_seconds']} s" if pd.notna(latest["feed_age_seconds"]) else "Unknown"
        )
        columns[2].metric("Trip updates", f"{latest['trip_update_count']:,.0f}")
        st.line_chart(freshness.set_index("collected_at")[["feed_age_seconds"]])
        st.dataframe(
            freshness.tail(20).sort_values("collected_at", ascending=False), use_container_width=True, hide_index=True
        )

    st.subheader("Realtime/static match coverage")
    if coverage.empty:
        st.info("Coverage is calculated only for service dates on which at least one feed snapshot was collected.")
    else:
        st.bar_chart(coverage.set_index("service_date")[["coverage_percentage"]])
        st.dataframe(coverage, use_container_width=True, hide_index=True)
    st.warning(
        "Trips without a matching realtime observation remain UNKNOWN. They are not counted as cancelled or on-time."
    )


def main() -> None:
    st.set_page_config(page_title="Mobility Control Tower", page_icon="🚇", layout="wide")
    st.title("Mobility Control Tower — Toulouse")
    st.caption("Tisséo GTFS Schedule compared with scheduled GTFS-Realtime Trip Updates polling")
    if not DB_PATH.is_file():
        st.error(f"DuckDB file not found at {DB_PATH}. Run a pipeline before opening the dashboard.")
        st.stop()
    page = st.sidebar.radio("Page", ("Network Overview", "Route Reliability", "Data Quality / Feed Health"))
    if page == "Network Overview":
        network_overview()
    elif page == "Route Reliability":
        route_reliability()
    else:
        feed_health()


if __name__ == "__main__":
    main()
```

### 62. `data/ci-dbt111/bronze/static/20260101T120000000000Z/calendar.txt`

**File size:** `124` bytes

```
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
WK,1,1,1,1,1,1,1,20260101,20260103
```

### 63. `data/ci-dbt111/bronze/static/20260101T120000000000Z/calendar_dates.txt`

**File size:** `60` bytes

```
service_id,date,exception_type
WK,20260102,2
WK,20260104,1
```

### 64. `data/ci-dbt111/bronze/static/20260101T120000000000Z/manifest.json`

**File size:** `255` bytes

```json
{
  "run_id": "20260101T120000000000Z",
  "raw_run": "D:\\wsl\\projects\\Mobility_Control_Tower\\mct_solo\\data\\ci-dbt111\\raw\\static\\20260101T120000000000Z",
  "source_sha256": "1303f0ad32fb5f9321fa47d03f89300566e3efc6236022e4766f9e20dfc81848"
}
```

### 65. `data/ci-dbt111/bronze/static/20260101T120000000000Z/routes.txt`

**File size:** `124` bytes

```
route_id,agency_id,route_short_name,route_long_name,route_type
R1,TIS,A,Aéroport - Centre,3
R2,TIS,B,Gare - Université,3
```

### 66. `data/ci-dbt111/bronze/static/20260101T120000000000Z/stop_times.txt`

**File size:** `215` bytes

```
trip_id,arrival_time,departure_time,stop_id,stop_sequence
T1,08:00:00,08:00:30,S1,1
T1,08:25:00,08:25:30,S2,2
T2,25:05:00,25:05:30,S2,1
T2,25:30:00,25:30:30,S1,2
T3,09:00:00,09:00:30,S2,1
T3,09:20:00,09:20:30,S3,2
```

### 67. `data/ci-dbt111/bronze/static/20260101T120000000000Z/stops.txt`

**File size:** `122` bytes

```
stop_id,stop_name,stop_lat,stop_lon
S1,Aéroport,43.6293,1.3638
S2,Capitole,43.6044,1.4437
S3,Université,43.5601,1.4637
```

### 68. `data/ci-dbt111/bronze/static/20260101T120000000000Z/trips.txt`

**File size:** `118` bytes

```
route_id,service_id,trip_id,trip_headsign,direction_id
R1,WK,T1,Centre,0
R1,WK,T2,Aéroport,1
R2,WK,T3,Université,0
```

### 69. `data/ci-dbt111/raw/realtime/date=2026-01-01/1767268770-7f86c755c925/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 70. `data/ci-dbt111/raw/static/20260101T120000000000Z/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 71. `data/ci-dbt111/silver/static/20260101T120000000000Z/manifest.json`

**File size:** `403` bytes

```json
{
  "run_id": "20260101T120000000000Z",
  "source_id": "tisseo",
  "source_url": "fixture://tisseo-static",
  "source_sha256": "1303f0ad32fb5f9321fa47d03f89300566e3efc6236022e4766f9e20dfc81848",
  "transformed_at": "2026-09-23T23:04:29.800958+00:00",
  "row_counts": {
    "routes": 2,
    "trips": 3,
    "stops": 3,
    "stop_times": 6,
    "calendar": 1,
    "calendar_dates": 2
  }
}
```

### 72. `data/ci/bronze/static/20260101T120000000000Z/calendar.txt`

**File size:** `124` bytes

```
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
WK,1,1,1,1,1,1,1,20260101,20260103
```

### 73. `data/ci/bronze/static/20260101T120000000000Z/calendar_dates.txt`

**File size:** `60` bytes

```
service_id,date,exception_type
WK,20260102,2
WK,20260104,1
```

### 74. `data/ci/bronze/static/20260101T120000000000Z/manifest.json`

**File size:** `248` bytes

```json
{
  "run_id": "20260101T120000000000Z",
  "raw_run": "D:\\wsl\\projects\\Mobility_Control_Tower\\mct_solo\\data\\ci\\raw\\static\\20260101T120000000000Z",
  "source_sha256": "1303f0ad32fb5f9321fa47d03f89300566e3efc6236022e4766f9e20dfc81848"
}
```

### 75. `data/ci/bronze/static/20260101T120000000000Z/routes.txt`

**File size:** `124` bytes

```
route_id,agency_id,route_short_name,route_long_name,route_type
R1,TIS,A,Aéroport - Centre,3
R2,TIS,B,Gare - Université,3
```

### 76. `data/ci/bronze/static/20260101T120000000000Z/stop_times.txt`

**File size:** `215` bytes

```
trip_id,arrival_time,departure_time,stop_id,stop_sequence
T1,08:00:00,08:00:30,S1,1
T1,08:25:00,08:25:30,S2,2
T2,25:05:00,25:05:30,S2,1
T2,25:30:00,25:30:30,S1,2
T3,09:00:00,09:00:30,S2,1
T3,09:20:00,09:20:30,S3,2
```

### 77. `data/ci/bronze/static/20260101T120000000000Z/stops.txt`

**File size:** `122` bytes

```
stop_id,stop_name,stop_lat,stop_lon
S1,Aéroport,43.6293,1.3638
S2,Capitole,43.6044,1.4437
S3,Université,43.5601,1.4637
```

### 78. `data/ci/bronze/static/20260101T120000000000Z/trips.txt`

**File size:** `118` bytes

```
route_id,service_id,trip_id,trip_headsign,direction_id
R1,WK,T1,Centre,0
R1,WK,T2,Aéroport,1
R2,WK,T3,Université,0
```

### 79. `data/ci/raw/realtime/date=2026-01-01/1767268770-7f86c755c925/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 80. `data/ci/raw/static/20260101T120000000000Z/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 81. `data/ci/silver/static/20260101T120000000000Z/manifest.json`

**File size:** `403` bytes

```json
{
  "run_id": "20260101T120000000000Z",
  "source_id": "tisseo",
  "source_url": "fixture://tisseo-static",
  "source_sha256": "1303f0ad32fb5f9321fa47d03f89300566e3efc6236022e4766f9e20dfc81848",
  "transformed_at": "2026-09-23T22:50:45.793403+00:00",
  "row_counts": {
    "routes": 2,
    "trips": 3,
    "stops": 3,
    "stop_times": 6,
    "calendar": 1,
    "calendar_dates": 2
  }
}
```

### 82. `data/real-smoke/bronze/static/20260923T225641454289Z/calendar.txt`

**File size:** `89` bytes

```
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
```

### 83. `data/real-smoke/bronze/static/20260923T225641454289Z/manifest.json`

**File size:** `256` bytes

```json
{
  "run_id": "20260923T225641454289Z",
  "raw_run": "D:\\wsl\\projects\\Mobility_Control_Tower\\mct_solo\\data\\real-smoke\\raw\\static\\20260923T225641454289Z",
  "source_sha256": "1ff762e320c9327cee9d9d986664a2cab46daaf68a42a295cc76eb2b2a4d0de6"
}
```

### 84. `data/real-smoke/bronze/static/20260923T225641454289Z/routes.txt`

**File size:** `9,531` bytes

```
route_id,agency_id,route_short_name,route_long_name,route_color,route_text_color,route_type
line:142,network:1,13,Saint Cyprien - République / Oncopole Courrière,3f2682,ffffff,3
line:8,network:1,15,Jeanne d'Arc / Etats-Unis Fondeyre,a0670f,ffffff,3
line:143,network:1,18,Basso Cambo / Arènes ou Cité Scolaire Rive-Gauche,e46809,ffffff,3
line:10,network:1,19,Borderouge / Argoulets,58ac25,ffffff,3
line:12,network:1,20,Balma - Gramont / Beaupuy Mairie,007c52,ffffff,3
line:72,network:1,21,Basso Cambo / Colomiers Airbus,007c52,ffffff,3
line:74,network:1,23,Jeanne d'Arc / La Terrasse,a0670f,ffffff,3
line:90,network:1,25,Oncopole Courrière / Colomiers Gare SNCF,3f2682,ffffff,3
line:75,network:1,26,Borderouge / Montberon,a0670f,ffffff,3
line:76,network:1,27,Toulouse-Lautrec Négreneys / Ramonville,58ac25,ffffff,3
line:84,network:1,29,Jeanne d'Arc / Fonbeauzard Mermoz,dc006b,ffffff,3
line:96,network:1,30,Aéroport / MEETT,0098d4,ffffff,3
line:139,network:1,31,Guyenne - Berry / Aéroport,dc006b,ffffff,3
line:14,network:1,32,Colomiers Ramassiers Gare SNCF / Léguevin Collège,a0670f,ffffff,3
line:63,network:1,33,Argoulets / Gratentour Gravette,0098d4,ffffff,3
line:73,network:1,34,Université Paul Sabatier / Arènes,e46809,ffffff,3
line:64,network:1,35,Colomiers Ramassiers Gare SNCF / Arènes Romaines,58ac25,ffffff,3
line:65,network:1,37,Jolimont / Ramonville,004687,ffffff,3
line:16,network:1,39,Jeanne d'Arc / Amouroux,007c52,ffffff,3
line:17,network:1,40,Borderouge / L'Union Malbou,dc006b,ffffff,3
line:18,network:1,41,Borderouge / Chaussas,e46809,ffffff,3
line:19,network:1,42,Borderouge / Saint-Jean Clinique de L'Union,e46809,ffffff,3
line:62,network:1,43,Argoulets / Saint-Jean Clinique de L'Union,58ac25,ffffff,3
line:140,network:1,44,Empalot / Université Paul Sabatier,0098d4,ffffff,3
line:97,network:1,45,Jeanne d'Arc / Pelletier Purpan,58ac25,ffffff,3
line:20,network:1,46,Basso Cambo / Pelletier Purpan,dc006b,ffffff,3
line:22,network:1,48,Basso Cambo / Tournefeuille Lycée,007c52,ffffff,3
line:23,network:1,49,Basso Cambo / Portet Gare SNCF,004687,ffffff,3
line:24,network:1,50,Basso Cambo / Portet H. Boucher,a0670f,ffffff,3
line:25,network:1,51,Balma - Gramont / La Terrasse,e46809,ffffff,3
line:104,network:1,53,Basso Cambo / Tibaous,0098d4,ffffff,3
line:27,network:1,54,Empalot / Gleyze-Vieille,e46809,ffffff,3
line:28,network:1,55,Colomiers Gare SNCF / Plaisance Ousseau,db001b,ffffff,3
line:29,network:1,56,Université Paul Sabatier / Auzeville Eglise,58ac25,ffffff,3
line:31,network:1,58,"Basso Cambo / Seysses Gay, Seysses Maison d'Arrêt ou Muret Lycée",58ac25,ffffff,3
line:32,network:1,59,La Vache / Saint-Jory Collège,3f2682,ffffff,3
line:33,network:1,60,Trois Cocus / Saint-Alban Centre Commercial,3f2682,ffffff,3
line:94,network:1,63,Tournefeuille Lycée / Compans-Caffarelli,e675a7,ffffff,3
line:38,network:1,66,Pelletier Purpan / Grand Rond,007c52,ffffff,3
line:39,network:1,67,Arènes / Plaisance Monestié,e675a7,ffffff,3
line:40,network:1,68,Balma - Gramont / Castelmaurou Mairie,572f08,ffffff,3
line:41,network:1,69,La Vache / Bruguières Verger,bb9dc6,ffffff,3
line:42,network:1,70,Jeanne d'Arc / Aéroconstellation,e675a7,ffffff,3
line:43,network:1,71,Seilh Mairie / Aussonne Agassines,58ac25,ffffff,3
line:44,network:1,72,Balma - Gramont / Balma Lasbordes,004687,ffffff,3
line:45,network:1,73,Borderouge / Saint-Jean Lestang,db001b,ffffff,3
line:46,network:1,74,Andromède Lycée / Mondonville Moulis,3f2682,ffffff,3
line:47,network:1,75,Colomiers Gare SNCF / Mondonville Moulis,007c52,ffffff,3
line:48,network:1,76,Argoulets / Lapeyrouse,a0670f,ffffff,3
line:51,network:1,79,Ramonville / Labège Couder ou Saint-Orens Lycée,0098d4,ffffff,3
line:52,network:1,80,Rangueil / Belberaud La Balme,3f2682,ffffff,3
line:58,network:1,81,Université Paul Sabatier / Castanet-Tolosan,dc006b,ffffff,3
line:59,network:1,82,Université Paul Sabatier / Ramonville Port Sud,db001b,ffffff,3
line:60,network:1,83,Balma - Gramont / Saint-Orens Lycée,dc006b,ffffff,3
line:105,network:1,84,Balma - Gramont / Fonsegrives Collège,0098d4,ffffff,3
line:215,network:1,85,Basso Cambo / Portet Gare SNCF,e675a7,ffffff,3
line:109,network:1,87,Cité Scolaire Rive Gauche / Frouzins Complexe Sportif,004687,ffffff,3
line:182,network:1,101,Balma - Gramont / Mondouzil ZA Les Landes,bb9dc6,ffffff,3
line:183,network:1,102,Balma - Gramont / Drémil Stade,3f2682,ffffff,3
line:184,network:1,103,Balma - Gramont / Drémil Le Colombier,58ac25,ffffff,3
line:185,network:1,104,Balma Ribaute / Aigrefeuille Clos Marelle,e675a7,ffffff,3
line:194,network:1,107,Fonsegrives Entiore / Drémil Stade,a0670f,ffffff,3
line:70,network:1,109,Balma Ribaute / Castanet-Tolosan,58ac25,ffffff,3
line:82,network:1,110,Barrière de Paris / Ginestous Chênes,0098d4,ffffff,3
line:81,network:1,111,Ramonville / Ramonville,dc006b,ffffff,3
line:83,network:1,112,Ramonville / Montjoie,007c52,ffffff,3
line:100,network:1,113,Fenouillet Croix / Collège Pechbonnieu,e46809,ffffff,3
line:87,network:1,114,Borderouge / Quartier Virebent,58ac25,ffffff,3
line:89,network:1,115,Saint Agne - SNCF / Université Paul Sabatier,007c52,ffffff,3
line:102,network:1,116,Tournefeuille Lycée / Saint-Lys Rossignols,0098d4,ffffff,3
line:101,network:1,117,Basso Cambo / Muret Gare SNCF - Cimetière,0098d4,ffffff,3
line:197,network:1,121,Tournefeuille Les Chênes / La Salvetat Apouticayre,dc006b,ffffff,3
line:151,network:1,130,Andromède Lycée / Fenouillet Centre Commercial - Entrée Sud,a0670f,ffffff,3
line:207,network:1,131,Saint-Alban Salvador Allende / Bruguières Gutenberg,58ac25,ffffff,3
line:208,network:1,132,Sept Deniers - Salvador Dali / Pôle,007c52,ffffff,3
line:275,network:1,139,Roseraie / Amouroux,58ac25,ffffff,3
line:138,network:1,150,Colomiers Gare SNCF / Colomiers Gare SNCF,0098d4,ffffff,3
line:198,network:1,151,Colomiers Gare SNCF / Colomiers Gare SNCF,004687,ffffff,3
line:230,network:1,169,La Vache / Bruguières Mairie,db001b,ffffff,3
line:54,network:1,201,Malepère / Varennes En Clavié,e675a7,ffffff,3
line:55,network:1,202,Castanet-Tolosan / Montbrun-Lauragais Roumieu,58ac25,ffffff,3
line:56,network:1,204,Labège Innopole Gare SNCF / Ayguesvives Collège,db001b,ffffff,3
line:57,network:1,205,Castanet-Tolosan / Ayguesvives Collège,0098d4,ffffff,3
line:152,network:1,301,Muret Gare SNCF - Parvis / Muret Sans Souci,dc006b,ffffff,3
line:153,network:1,302,Muret Gare SNCF - Parvis / Muret Salle Horizon,e46809,ffffff,3
line:154,network:1,303,Muret Gare SNCF - Parvis / Muret Peyrusse,e675a7,ffffff,3
line:155,network:1,304,Muret Gare SNCF - Cimetière / Muret Guyenne,dc006b,ffffff,3
line:156,network:1,305,Muret Gare SNCF - Parvis / Muret Côte des Bènes,0098d4,ffffff,3
line:157,network:1,306,Muret Gare SNCF - Parvis / Muret C.A.M.,e675a7,ffffff,3
line:158,network:1,310,Muret Gare SNCF - Parvis / Muret Estantens Eglise,007c52,ffffff,3
line:159,network:1,311,Muret Gare SNCF - Parvis / Portet Gare SNCF (par Villate),58ac25,ffffff,3
line:160,network:1,312,Muret Gare SNCF - Cimetière/ Saint-Clar Mairie,3f2682,ffffff,3
line:161,network:1,313,Muret Gare SNCF - Cimetière / Le Fauga Cimetière,e675a7,ffffff,3
line:162,network:1,314,Muret Gare SNCF - Parvis / Eaunes ZAC du Mandarin,db001b,ffffff,3
line:163,network:1,315,Muret Gare SNCF - Cimetière / Fonsorbes Lycée,a0670f,ffffff,3
line:164,network:1,316,Muret Gare SNCF - Parvis / Portet Gare SNCF (par Labarthe),004687,ffffff,3
line:165,network:1,317,Muret Gare SNCF - Parvis / Portet Gare SNCF (par Saubens),e46809,ffffff,3
line:224,network:1,318,Muret Gare SNCF - Cimetière / Fonsorbes Lycée,007c52,ffffff,3
line:166,network:1,320,Portet Gare SNCF / Muret Sans Souci,0098d4,ffffff,3
line:217,network:1,321,Frouzins Tréville / Portet Gare SNCF,a0670f,ffffff,3
line:270,network:1,401,Colomiers Gare SNCF / Saint-Lys Boulodrome,58ac25,ffffff,3
line:271,network:1,402,Colomiers Gare SNCF / Léguevin Salle Polyvalente,dc006b,ffffff,3
line:272,network:1,403,Lévignac Ancienne Gare / Mérenvielle Gare,004687,ffffff,3
line:61,network:1,A,Basso Cambo / Balma - Gramont,db001b,ffffff,1
line:99,network:1,AERO,Navette Aéroport,e46809,ffffff,3
line:69,network:1,B,Borderouge / Ramonville,ffdd00,000000,1
line:108,network:1,CIMTR,Navette Cimetières,0098d4,ffffff,3
line:144,network:1,L1,Sept Deniers - Salvador Dali / Fonsegrives Entiore,ff671b,ffffff,3
line:145,network:1,L2,Arènes / Colomiers Lycée International,ff671b,ffffff,3
line:176,network:1,L3,Arènes / Plaisance Monestié,ff671b,ffffff,3
line:187,network:1,L4,Basso Cambo / Cours Dillon,ff671b,ffffff,3
line:193,network:1,L5,Empalot / Portet Gare SNCF,ff671b,ffffff,3
line:170,network:1,L6,Ramonville / Castanet-Tolosan,ff671b,ffffff,3
line:171,network:1,L7,Université Paul Sabatier / Saint-Orens Piscine,ff671b,ffffff,3
line:172,network:1,L8,Marengo - SNCF / Gonin,ff671b,ffffff,3
line:174,network:1,L9,L'Union Grande Halle / Saint-Orens Centre Commercial,ff671b,ffffff,3
line:209,network:1,L10,La Vache / Fenouillet Centre Commercial - Entrée Nord,ff671b,ffffff,3
line:216,network:1,L11,Basso Cambo / Frouzins Complexe Sportif,ff671b,ffffff,3
line:269,network:1,L12,Borderouge  / Rangueil,ff671b,ffffff,3
line:264,network:1,L14,Basso Cambo / Marengo - SNCF,ff671b,ffffff,3
line:274,network:1,NFEN,Fenouillet Centre Commercial - Entrée Nord / Tournelle,007c52,ffffff,3
line:68,network:1,T1,Palais de Justice / MEETT,004687,ffffff,0
line:204,network:1,TELEO,Université Paul Sabatier / Oncopole - Lise Enjalbert,dc006b,ffffff,6
line:107,network:1,VILLE,Navette Centre Ville,e675a7,ffffff,3
```

### 85. `data/real-smoke/raw/realtime/date=2026-09-23/1790204219-865715567f81/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 86. `data/real-smoke/raw/realtime/date=2026-09-23/1790204350-9631d56a7f41/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 87. `data/real-smoke/raw/static/20260923T225641454289Z/_SUCCESS`

**File size:** `4` bytes

```
ok
```

### 88. `data/real-smoke/silver/static/20260923T225641454289Z/manifest.json`

**File size:** `510` bytes

```json
{
  "run_id": "20260923T225641454289Z",
  "source_id": "tisseo",
  "source_url": "https://data.toulouse-metropole.fr/explore/dataset/tisseo-gtfs/files/fc1dda89077cf37e4f7521760e0ef4e9/download/",
  "source_sha256": "1ff762e320c9327cee9d9d986664a2cab46daaf68a42a295cc76eb2b2a4d0de6",
  "transformed_at": "2026-09-23T22:56:53.470074+00:00",
  "row_counts": {
    "routes": 124,
    "trips": 40427,
    "stops": 5721,
    "stop_times": 902869,
    "calendar": 0,
    "calendar_dates": 277050
  }
}
```

## Exclusion Summary

These omissions are intentional so the snapshot represents the logical software system
rather than generated data/dependencies/runtime noise.

- binary/bulk extension .parquet: **39**
- generated/vendor/cache/package-metadata directory: **12**
- generic JSON data/generated artifact: **9**
- non-text/binary content: **5**
- binary/bulk extension .duckdb: **3**
- binary/bulk extension .zip: **3**
- generated snapshot itself: **1**
- oversized file (1,981,752 bytes): **1**
- oversized file (5,568,400 bytes): **1**
- oversized file (61,497,235 bytes): **1**
- oversized generic text (510,238 bytes): **1**
- secret/private environment file: **1**

## Export Policy

Typical included material:

- application source code
- SQL/dbt models, macros, tests, schemas and configs
- Airflow/DAG orchestration
- tests and test-support code
- scripts and developer tooling
- Docker/Compose/deployment/CI configuration
- observability configuration
- `.env.example` / non-secret configuration templates
- architecture and engineering documentation

Typical excluded material:

- `.git`, virtual environments, `node_modules`, package metadata
- caches, coverage output, build artifacts and logs
- raw/bronze/silver/gold/serving/history datasets
- databases, CSV/Parquet, images, archives and binaries
- `.env`, credentials, private keys and obvious secret files
- generated manifests/evidence under bulk data directories
- placeholder `.gitkeep` files

## End of Project Snapshot
