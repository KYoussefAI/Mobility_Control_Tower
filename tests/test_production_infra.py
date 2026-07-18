from __future__ import annotations

from pathlib import Path

import yaml

from mobility_control_tower.core.exceptions import cli_failure_message, not_found
from mobility_control_tower.core.logging import LOG_FORMAT


def test_docker_and_compose_files_are_present_and_configured() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

    assert "FROM python:3.10-slim AS builder" in dockerfile
    assert "FROM python:3.10-slim AS runtime" in dockerfile
    assert "USER mct" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert set(compose["services"]) == {"api", "dashboard", "airflow-webserver", "airflow-scheduler", "airflow-init"}
    assert "mct-data" in compose["volumes"]
    assert "airflow-metadata" in compose["volumes"]


def test_env_example_documents_required_variables() -> None:
    text = Path(".env.example").read_text(encoding="utf-8")

    for name in ("GTFS_SOURCE", "API_PORT", "DASHBOARD_PORT", "AIRFLOW_PORT", "POLLING_INTERVAL", "DUCKDB_PATH", "HISTORY_PATH", "LOG_LEVEL"):
        assert name in text


def test_github_actions_and_precommit_are_configured() -> None:
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    quality = yaml.safe_load(Path(".github/workflows/quality.yml").read_text(encoding="utf-8"))
    precommit = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))

    assert "push" in ci[True]
    assert "pull_request" in ci[True]
    assert "docker build" in str(ci)
    assert "coverage html" in str(quality)
    hooks = str(precommit)
    for tool in ("ruff", "black", "isort", "mypy", "trailing-whitespace", "end-of-file-fixer", "check-yaml", "check-toml"):
        assert tool in hooks


def test_pyproject_quality_sections_exist() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")

    for section in ("[tool.black]", "[tool.isort]", "[tool.ruff]", "[tool.mypy]", "[tool.coverage.run]", "[tool.coverage.report]", "[tool.coverage.html]"):
        assert section in text


def test_architecture_diagrams_exist() -> None:
    expected = {
        "overall_architecture.md",
        "data_flow.md",
        "airflow_dag_overview.md",
        "medallion_architecture.md",
        "historical_realtime_flow.md",
        "api_architecture.md",
    }
    actual = {path.name for path in Path("docs/architecture").glob("*.md")}

    assert expected.issubset(actual)


def test_logging_and_exception_helpers() -> None:
    assert "%(asctime)s" in LOG_FORMAT
    assert "%(name)s" in LOG_FORMAT
    assert "%(levelname)s" in LOG_FORMAT
    assert cli_failure_message(ValueError("bad")) == "Error: bad"
    exc = not_found("missing")
    assert exc.status_code == 404
    assert exc.detail == "missing"

