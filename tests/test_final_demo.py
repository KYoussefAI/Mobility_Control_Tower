import json
from pathlib import Path

import duckdb
import pytest
import requests

from mobility_control_tower.cli import build_parser
from mobility_control_tower.dashboard.api_client import fetch_dashboard_data, get_json
from mobility_control_tower.reporting.final_report import generate_final_report


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def make_serving_run(tmp_path: Path) -> Path:
    serving = tmp_path / "serving" / "tisseo" / "run-1"
    serving.mkdir(parents=True)
    db = serving / "mobility_control_tower.duckdb"
    with duckdb.connect(str(db)) as connection:
        connection.execute(
            """
            CREATE TABLE route_period_summary AS
            SELECT 'A' AS route_short_name, 'Airport' AS route_long_name, 10 AS total_scheduled_trips
            """
        )
        connection.execute("CREATE VIEW v_top_routes_static AS SELECT * FROM route_period_summary")
        connection.execute(
            """
            CREATE TABLE rt_feed_health_snapshot AS
            SELECT 'trip_updates' AS feed_type, 6 AS feed_age_seconds, 'PASS' AS freshness_status, 10 AS entity_count
            """
        )
        connection.execute("CREATE VIEW v_rt_feed_health AS SELECT * FROM rt_feed_health_snapshot")
        connection.execute(
            """
            CREATE TABLE rt_identifier_compatibility_snapshot AS
            SELECT 'route_id' AS identifier_type, 100.0 AS match_percentage, 'PASS' AS status
            """
        )
        connection.execute("CREATE VIEW v_rt_identifier_compatibility AS SELECT * FROM rt_identifier_compatibility_snapshot")
    manifest = {
        "database_path": str(db),
        "tables_loaded": {"route_period_summary": {"row_count": 1}, "rt_feed_health_snapshot": {"row_count": 1}},
    }
    (serving / "serving_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return serving


def test_dashboard_api_client_success_and_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, params=None, timeout=5):
        return FakeResponse(200, {"data": [{"value": 1}], "count": 1, "source": "test", "notes": []})

    monkeypatch.setattr(requests, "get", fake_get)
    payload = get_json("http://api.test", "/health")
    assert payload["ok"] is True
    assert payload["count"] == 1

    def failing_get(url: str, params=None, timeout=5):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "get", failing_get)
    error = get_json("http://api.test", "/health")
    assert error["ok"] is False
    assert "API is not reachable" in error["error"]


def test_dashboard_fetches_expected_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get(url: str, params=None, timeout=5):
        calls.append(url)
        return FakeResponse(200, {"data": [], "count": 0, "source": url, "notes": []})

    monkeypatch.setattr(requests, "get", fake_get)
    result = fetch_dashboard_data("http://api.test")
    assert "health" in result
    assert "rt_top_delayed_routes" in result
    assert any("/static/top-routes" in call for call in calls)
    assert any("/realtime/feed-health" in call for call in calls)


def test_final_report_generation_and_cli_registration(tmp_path: Path) -> None:
    serving = make_serving_run(tmp_path)
    report = generate_final_report(serving, tmp_path / "reports")
    commands = build_parser()._subparsers._group_actions[0].choices

    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "Final academic MVP status" in text
    assert "Dashboard layer" in text
    assert "generate-final-report" in commands
    assert "serve-dashboard" in commands


def test_final_docs_readme_and_dashboard_are_presentation_ready() -> None:
    required_docs = [
        Path("docs/final_demo_guide.md"),
        Path("docs/teacher_presentation_notes.md"),
        Path("docs/project_summary.md"),
    ]
    for doc in required_docs:
        assert doc.is_file()

    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Architecture Overview" in readme
    assert "Dashboard Usage" in readme
    assert "Academic Positioning" in readme

    dashboard = Path("src/mobility_control_tower/dashboard/app.py").read_text(encoding="utf-8")
    forbidden_write_actions = ["st.file_uploader", "st.download_button", "requests.post", "requests.delete", "requests.put"]
    assert not any(action in dashboard for action in forbidden_write_actions)
