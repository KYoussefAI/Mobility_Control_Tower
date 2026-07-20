import json
from pathlib import Path

import pandas as pd
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.realtime.gtfs_rt_compatibility import check_realtime_compatibility
from mobility_control_tower.realtime.gtfs_rt_parser import parse_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_raw import preserve_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_report import generate_realtime_report

SOURCE = {"name": "Tisseo", "source_page_url": "https://example.test"}


def trip_updates_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_700_000_000
    entity = feed.entity.add()
    entity.id = "tu-1"
    update = entity.trip_update
    update.trip.trip_id = "T1"
    update.trip.route_id = "R1"
    update.trip.start_date = "20260105"
    update.trip.start_time = "08:00:00"
    update.timestamp = 1_700_000_010
    stop_update = update.stop_time_update.add()
    stop_update.stop_sequence = 1
    stop_update.stop_id = "S1"
    stop_update.arrival.time = 1_700_000_100
    stop_update.arrival.delay = 60
    stop_update.departure.time = 1_700_000_120
    stop_update.departure.delay = 30
    return feed.SerializeToString()


def vehicle_positions_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_700_000_000
    entity = feed.entity.add()
    entity.id = "veh-1"
    vehicle = entity.vehicle
    vehicle.trip.trip_id = "T1"
    vehicle.trip.route_id = "R1"
    vehicle.vehicle.id = "V1"
    vehicle.vehicle.label = "Bus 1"
    vehicle.position.latitude = 43.6
    vehicle.position.longitude = 1.44
    vehicle.position.bearing = 90
    vehicle.position.speed = 12.5
    vehicle.current_stop_sequence = 1
    vehicle.stop_id = "S1"
    vehicle.current_status = gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO
    vehicle.timestamp = 1_700_000_030
    return feed.SerializeToString()


def service_alerts_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_700_000_000
    entity = feed.entity.add()
    entity.id = "alert-1"
    alert = entity.alert
    alert.cause = gtfs_realtime_pb2.Alert.CONSTRUCTION
    alert.effect = gtfs_realtime_pb2.Alert.DETOUR
    period = alert.active_period.add()
    period.start = 1_700_000_000
    period.end = 1_700_003_600
    alert.header_text.translation.add(text="Works")
    alert.description_text.translation.add(text="Temporary detour")
    informed = alert.informed_entity.add()
    informed.route_id = "R1"
    informed.route_type = 3
    informed.stop_id = "S1"
    return feed.SerializeToString()


def read_csv(path: Path) -> list[dict[str, str]]:
    return pd.read_csv(path, dtype=str, keep_default_na=False).to_dict("records")


def make_raw_run(tmp_path: Path, feed_type: str, content: bytes) -> Path:
    return preserve_realtime_snapshot(
        content,
        "tisseo",
        SOURCE,
        feed_type,
        "https://example.test/feed.pb",
        tmp_path / "raw_realtime",
        http_status=200,
        content_type="application/x-protobuf",
    )


def test_raw_realtime_metadata_is_created(tmp_path: Path) -> None:
    raw_run = make_raw_run(tmp_path, "trip_updates", trip_updates_feed())
    metadata = json.loads((raw_run / "metadata.json").read_text(encoding="utf-8"))

    assert (raw_run / "feed.pb").is_file()
    assert metadata["feed_type"] == "trip_updates"
    assert metadata["sha256"]
    assert metadata["file_size_bytes"] > 0
    assert metadata["http_status"] == 200


def test_parse_trip_updates_and_stop_time_updates(tmp_path: Path) -> None:
    raw_run = make_raw_run(tmp_path, "trip_updates", trip_updates_feed())
    rt_run = parse_realtime_snapshot(raw_run, tmp_path / "realtime")

    summary = read_csv(rt_run / "rt_feed_summary.csv")[0]
    trips = read_csv(rt_run / "rt_trip_updates.csv")
    stops = read_csv(rt_run / "rt_stop_time_updates.csv")

    assert summary["feed_type"] == "trip_updates"
    assert summary["entity_count"] == "1"
    assert trips[0]["trip_id"] == "T1"
    assert trips[0]["route_id"] == "R1"
    assert stops[0]["stop_id"] == "S1"
    assert stops[0]["arrival_delay"] == "60"


