import json
from pathlib import Path

import pandas as pd

from mobility_control_tower.realtime.gtfs_rt_charts import RT_CHART_FILES, generate_rt_charts
from mobility_control_tower.realtime.gtfs_rt_kpis import (
    build_rt_gold,
    compatibility_status,
    compute_rt_gold_tables,
    freshness_status,
)
from mobility_control_tower.realtime.gtfs_rt_snapshot_report import generate_rt_snapshot_report


def static_tables() -> dict[str, pd.DataFrame]:
    return {
        "routes": pd.DataFrame(
            [
                {"route_id": "R1", "route_short_name": "A", "route_long_name": "Airport"},
                {"route_id": "R2", "route_short_name": "B", "route_long_name": "Basso"},
            ]
        ),
        "trips": pd.DataFrame([{"trip_id": "T1"}, {"trip_id": "T2"}]),
        "stops": pd.DataFrame([{"stop_id": "S1", "stop_name": "Capitole"}, {"stop_id": "S2", "stop_name": "Matabiau"}]),
    }


def rt_tables() -> dict[str, pd.DataFrame]:
    return {
        "rt_feed_summary": pd.DataFrame(
            [
                {
                    "feed_type": "trip_updates",
                    "fetched_at": "2026-01-01T00:01:00+00:00",
                    "header_timestamp": "1767225600",
                    "feed_age_seconds": "60",
                    "entity_count": "4",
                    "parsed_entity_count": "4",
                    "skipped_entity_count": "0",
                }
            ]
        ),
        "rt_trip_updates": pd.DataFrame(
            [
                {"entity_id": "E1", "trip_id": "T1", "route_id": "R1", "start_date": "20260101", "start_time": "08:00:00", "schedule_relationship": "SCHEDULED", "trip_update_timestamp": "1", "stop_time_update_count": "2"},
                {"entity_id": "E2", "trip_id": "T2", "route_id": "R2", "start_date": "20260101", "start_time": "09:00:00", "schedule_relationship": "SCHEDULED", "trip_update_timestamp": "1", "stop_time_update_count": "2"},
                {"entity_id": "E3", "trip_id": "T3", "route_id": "R3", "start_date": "20260101", "start_time": "10:00:00", "schedule_relationship": "SCHEDULED", "trip_update_timestamp": "1", "stop_time_update_count": "2"},
                {"entity_id": "E4", "trip_id": "", "route_id": "R1", "start_date": "20260101", "start_time": "11:00:00", "schedule_relationship": "SCHEDULED", "trip_update_timestamp": "1", "stop_time_update_count": "1"},
            ]
        ),
        "rt_stop_time_updates": pd.DataFrame(
            [
                {"entity_id": "E1", "trip_id": "T1", "route_id": "R1", "stop_id": "S1", "arrival_delay": "100", "departure_delay": "999"},
                {"entity_id": "E1", "trip_id": "T1", "route_id": "R1", "stop_id": "S2", "arrival_delay": "", "departure_delay": "400"},
                {"entity_id": "E2", "trip_id": "T2", "route_id": "R2", "stop_id": "S1", "arrival_delay": "-30", "departure_delay": ""},
                {"entity_id": "E2", "trip_id": "T2", "route_id": "R2", "stop_id": "S2", "arrival_delay": "", "departure_delay": ""},
                {"entity_id": "E3", "trip_id": "T3", "route_id": "R3", "stop_id": "S3", "arrival_delay": "600", "departure_delay": ""},
            ]
        ),
    }


def write_tables(root: Path, tables: dict[str, pd.DataFrame]) -> None:
    root.mkdir(parents=True)
    for name, frame in tables.items():
        frame.to_csv(root / f"{name}.csv", index=False)


def test_freshness_and_compatibility_status_thresholds() -> None:
    assert freshness_status("90") == "PASS"
    assert freshness_status("120") == "WARN"
    assert freshness_status("301") == "FAIL"
    assert freshness_status("") == "UNKNOWN"
    assert compatibility_status(95) == "PASS"
    assert compatibility_status(50) == "WARN"
    assert compatibility_status(49.9) == "FAIL"
    assert compatibility_status(None) == "NOT_APPLICABLE"


