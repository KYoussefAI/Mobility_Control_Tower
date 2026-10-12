from __future__ import annotations

from pathlib import Path

import duckdb
from streamlit.testing.v1 import AppTest

from dashboard.app import REQUIRED_MARTS, missing_required_marts


def test_missing_required_marts_reports_partial_database(tmp_path) -> None:
    database = tmp_path / "partial.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("create table feed_freshness (snapshot_id varchar)")

    assert missing_required_marts(database) == sorted(REQUIRED_MARTS - {"feed_freshness"})


def test_missing_required_marts_accepts_complete_database(tmp_path) -> None:
    database = tmp_path / "complete.duckdb"
    with duckdb.connect(str(database)) as connection:
        for mart in REQUIRED_MARTS:
            connection.execute(f"create table {mart} (placeholder integer)")

    assert missing_required_marts(database) == []


def test_partial_database_shows_rebuild_message_instead_of_catalog_exception(tmp_path, monkeypatch) -> None:
    database = tmp_path / "partial.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("create table feed_freshness (snapshot_id varchar)")
    monkeypatch.setenv("MCT_DBT_DATABASE_PATH", str(database))

    app = AppTest.from_file(Path(__file__).parents[1] / "dashboard" / "app.py").run()

    assert not app.exception
    assert "partially built" in app.error[0].value
    assert "network_on_time_performance" in app.error[0].value
    assert "dbt-build" in app.error[0].value