def test_parse_vehicle_positions(tmp_path: Path) -> None:
    raw_run = make_raw_run(tmp_path, "vehicle_positions", vehicle_positions_feed())
    rt_run = parse_realtime_snapshot(raw_run, tmp_path / "realtime")
    vehicles = read_csv(rt_run / "rt_vehicle_positions.csv")

    assert vehicles[0]["vehicle_id"] == "V1"
    assert vehicles[0]["trip_id"] == "T1"
    assert vehicles[0]["stop_id"] == "S1"
    assert vehicles[0]["current_status"] == "IN_TRANSIT_TO"


def test_parse_service_alerts(tmp_path: Path) -> None:
    raw_run = make_raw_run(tmp_path, "service_alerts", service_alerts_feed())
    rt_run = parse_realtime_snapshot(raw_run, tmp_path / "realtime")
    alerts = read_csv(rt_run / "rt_alerts.csv")
    entities = read_csv(rt_run / "rt_alert_informed_entities.csv")

    assert alerts[0]["cause"] == "CONSTRUCTION"
    assert alerts[0]["effect"] == "DETOUR"
    assert alerts[0]["header_text"] == "Works"
    assert entities[0]["route_id"] == "R1"
    assert entities[0]["stop_id"] == "S1"


def test_realtime_report_and_static_compatibility(tmp_path: Path) -> None:
    raw_run = make_raw_run(tmp_path, "trip_updates", trip_updates_feed())
    rt_run = parse_realtime_snapshot(raw_run, tmp_path / "realtime")
    report_path = generate_realtime_report(rt_run, tmp_path / "reports")

    silver_run = tmp_path / "silver" / "tisseo" / "static-1"
    silver_run.mkdir(parents=True)
    (silver_run / "routes.csv").write_text("route_id\nR1\n", encoding="utf-8")
    (silver_run / "trips.csv").write_text("trip_id\nT1\n", encoding="utf-8")
    (silver_run / "stops.csv").write_text("stop_id\nS1\n", encoding="utf-8")
    json_path, markdown_path = check_realtime_compatibility(silver_run, rt_run, tmp_path / "reports")
    compatibility = json.loads(json_path.read_text(encoding="utf-8"))

    assert report_path.is_file()
    assert "snapshot" in report_path.read_text(encoding="utf-8")
    assert compatibility["overall_status"] == "PASS"
    assert markdown_path.is_file()


def test_compatibility_reports_unmatched_ids(tmp_path: Path) -> None:
    raw_run = make_raw_run(tmp_path, "trip_updates", trip_updates_feed())
    rt_run = parse_realtime_snapshot(raw_run, tmp_path / "realtime")
    silver_run = tmp_path / "silver" / "tisseo" / "static-1"
    silver_run.mkdir(parents=True)
    (silver_run / "routes.csv").write_text("route_id\nOTHER\n", encoding="utf-8")
    (silver_run / "trips.csv").write_text("trip_id\nOTHER\n", encoding="utf-8")
    (silver_run / "stops.csv").write_text("stop_id\nOTHER\n", encoding="utf-8")
    json_path, _ = check_realtime_compatibility(silver_run, rt_run, tmp_path / "reports")
    compatibility = json.loads(json_path.read_text(encoding="utf-8"))

    assert compatibility["overall_status"] == "WARN"
    route_check = next(check for check in compatibility["checks"] if check["check_name"] == "route_id_matches_static_routes")
    assert route_check["unmatched_count"] == 1
    assert route_check["status"] == "WARN"
