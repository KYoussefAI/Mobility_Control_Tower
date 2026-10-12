from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
from streamlit.testing.v1 import AppTest

from dashboard import app as dashboard_app
from dashboard.app import REQUIRED_MARTS, format_delay, format_service_date, missing_required_marts


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


def test_dashboard_formats_dates_and_signed_delays_for_people() -> None:
    assert format_service_date("2026-10-12") == "12 Oct 2026"
    assert format_delay(-45) == "45 sec early"
    assert format_delay(125) == "2 min 5 sec late"


def test_network_snapshot_aligns_every_query_to_selected_date(monkeypatch) -> None:
    selected = date(2026, 10, 12)
    calls: list[tuple[str, list[object] | None]] = []

    def fake_query(sql: str, parameters: list[object] | None = None) -> pd.DataFrame:
        calls.append((sql, parameters))
        return pd.DataFrame()

    monkeypatch.setattr(dashboard_app, "query", fake_query)
    dashboard_app.load_network_snapshot(selected)

    assert len(calls) == 3
    assert all(parameters == [selected] for _, parameters in calls)
