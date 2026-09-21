from pathlib import Path

import yaml


def test_local_container_stack_has_bounded_services_and_health_checks() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) == {
        "postgres",
        "incident-migrate",
        "airflow-init",
        "airflow-webserver",
        "airflow-scheduler",
        "api",
        "dashboard",
    }
    assert services["postgres"]["healthcheck"]
    assert services["api"]["healthcheck"]
    assert services["dashboard"]["healthcheck"]
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.10-slim AS builder" in dockerfile
    assert "USER mct" in dockerfile
