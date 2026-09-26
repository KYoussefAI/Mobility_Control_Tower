from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pytest

from scripts.create_ci_fixture import create_fixture

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_exactly_two_readable_airflow_dags() -> None:
    dag_files = sorted((PROJECT_ROOT / "airflow" / "dags").glob("*.py"))
    assert [path.name for path in dag_files] == ["realtime_pipeline.py", "static_gtfs_pipeline.py"]
    dag_ids: set[str] = set()
    for path in dag_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        dag_ids.update(
            node.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.keyword)
            and node.arg == "dag_id"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    assert dag_ids == {"realtime_pipeline", "static_gtfs_pipeline"}


def test_dashboard_module_imports_without_opening_a_database() -> None:
    path = PROJECT_ROOT / "dashboard" / "app.py"
    spec = importlib.util.spec_from_file_location("mct_dashboard", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DB_PATH.name == "mobility_control_tower.duckdb"


def test_ci_fixture_generation_is_repeatable(tmp_path: Path) -> None:
    root = tmp_path / "ci"
    first = create_fixture(root, allowed_parent=tmp_path)
    first_manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    first_files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

    second = create_fixture(root, allowed_parent=tmp_path)
    second_manifest = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    second_files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

    assert first == second
    assert first_manifest == second_manifest
    assert first_files == second_files


def test_ci_fixture_reset_rejects_its_allowed_parent(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be a child"):
        create_fixture(tmp_path, allowed_parent=tmp_path)
