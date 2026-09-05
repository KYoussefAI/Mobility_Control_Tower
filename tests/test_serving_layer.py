from pathlib import Path

import duckdb

from mobility_control_tower.serving.duckdb_loader import build_serving_database


def test_build_serving_database_publishes_static_gold(tmp_path: Path) -> None:
    gold_run = tmp_path / "gold" / "tisseo" / "run-001"
    gold_run.mkdir(parents=True)
    (gold_run / "network_daily_summary.csv").write_text(
        "service_date,total_trips\n2025-01-01,12\n", encoding="utf-8"
    )
    (gold_run / "route_daily_trips.csv").write_text(
        "service_date,route_id,trip_count\n2025-01-01,A,12\n", encoding="utf-8"
    )
    (gold_run / "route_period_summary.csv").write_text(
        "route_id,total_scheduled_trips\nA,12\n", encoding="utf-8"
    )

    serving_run = build_serving_database(gold_run, tmp_path / "serving")
    database = serving_run / "mobility_control_tower.duckdb"

    assert database.is_file()
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            "select total_trips from network_daily_summary"
        ).fetchone() == (12,)
