from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.analytics_engineering import generate_dbt_docs, run_dbt, run_quality_validation
from mobility_control_tower.analytics_engineering import test_dbt as run_dbt_tests
from mobility_control_tower.api.app import create_app
from mobility_control_tower.api.routes import quality_summary
from mobility_control_tower.cli import build_parser
from mobility_control_tower.dashboard.api_client import ENDPOINTS
from mobility_control_tower.realtime.historical_storage import collect_gtfs_rt_snapshot


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def make_silver_run(tmp_path: Path) -> Path:
    silver = tmp_path / "silver" / "tisseo" / "static-1"
    write_csv(silver / "routes.csv", [{"route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3"}])
    write_csv(silver / "trips.csv", [{"route_id": "R1", "service_id": "WK", "trip_id": "T1"}])
    write_csv(
        silver / "stop_times.csv",
        [{"trip_id": "T1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "S1", "stop_sequence": "1", "departure_time_seconds": "28800"}],
    )
    write_csv(silver / "stops.csv", [{"stop_id": "S1", "stop_name": "Central", "stop_lat": "43.6", "stop_lon": "1.44"}])
    write_csv(
        silver / "calendar.csv",
        [
            {
                "service_id": "WK",
                "monday": "1",
                "tuesday": "1",
                "wednesday": "1",
                "thursday": "1",
                "friday": "1",
                "saturday": "0",
                "sunday": "0",
                "start_date": "20260101",
                "end_date": "20260102",
            }
        ],
    )
    write_csv(silver / "calendar_dates.csv", [{"service_id": "WK", "date": "20260103", "exception_type": "1"}])
    return silver


def trip_updates_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_700_000_000
    entity = feed.entity.add()
    entity.id = "tu-1"
    update = entity.trip_update
    update.trip.trip_id = "T1"
    update.trip.route_id = "R1"
    stop_update = update.stop_time_update.add()
    stop_update.stop_id = "S1"
    stop_update.arrival.delay = 60
    return feed.SerializeToString()


def make_history_run(tmp_path: Path) -> Path:
    collect_gtfs_rt_snapshot(
        "tisseo",
        {"name": "Tisseo"},
        "trip_updates",
        url="https://example.test/feed.pb",
        raw_history_root=tmp_path / "raw_history",
        parsed_history_root=tmp_path / "history",
        fetcher=lambda url, timeout_seconds: (trip_updates_feed(), 200, "application/x-protobuf"),
    )
    return tmp_path / "history" / "tisseo" / "trip_updates"


def test_dbt_project_has_required_structure_and_models() -> None:
    project = Path("dbt")
    config = yaml.safe_load((project / "dbt_project.yml").read_text(encoding="utf-8"))
    models = {path.stem for path in (project / "models").glob("**/*.sql")}

    assert config["profile"] == "mobility_control_tower"
    assert (project / "profiles.yml").is_file()
    assert {"route_daily_trips", "network_daily_summary", "route_delay_history", "daily_summary"}.issubset(models)
    assert (project / "models" / "marts" / "schema.yml").is_file()
    assert (project / "tests" / "assert_delay_reasonable.sql").is_file()


def test_run_dbt_requires_real_dbt_when_fallback_flag_is_used(tmp_path: Path) -> None:
    silver = make_silver_run(tmp_path)
    history = make_history_run(tmp_path)

    with pytest.raises(RuntimeError, match="real dbt executable"):
        run_dbt(silver_run=silver, history_run=history, output_root=tmp_path / "dbt_gold", use_installed=False)
    with pytest.raises(RuntimeError, match="real dbt executable"):
        run_dbt_tests(use_installed=False)
    with pytest.raises(RuntimeError, match="real dbt executable"):
        generate_dbt_docs(use_installed=False)


def test_real_dbt_build_exports_authoritative_gold_and_serving_matches(tmp_path: Path) -> None:
    from mobility_control_tower.serving.duckdb_loader import build_serving_database

    silver = make_silver_run(tmp_path)
    history = make_history_run(tmp_path)
    dbt_gold = run_dbt(silver_run=silver, history_run=history, output_root=tmp_path / "dbt_gold")
    manifest = json.loads((dbt_gold / "dbt_run_manifest.json").read_text(encoding="utf-8"))
    network = pd.read_csv(dbt_gold / "network_daily_summary.csv")
    route_delay = pd.read_parquet(dbt_gold / "route_delay_history.parquet")
    serving_run = build_serving_database(dbt_gold, serving_root=tmp_path / "serving", history_run=history, history_gold_run=dbt_gold)

    assert manifest["tool"] == "dbt Core"
    assert manifest["status"] == "success"
    assert Path(manifest["database_path"]).is_file()
    assert manifest["models_created"]["network_daily_summary"]["row_count"] == len(network)
    assert network["scheduled_trips_count"].sum() == 3
    assert route_delay.iloc[0]["updates_collected"] == 1
    with __import__("duckdb").connect(str(serving_run / "mobility_control_tower.duckdb"), read_only=True) as connection:
        served = connection.execute("select sum(scheduled_trips_count) from v_network_overview").fetchone()[0]
    assert served == network["scheduled_trips_count"].sum()


def test_failed_dbt_build_leaves_no_success_manifest(tmp_path: Path) -> None:
    silver = make_silver_run(tmp_path)
    (silver / "trips.csv").unlink()

    with pytest.raises(RuntimeError):
        run_dbt(silver_run=silver, output_root=tmp_path / "dbt_gold")

    manifests = list((tmp_path / "dbt_gold").glob("**/dbt_run_manifest.json"))
    assert manifests == []


def test_missing_dbt_binary_reports_actionable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mobility_control_tower import analytics_engineering

    silver = make_silver_run(tmp_path)
    monkeypatch.setattr(analytics_engineering, "_dbt_binary", lambda: None)

    with pytest.raises(FileNotFoundError, match="Install analytics dependencies"):
        run_dbt(silver_run=silver, output_root=tmp_path / "dbt_gold")


def test_ge_validation_suites_and_quality_summary(tmp_path: Path) -> None:
    silver = make_silver_run(tmp_path)
    history = make_history_run(tmp_path)
    dbt_gold = run_dbt(silver_run=silver, history_run=history, output_root=tmp_path / "dbt_gold")
    result = run_quality_validation(suite_name="all", silver_run=silver, gold_run=dbt_gold, history_run=history, quality_root=tmp_path / "quality")
    summary = json.loads((tmp_path / "quality" / "latest_validation_summary.json").read_text(encoding="utf-8"))

    assert result.is_file()
    assert summary["expectations_evaluated"] > 0
    assert summary["success_rate"] >= 80
    assert Path("quality_contracts/expectations/silver_suite.json").is_file()
    assert Path("quality_contracts/checkpoints/gold_checkpoint.yml").is_file()


def test_cli_parser_exposes_dbt_and_ge_commands() -> None:
    parser = build_parser()

    assert parser.parse_args(["test-dbt"]).command == "test-dbt"
    assert parser.parse_args(["generate-dbt-docs"]).command == "generate-dbt-docs"
    assert parser.parse_args(["run-quality-validation", "--suite", "silver"]).command == "run-quality-validation"
    assert parser.parse_args(["run-ge-validation", "--suite", "silver"]).command == "run-ge-validation"
    assert parser.parse_args(["run-dbt", "--silver-run", "data/silver/tisseo/run"]).command == "run-dbt"


def test_quality_endpoint_and_dashboard_client(tmp_path: Path, monkeypatch) -> None:
    quality_dir = tmp_path / "data" / "quality"
    quality_dir.mkdir(parents=True)
    (quality_dir / "latest_validation_summary.json").write_text(
        json.dumps({"success_rate": 100, "expectations_failed": 0, "expectations_evaluated": 1, "failed_expectations": []}),
        encoding="utf-8",
    )
    db = tmp_path / "api.duckdb"
    import duckdb

    with duckdb.connect(str(db)) as connection:
        connection.execute("CREATE TABLE t AS SELECT 1 AS x")
    app = create_app(db)

    class Request:
        def __init__(self, app):
            self.app = app

    monkeypatch.chdir(tmp_path)
    response = quality_summary()

    assert response["data"][0]["success_rate"] == 100
    assert ENDPOINTS["quality_summary"] == "/quality/summary"
    assert Request(app).app.state.db_path == db
