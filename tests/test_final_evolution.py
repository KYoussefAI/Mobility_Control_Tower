from __future__ import annotations

import json
from pathlib import Path

import duckdb
import yaml

from mobility_control_tower.api.app import create_app
from mobility_control_tower.benchmarking import run_benchmarks
from mobility_control_tower.config import load_source
from mobility_control_tower.observability import HISTORICAL_POLLS, metrics_response
from mobility_control_tower.settings import AppSettings
from mobility_control_tower.storage import LocalStorage, S3Storage, get_storage_backend


def make_db(path: Path) -> Path:
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE TABLE route_period_summary AS SELECT 'R1' AS route_id, 10 AS total_scheduled_trips")
        connection.execute("CREATE VIEW v_top_routes_static AS SELECT * FROM route_period_summary")
        connection.execute(
            "CREATE TABLE network_daily_summary AS SELECT '2026-01-01' AS service_date, 1 AS active_routes_count, 10 AS scheduled_trips_count, 20 AS scheduled_stop_departures_count, 2 AS active_stops_count"
        )
        connection.execute("CREATE VIEW v_network_overview AS SELECT * FROM network_daily_summary")
    return path


def test_local_storage_backend_roundtrip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    location = storage.write_bytes("city/feed.pb", b"abc")

    assert location.endswith("city/feed.pb")
    assert storage.exists("city/feed.pb")
    assert storage.read_bytes("city/feed.pb") == b"abc"
    assert storage.list_keys("city") == ["city/feed.pb"]


def test_s3_storage_uses_boto3_client(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class Body:
        def read(self):
            return b"payload"

    class Client:
        def put_object(self, **kwargs):
            calls.append(("put", kwargs))

        def get_object(self, **kwargs):
            calls.append(("get", kwargs))
            return {"Body": Body()}

        def head_object(self, **kwargs):
            calls.append(("head", kwargs))

        def list_objects_v2(self, **kwargs):
            calls.append(("list", kwargs))
            return {"Contents": [{"Key": "prefix/a.txt"}]}

    class Boto3:
        @staticmethod
        def client(service, region_name=None):
            calls.append(("client", {"service": service, "region_name": region_name}))
            return Client()

    monkeypatch.setitem(__import__("sys").modules, "boto3", Boto3)
    storage = S3Storage("bucket", "prefix", "eu-west-3")

    assert storage.write_bytes("a.txt", b"x") == "s3://bucket/prefix/a.txt"
    assert storage.read_bytes("a.txt") == b"payload"
    assert storage.exists("a.txt") is True
    assert storage.list_keys("") == ["prefix/a.txt"]
    assert ("put", {"Bucket": "bucket", "Key": "prefix/a.txt", "Body": b"x"}) in calls


def test_settings_and_storage_factory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCT_GTFS_SOURCE", "star_rennes")
    monkeypatch.setenv("MCT_STORAGE_BACKEND", "local")
    monkeypatch.setenv("MCT_STORAGE_ROOT", str(tmp_path))
    settings = AppSettings()
    storage = get_storage_backend(settings)

    assert settings.gtfs_source == "star_rennes"
    assert isinstance(storage, LocalStorage)


def test_second_transport_network_configured() -> None:
    source = load_source("star_rennes")

    assert "Rennes" in source["name"]
    assert source["output_filename"] == "STAR_Rennes_GTFS.zip"
    assert source["gtfs_realtime"]["trip_updates_url"]


def test_prometheus_metrics_export() -> None:
    HISTORICAL_POLLS.labels(source="unit", feed_type="trip_updates").inc()
    content, media_type = metrics_response()

    assert media_type.startswith("text/plain")
    assert b"mct_historical_polls_total" in content


def test_versioned_openapi_and_metrics_endpoint(tmp_path: Path) -> None:
    app = create_app(make_db(tmp_path / "api.duckdb"))
    openapi = app.openapi()
    from mobility_control_tower.api.routes import pipeline_metrics

    metrics = pipeline_metrics()

    assert "/v1/health" in openapi["paths"]
    assert "/health" in openapi["paths"]
    assert metrics.status_code == 200
    assert b"mct_api_requests_total" in metrics.body


def test_benchmark_report_generation(tmp_path: Path) -> None:
    silver = tmp_path / "silver"
    silver.mkdir()
    (silver / "routes.csv").write_text("route_id\nR1\n", encoding="utf-8")
    db = make_db(tmp_path / "serving.duckdb")
    report = run_benchmarks(silver_run=silver, db_path=db, output_dir=tmp_path / "benchmarks")

    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "silver_build_artifact_scan" in text
    assert "api_latency_openapi_generation" in text


def test_grafana_dashboard_and_portfolio_docs_exist() -> None:
    dashboard = json.loads(Path("grafana/mobility-control-tower-dashboard.json").read_text(encoding="utf-8"))
    sources = yaml.safe_load(Path("config/sources.yml").read_text(encoding="utf-8"))["sources"]

    assert dashboard["title"] == "Mobility Control Tower"
    assert "star_rennes" in sources
    assert Path("docs/portfolio_case_study.md").is_file()
    assert Path("docs/interview_questions.md").is_file()
    assert Path("docs/architecture/portfolio_architecture.md").is_file()
