import json
from pathlib import Path

import pandas as pd

from mobility_control_tower.metrics.gtfs_kpis import build_gold, compute_gold_tables, expand_service_dates
from mobility_control_tower.reporting.charts import CHART_FILES, generate_static_charts
from mobility_control_tower.reporting.demo_report import generate_demo_report, generate_static_mvp_report


def fake_silver_tables() -> dict[str, pd.DataFrame]:
    return {
        "routes": pd.DataFrame(
            [
                {"route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3"},
                {"route_id": "R2", "route_short_name": "B", "route_long_name": "Basso", "route_type": "1"},
            ]
        ),
        "trips": pd.DataFrame(
            [
                {"route_id": "R1", "service_id": "WK", "trip_id": "T1"},
                {"route_id": "R1", "service_id": "WK", "trip_id": "T2"},
                {"route_id": "R1", "service_id": "WK", "trip_id": "T4"},
                {"route_id": "R1", "service_id": "EXTRA", "trip_id": "T5"},
                {"route_id": "R2", "service_id": "SPECIAL", "trip_id": "T3"},
            ]
        ),
        "stop_times": pd.DataFrame(
            [
                {"trip_id": "T1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "S1", "stop_sequence": "1", "departure_time_seconds": "28800"},
                {"trip_id": "T1", "arrival_time": "08:10:00", "departure_time": "08:10:00", "stop_id": "S2", "stop_sequence": "2", "departure_time_seconds": "29400"},
                {"trip_id": "T2", "arrival_time": "24:10:00", "departure_time": "24:10:00", "stop_id": "S1", "stop_sequence": "1", "departure_time_seconds": "87000"},
                {"trip_id": "T2", "arrival_time": "24:20:00", "departure_time": "24:20:00", "stop_id": "S2", "stop_sequence": "2", "departure_time_seconds": "87600"},
                {"trip_id": "T4", "arrival_time": "08:30:00", "departure_time": "08:30:00", "stop_id": "S1", "stop_sequence": "1", "departure_time_seconds": "30600"},
                {"trip_id": "T4", "arrival_time": "08:40:00", "departure_time": "08:40:00", "stop_id": "S2", "stop_sequence": "2", "departure_time_seconds": "31200"},
                {"trip_id": "T5", "arrival_time": "08:45:00", "departure_time": "08:45:00", "stop_id": "S1", "stop_sequence": "1", "departure_time_seconds": "31500"},
                {"trip_id": "T5", "arrival_time": "08:55:00", "departure_time": "08:55:00", "stop_id": "S2", "stop_sequence": "2", "departure_time_seconds": "32100"},
                {"trip_id": "T3", "arrival_time": "25:30:00", "departure_time": "25:30:00", "stop_id": "S2", "stop_sequence": "1", "departure_time_seconds": "91800"},
                {"trip_id": "T3", "arrival_time": "25:40:00", "departure_time": "25:40:00", "stop_id": "S3", "stop_sequence": "2", "departure_time_seconds": "92400"},
            ]
        ),
        "stops": pd.DataFrame(
            [
                {"stop_id": "S1", "stop_name": "Capitole"},
                {"stop_id": "S2", "stop_name": "Matabiau"},
                {"stop_id": "S3", "stop_name": "Basso Cambo"},
            ]
        ),
        "calendar": pd.DataFrame(
            [
                {
                    "service_id": "WK",
                    "monday": "1",
                    "tuesday": "1",
                    "wednesday": "0",
                    "thursday": "0",
                    "friday": "0",
                    "saturday": "0",
                    "sunday": "0",
                    "start_date": "20260105",
                    "end_date": "20260106",
                }
            ]
        ),
        "calendar_dates": pd.DataFrame(
            [
                {"service_id": "WK", "date": "20260106", "exception_type": "2"},
                {"service_id": "WK", "date": "20260107", "exception_type": "1"},
                {"service_id": "EXTRA", "date": "20260105", "exception_type": "1"},
                {"service_id": "SPECIAL", "date": "20260108", "exception_type": "1"},
            ]
        ),
    }


def test_service_date_expansion_applies_regular_service_additions_and_removals() -> None:
    tables = fake_silver_tables()
    services = expand_service_dates(tables["calendar"], tables["calendar_dates"])

    assert set(map(tuple, services[["service_id", "service_date"]].to_records(index=False))) == {
        ("WK", "2026-01-05"),
        ("WK", "2026-01-07"),
        ("EXTRA", "2026-01-05"),
        ("SPECIAL", "2026-01-08"),
    }


def test_service_date_expansion_works_with_calendar_dates_only() -> None:
    services = expand_service_dates(
        None,
        pd.DataFrame([{"service_id": "EXTRA", "date": "20260109", "exception_type": "1"}]),
    )

    assert services.to_dict("records") == [{"service_id": "EXTRA", "service_date": "2026-01-09"}]


def test_gold_kpis_use_service_day_hours_and_correct_grains() -> None:
    outputs = compute_gold_tables(fake_silver_tables())
    route_daily = outputs["route_daily_trips"]
    hourly = outputs["route_hourly_departures"]
    stop_daily = outputs["stop_daily_departures"]
    network = outputs["network_daily_summary"]

    assert route_daily.to_dict("records") == [
        {"service_date": "2026-01-05", "route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3", "scheduled_trips_count": 4},
        {"service_date": "2026-01-07", "route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3", "scheduled_trips_count": 3},
        {"service_date": "2026-01-08", "route_id": "R2", "route_short_name": "B", "route_long_name": "Basso", "route_type": "1", "scheduled_trips_count": 1},
    ]
    assert set(hourly["departure_hour"]) == {8, 24, 25}
    assert hourly["scheduled_departures_count"].sum() == 8
    assert stop_daily["scheduled_departures_count"].sum() == 16
    assert network.to_dict("records") == [
        {"service_date": "2026-01-05", "active_routes_count": 1, "scheduled_trips_count": 4, "scheduled_stop_departures_count": 8, "active_stops_count": 2},
        {"service_date": "2026-01-07", "active_routes_count": 1, "scheduled_trips_count": 3, "scheduled_stop_departures_count": 6, "active_stops_count": 2},
        {"service_date": "2026-01-08", "active_routes_count": 1, "scheduled_trips_count": 1, "scheduled_stop_departures_count": 2, "active_stops_count": 2},
    ]


def test_richer_gold_kpis_period_headway_route_type_and_rankings() -> None:
    outputs = compute_gold_tables(fake_silver_tables())
    route_period = outputs["route_period_summary"]
    headway = outputs["route_hourly_headway"]
    route_type = outputs["route_type_daily_summary"]
    busiest_route = outputs["busiest_route_day"]
    busiest_stop = outputs["busiest_stop_day"]

    r1 = route_period.loc[route_period["route_id"] == "R1"].iloc[0]
    assert r1["active_service_days"] == 2
    assert r1["total_scheduled_trips"] == 7
    assert r1["average_trips_per_active_day"] == 3.5
    assert r1["max_daily_trips"] == 4

    r1_hour_8 = headway.query("service_date == '2026-01-05' and route_id == 'R1' and departure_hour == 8").iloc[0]
    assert r1_hour_8["scheduled_departures_count"] == 3
    assert r1_hour_8["planned_headway_minutes"] == 20.0

    assert set(route_type["route_type_label"]) == {"Bus", "Subway/Metro"}
    assert busiest_route.iloc[0]["rank"] == 1
    assert busiest_route.iloc[0]["scheduled_trips_count"] == 4
    assert busiest_stop.iloc[0]["rank"] == 1
    assert busiest_stop.iloc[0]["scheduled_departures_count"] == 4


def test_gold_builder_writes_outputs_manifest_and_demo_report(tmp_path: Path) -> None:
    silver_run = tmp_path / "silver" / "tisseo" / "run-1"
    silver_run.mkdir(parents=True)
    for name, frame in fake_silver_tables().items():
        frame.to_csv(silver_run / f"{name}.csv", index=False)

    gold_run = build_gold(silver_run, tmp_path / "gold")
    manifest = json.loads((gold_run / "gold_manifest.json").read_text(encoding="utf-8"))

    assert (gold_run / "route_daily_trips.csv").is_file()
    assert (gold_run / "route_hourly_departures.csv").is_file()
    assert (gold_run / "stop_daily_departures.csv").is_file()
    assert (gold_run / "network_daily_summary.csv").is_file()
    assert (gold_run / "route_period_summary.csv").is_file()
    assert (gold_run / "route_hourly_headway.csv").is_file()
    assert (gold_run / "route_type_daily_summary.csv").is_file()
    assert (gold_run / "busiest_route_day.csv").is_file()
    assert (gold_run / "busiest_stop_day.csv").is_file()
    assert manifest["tables_created"]["route_daily_trips"]["row_count"] == 3
    assert manifest["kpi_definitions"]["route_period_summary"]["static_planning_only"] is True
    assert "route_hourly_departures" in manifest["kpi_definitions"]

    reports_dir = tmp_path / "reports"
    quality_stub = {"overall_status": "PASS", "checks": [{"status": "PASS"}, {"status": "WARN"}, {"status": "FAIL"}]}
    reports_dir.mkdir()
    (reports_dir / "gtfs_quality_run-1.json").write_text(json.dumps(quality_stub), encoding="utf-8")
    figures_dir = generate_static_charts(gold_run, reports_dir)
    report_path = generate_demo_report(gold_run, reports_dir)
    evidence_path = generate_static_mvp_report(gold_run, reports_dir)
    report = report_path.read_text(encoding="utf-8")
    evidence = evidence_path.read_text(encoding="utf-8")

    for filename in CHART_FILES:
        assert (figures_dir / filename).is_file()
    assert report_path.name == "mobility_demo_run-1.md"
    assert "# Mobility Control Tower" in report
    assert "static planning KPIs" in report
    assert "over the GTFS service period" in report
    assert "1 PASS, 1 WARN, 1 FAIL" in report
    assert evidence_path.name == "static_mvp_evidence_run-1.md"
    assert "Why this is Data Engineering" in evidence
