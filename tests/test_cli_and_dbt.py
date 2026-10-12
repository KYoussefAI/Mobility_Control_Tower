from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import duckdb
import pytest
from google.transit import gtfs_realtime_pb2
from test_realtime_pipeline import trip_updates_payload

from mobility_control_tower import cli
from mobility_control_tower.config import db_path, latest_run, load_source
from mobility_control_tower.dbt import build_dbt
from mobility_control_tower.quality import require_pass
from mobility_control_tower.realtime_pipeline import preserve_realtime_bytes
from mobility_control_tower.static_pipeline import preserve_static_bytes, transform_static

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

    monkeypatch.setattr("mobility_control_tower.dbt.shutil.which", lambda _: "dbt")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs["env"]))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("mobility_control_tower.dbt.subprocess.run", fake_run)
    database = build_dbt(static_run, tmp_path)

    command, environment = calls[0]
    variables = json.loads(command[command.index("--vars") + 1])
    assert command[:2] == ["dbt", "build"]
    assert command[2:4] == ["--threads", "1"]
    assert variables["static_path"] == static_run.resolve().as_posix()
    assert variables["on_time_late_seconds"] == 300
    assert variables["max_abs_delay_seconds"] == 7200
    assert variables["min_reliable_sample_size"] == 5
    assert variables["fresh_realtime_seconds"] == 90
    assert environment["MCT_DBT_DATABASE_PATH"] == str(database)
    assert environment["MCT_DBT_TEMP_DIRECTORY"] == (tmp_path / "duckdb_tmp").resolve().as_posix()


def test_cli_dbt_build_uses_paris_date_when_start_date_is_missing(tmp_path, monkeypatch, gtfs_zip_bytes: bytes) -> None:
    source = load_source()
    raw = preserve_static_bytes(
        gtfs_zip_bytes,
        source,
        tmp_path,
        ingested_at=datetime(2026, 1, 1, 12, tzinfo=UTC),
    )
    static_run = transform_static(raw, tmp_path)

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(trip_updates_payload())
    feed.entity[0].trip_update.trip.ClearField("start_date")
    preserve_realtime_bytes(
        feed.SerializeToString(),
        source,
        tmp_path,
        collected_at=datetime(2026, 1, 1, 23, 30, tzinfo=UTC),
    )

    monkeypatch.delenv("MCT_DBT_DATABASE_PATH", raising=False)
    cli.main(["--data-root", str(tmp_path), "dbt-build", "--static-run", str(static_run)])

    with duckdb.connect(str(db_path(tmp_path)), read_only=True) as connection:
        service_date = connection.execute("select distinct service_date from int_delay_observations").fetchone()[0]
    assert service_date.isoformat() == "2026-01-02"


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
