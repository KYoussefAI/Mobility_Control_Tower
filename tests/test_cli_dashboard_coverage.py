from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pandas as pd

from mobility_control_tower import cli


def run_cli(monkeypatch, args: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["mobility-control-tower", *args])
    cli.main()


def test_cli_success_branches(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "run"
    path.mkdir()
    file_path = tmp_path / "report.md"
    file_path.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(cli, "load_source", lambda source, config: {"name": source})
    monkeypatch.setattr(cli, "download_and_preserve_gtfs", lambda *args: path)
    monkeypatch.setattr(cli, "profile_raw_run", lambda *args: (file_path, file_path))
    monkeypatch.setattr(cli, "build_bronze", lambda *args: path)
    monkeypatch.setattr(cli, "build_silver", lambda *args: path)
    monkeypatch.setattr(cli, "validate_silver_run", lambda *args: (file_path, file_path))
    monkeypatch.setattr(cli, "build_gold", lambda *args: path)
    monkeypatch.setattr(cli, "generate_demo_report", lambda *args: file_path)
    monkeypatch.setattr(cli, "generate_static_charts", lambda *args: path)
    monkeypatch.setattr(cli, "generate_static_mvp_report", lambda *args: file_path)
    monkeypatch.setattr(cli, "fetch_realtime_snapshot", lambda *args: path)
    monkeypatch.setattr(cli, "parse_realtime_snapshot", lambda *args: path)
    monkeypatch.setattr(cli, "generate_realtime_report", lambda *args: file_path)
    monkeypatch.setattr(cli, "check_realtime_compatibility", lambda *args: (file_path, file_path))
    monkeypatch.setattr(cli, "build_rt_gold", lambda *args: path)
    monkeypatch.setattr(cli, "generate_rt_charts", lambda *args: path)
    monkeypatch.setattr(cli, "generate_rt_snapshot_report", lambda *args: file_path)
    monkeypatch.setattr(cli, "run_historical_collection", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "build_historical_kpis", lambda *args: path)
    monkeypatch.setattr(cli, "run_dbt", lambda **kwargs: path)
    monkeypatch.setattr(cli, "test_dbt", lambda *args, **kwargs: file_path)
    monkeypatch.setattr(cli, "generate_dbt_docs", lambda *args, **kwargs: file_path)
    monkeypatch.setattr(cli, "run_quality_validation", lambda **kwargs: file_path)
    monkeypatch.setattr(cli, "run_ge_validation", lambda **kwargs: file_path)
    monkeypatch.setattr(cli, "run_benchmarks", lambda **kwargs: file_path)
    monkeypatch.setattr(cli, "build_serving_database", lambda *args, **kwargs: path)
    monkeypatch.setattr(cli, "query_serving_database", lambda *args, **kwargs: pd.DataFrame([{"x": 1}]))
    monkeypatch.setattr(cli, "generate_serving_report", lambda *args: file_path)
    monkeypatch.setattr(cli, "generate_api_report", lambda *args: file_path)
    monkeypatch.setattr(cli, "generate_final_report", lambda *args: file_path)

    commands = [
        ["ingest-gtfs", "--source", "tisseo", "--download"],
        ["profile-gtfs", "--raw-run", str(path)],
        ["build-bronze", "--raw-run", str(path)],
        ["build-silver", "--bronze-run", str(path)],
        ["validate-gtfs", "--silver-run", str(path)],
        ["build-gold", "--silver-run", str(path)],
        ["generate-demo-report", "--gold-run", str(path)],
        ["generate-static-charts", "--gold-run", str(path)],
        ["generate-static-mvp-report", "--gold-run", str(path)],
        ["fetch-gtfs-rt", "--source", "tisseo", "--feed-type", "trip_updates"],
        ["parse-gtfs-rt", "--raw-rt-run", str(path)],
        ["report-gtfs-rt", "--rt-run", str(path)],
        ["check-rt-compatibility", "--silver-run", str(path), "--rt-run", str(path)],
        ["build-rt-gold", "--silver-run", str(path), "--rt-run", str(path)],
        ["generate-rt-charts", "--rt-gold-run", str(path)],
        ["generate-rt-snapshot-report", "--rt-gold-run", str(path)],
        ["collect-gtfs-rt", "--source", "tisseo", "--feed-type", "trip_updates", "--max-polls", "1"],
        ["build-history-kpis", "--history-run", str(path)],
        ["run-dbt", "--silver-run", str(path)],
        ["test-dbt"],
        ["generate-dbt-docs"],
        ["run-quality-validation", "--suite", "silver", "--silver-run", str(path)],
        ["run-ge-validation", "--suite", "silver", "--silver-run", str(path)],
        ["run-benchmarks", "--silver-run", str(path)],
        ["build-serving-db", "--gold-run", str(path)],
        ["query-serving-db", "--db", str(file_path), "--query-name", "top-routes"],
        ["generate-serving-report", "--serving-run", str(path)],
        ["generate-api-report", "--db", str(file_path)],
        ["generate-final-report", "--serving-run", str(path)],
    ]
    for command in commands:
        run_cli(monkeypatch, command)


def test_cli_failure_path(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["mobility-control-tower", "build-gold", "--silver-run", "missing"])
    monkeypatch.setattr(cli, "build_gold", lambda *args: (_ for _ in ()).throw(ValueError("bad input")))
    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code == 1


class FakeSidebar:
    def __init__(self, page: str):
        self.page = page

    def text_input(self, *args, **kwargs):
        return "http://api"

    def markdown(self, *args, **kwargs):
        return None

    def radio(self, *args, **kwargs):
        return self.page


class FakeStreamlit(types.ModuleType):
    def __init__(self, page: str):
        super().__init__("streamlit")
        self.sidebar = FakeSidebar(page)

    def __getattr__(self, name):
        if name == "columns":
            return lambda count: [self for _ in range(count)]
        if name == "metric":
            return lambda *args, **kwargs: None
        return lambda *args, **kwargs: None


def dashboard_payload() -> dict:
    table = {"ok": True, "data": [{"service_date": "2026-01-01", "scheduled_trips_count": 1, "route_short_name": "A", "total_scheduled_trips": 1}], "count": 1}
    return {
        "health": {"ok": True, "status": "ok"},
        "network_overview": table,
        "top_routes": table,
        "route_types": table,
        "hourly_headway": table,
        "rt_feed_health": {"ok": True, "data": [{"freshness_status": "PASS"}], "count": 1},
        "rt_compatibility": {"ok": True, "data": [{"identifier_type": "route_id", "match_percentage": 100}], "count": 1},
        "rt_top_delayed_routes": {"ok": True, "data": [{"route_short_name": "A", "avg_delay_seconds": 1}], "count": 1},
        "history_summary": {"ok": True, "data": [{"collection_date": "2026-01-01", "updates_collected": 1}], "count": 1},
        "history_delay_trend": {"ok": True, "data": [{"collection_date": "2026-01-01", "collection_hour": "10", "average_delay_seconds": 1}], "count": 1},
        "history_feed_health": {"ok": True, "data": [{"collection_time": "t", "feed_age_seconds": 1}], "count": 1},
        "history_routes": {"ok": True, "data": [{"route_id": "R1", "average_delay_seconds": 1}], "count": 1},
        "history_stops": {"ok": True, "data": [{"stop_id": "S1", "average_delay_seconds": 1}], "count": 1},
        "quality_summary": {
            "ok": True,
            "data": [{"success_rate": 100, "expectations_failed": 0, "expectations_evaluated": 1, "failed_expectations": [], "freshness": {}}],
            "count": 1,
        },
    }


def test_dashboard_pages_execute(monkeypatch) -> None:
    for page in ("Operational MVP", "Historical Analytics", "Data Quality"):
        monkeypatch.setitem(sys.modules, "streamlit", FakeStreamlit(page))
        module = importlib.import_module("mobility_control_tower.dashboard.app")
        module = importlib.reload(module)
        monkeypatch.setattr(module, "fetch_dashboard_data", lambda api_url: dashboard_payload())
        module.main()