def test_rt_gold_delay_aggregation_compatibility_and_enrichment() -> None:
    outputs = compute_rt_gold_tables(static_tables(), rt_tables())
    health = outputs["rt_feed_health_snapshot"].iloc[0]
    enriched = outputs["rt_trip_update_enriched"]
    route_delay = outputs["rt_route_delay_snapshot"]
    stop_delay = outputs["rt_stop_delay_snapshot"]
    compatibility = outputs["rt_identifier_compatibility_snapshot"]

    assert health["freshness_status"] == "PASS"
    assert bool(health["has_delay_information"]) is True

    unmatched = enriched.loc[enriched["trip_id"] == "T3"].iloc[0]
    missing = enriched.loc[enriched["trip_id"] == ""].iloc[0]
    assert bool(unmatched["trip_id_static_match"]) is False
    assert "not found" in unmatched["compatibility_note"]
    assert "missing" in missing["compatibility_note"]

    r1 = route_delay.loc[route_delay["route_id"] == "R1"].iloc[0]
    assert r1["avg_delay_seconds"] == 250.0
    assert r1["delayed_updates_5min_count"] == 1
    assert r1["early_updates_count"] == 0

    r2 = route_delay.loc[route_delay["route_id"] == "R2"].iloc[0]
    assert r2["early_updates_count"] == 1
    assert r2["no_delay_info_count"] == 1

    s1 = stop_delay.loc[stop_delay["stop_id"] == "S1"].iloc[0]
    assert s1["avg_delay_seconds"] == 35.0
    assert bool(s1["stop_id_static_match"]) is True

    trip_compat = compatibility.loc[compatibility["identifier_type"] == "trip_id"].iloc[0]
    stop_compat = compatibility.loc[compatibility["identifier_type"] == "stop_id"].iloc[0]
    assert trip_compat["status"] == "WARN"
    assert stop_compat["status"] == "WARN"
    assert len(str(trip_compat["sample_unmatched_values"]).split("|")) <= 10


def test_identifier_compatibility_fail_and_not_applicable() -> None:
    outputs = compute_rt_gold_tables(
        {"routes": pd.DataFrame([{"route_id": "OTHER"}]), "trips": pd.DataFrame([{"trip_id": "OTHER"}]), "stops": pd.DataFrame([{"stop_id": "OTHER"}])},
        rt_tables(),
    )
    compatibility = outputs["rt_identifier_compatibility_snapshot"]
    assert set(compatibility["status"]) == {"FAIL"}

    empty_outputs = compute_rt_gold_tables(static_tables(), {"rt_feed_summary": rt_tables()["rt_feed_summary"], "rt_trip_updates": pd.DataFrame(), "rt_stop_time_updates": pd.DataFrame()})
    assert set(empty_outputs["rt_identifier_compatibility_snapshot"]["status"]) == {"NOT_APPLICABLE"}


def test_build_rt_gold_charts_and_report(tmp_path: Path) -> None:
    silver_run = tmp_path / "silver" / "tisseo" / "static-1"
    rt_run = tmp_path / "realtime" / "tisseo" / "trip_updates" / "rt-1"
    write_tables(silver_run, static_tables())
    write_tables(rt_run, rt_tables())
    (rt_run / "realtime_manifest.json").write_text(json.dumps({"feed_type": "trip_updates"}), encoding="utf-8")

    rt_gold_run = build_rt_gold(silver_run, rt_run, tmp_path / "realtime_gold")
    manifest = json.loads((rt_gold_run / "rt_gold_manifest.json").read_text(encoding="utf-8"))
    figures_dir = generate_rt_charts(rt_gold_run, tmp_path / "reports")
    report_path = generate_rt_snapshot_report(rt_gold_run, tmp_path / "reports")
    report = report_path.read_text(encoding="utf-8")

    assert (rt_gold_run / "rt_feed_health_snapshot.csv").is_file()
    assert (rt_gold_run / "rt_trip_update_enriched.csv").is_file()
    assert (rt_gold_run / "rt_route_delay_snapshot.csv").is_file()
    assert (rt_gold_run / "rt_stop_delay_snapshot.csv").is_file()
    assert (rt_gold_run / "rt_identifier_compatibility_snapshot.csv").is_file()
    assert manifest["compatibility_summary"]["trip_id"] == "WARN"
    for filename in RT_CHART_FILES:
        assert (figures_dir / filename).is_file()
    assert "GTFS-Realtime snapshot" in report
    assert "continuous real-time monitoring system" in report
    assert "streaming" in report
