import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2

from mobility_control_tower.api.app import create_app
from mobility_control_tower.config import load_sources
from mobility_control_tower.incidents import IncidentStore
from mobility_control_tower.realtime import historical_storage
from mobility_control_tower.realtime.historical_storage import collect_gtfs_rt_snapshot, discover_committed_snapshots
from mobility_control_tower.reliability import explicit_cancellations, headway_reliability, on_time_performance, realtime_coverage
from mobility_control_tower.security import AuthenticationError, create_access_token, verify_access_token
from mobility_control_tower.serving.duckdb_loader import build_serving_database

SOURCE = {"name": "Tisseo", "realtime": {}}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def make_gold_run(tmp_path: Path) -> Path:
    gold = tmp_path / "gold" / "tisseo" / "static-1"
    gold.mkdir(parents=True, exist_ok=True)
    (gold / "dbt_run_manifest.json").write_text(json.dumps({"status": "success", "tool": "dbt Core"}), encoding="utf-8")
    write_csv(
        gold / "route_daily_trips.csv",
        [
            {
                "service_date": "2026-01-01",
                "route_id": "R1",
                "route_short_name": "A",
                "route_long_name": "Airport",
                "route_type": "3",
                "scheduled_trips_count": 2,
            }
        ],
    )
    write_csv(
        gold / "network_daily_summary.csv",
        [{"service_date": "2026-01-01", "active_routes_count": 1, "scheduled_trips_count": 2, "scheduled_stop_departures_count": 4, "active_stops_count": 2}],
    )
    write_csv(
        gold / "route_period_summary.csv",
        [
            {
                "route_id": "R1",
                "route_short_name": "A",
                "route_long_name": "Airport",
                "route_type": "3",
                "active_service_days": 1,
                "total_scheduled_trips": 2,
                "average_trips_per_active_day": 2,
                "max_daily_trips": 2,
            }
        ],
    )
    return gold


def vehicle_positions_feed(*, stale: bool = False, invalid_coordinate: bool = False) -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_800_000_000 if stale else 1_900_000_000
    entity = feed.entity.add()
    entity.id = "veh-1"
    vehicle = entity.vehicle
    vehicle.trip.trip_id = "T1"
    vehicle.trip.route_id = "R1"
    vehicle.vehicle.id = "V1"
    vehicle.vehicle.label = "Bus 1"
    vehicle.position.latitude = 143.6 if invalid_coordinate else 43.6
    vehicle.position.longitude = 1.44
    vehicle.position.bearing = 90
    vehicle.position.speed = 12.5
    vehicle.current_stop_sequence = 1
    vehicle.stop_id = "S1"
    vehicle.current_status = gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO
    vehicle.timestamp = feed.header.timestamp
    return feed.SerializeToString()


def service_alerts_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1_900_000_000
    entity = feed.entity.add()
    entity.id = "alert-1"
    alert = entity.alert
    alert.cause = gtfs_realtime_pb2.Alert.CONSTRUCTION
    alert.effect = gtfs_realtime_pb2.Alert.DETOUR
    period = alert.active_period.add()
    period.start = 1_800_000_000
    period.end = 1_950_000_000
    alert.header_text.translation.add(text="Travaux", language="fr")
    alert.description_text.translation.add(text="Deviation temporaire", language="fr")
    informed_route = alert.informed_entity.add()
    informed_route.route_id = "R1"
    informed_route.route_type = 3
    informed_stop = alert.informed_entity.add()
    informed_stop.stop_id = "S1"
    return feed.SerializeToString()


def canceled_trip_updates() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source": "tisseo", "trip_id": "T1", "route_id": "R1", "schedule_relationship": "SCHEDULED"},
            {"source": "tisseo", "trip_id": "T2", "route_id": "R1", "schedule_relationship": "CANCELED"},
        ]
    )


def test_source_capability_registry_normalizes_feed_availability() -> None:
    sources = load_sources(Path("config/sources.yml"))

    assert sources["tisseo"]["timezone"] == "Europe/Paris"
    assert sources["tisseo"]["realtime"]["trip_updates"]["enabled"] is True
    assert sources["tisseo"]["realtime"]["vehicle_positions"]["enabled"] is False
    assert sources["star_rennes"]["realtime"]["vehicle_positions"]["enabled"] is True
    assert sources["star_rennes"]["expected_freshness"]["service_alerts_seconds"] == 600


def test_missing_trip_update_is_unknown_not_on_time_or_canceled() -> None:
    eligible = pd.DataFrame([{"trip_id": "T1"}, {"trip_id": "T2"}, {"trip_id": "T3"}])
    observed = pd.DataFrame([{"source": "tisseo", "trip_id": "T1"}, {"source": "tisseo", "trip_id": "UNMATCHED"}])

    coverage = realtime_coverage(eligible, observed, source="tisseo", service_date="2026-01-01", route_id="R1")
    otp = on_time_performance(pd.DataFrame([{"delay_seconds": -30}, {"delay_seconds": 120}, {"delay_seconds": 420}, {"delay_seconds": None}]), source="tisseo")
    cancellations = explicit_cancellations(canceled_trip_updates(), source="tisseo")

    assert coverage["observed_trip_count"] == 1
    assert coverage["unobserved_scheduled_trip_count"] == 2
    assert coverage["coverage_percentage"] == 33.33
    assert otp["eligible_observations"] == 3
    assert otp["on_time_observations"] == 2
    assert cancellations.iloc[0]["trip_id"] == "T2"
    assert cancellations.iloc[0]["evidence_type"] == "GTFS_RT_TRIP_SCHEDULE_RELATIONSHIP_CANCELED"
    assert cancellations.iloc[0]["evidence_category"] == "GTFS_RT_EXPLICIT_SCHEDULE_RELATIONSHIP"


def test_headway_reliability_detects_gap_bunching_and_excess_wait() -> None:
    result = headway_reliability(
        observed_times_seconds=[8 * 3600, 8 * 3600 + 120, 8 * 3600 + 1320],
        scheduled_headways_seconds=[600, 600],
        source="tisseo",
        route_id="R1",
    )

    assert result["observed_headway_count"] == 2
    assert result["bunching_event_count"] == 1
    assert result["service_gap_event_count"] == 1
    assert result["excess_waiting_time_seconds"] > 0
    assert result["confidence_status"] == "LOW_SAMPLE"


def test_vehicle_and_alert_snapshots_are_committed_and_served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    moments = iter(
        [
            datetime(2030, 3, 17, 8, 0, tzinfo=timezone.utc),
            datetime(2030, 3, 17, 8, 5, tzinfo=timezone.utc),
            datetime(2030, 3, 17, 8, 10, tzinfo=timezone.utc),
        ]
    )
    monkeypatch.setattr(historical_storage, "_utc_now", lambda: next(moments))
    raw_root = tmp_path / "raw"
    history_root = tmp_path / "history"

    vehicle_meta = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "vehicle_positions",
        url="https://example.test/vehicles.pb",
        raw_history_root=raw_root,
        parsed_history_root=history_root,
        fetcher=lambda url, timeout_seconds: (vehicle_positions_feed(invalid_coordinate=True), 200, "application/x-protobuf"),
    )
    duplicate = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "vehicle_positions",
        url="https://example.test/vehicles.pb",
        raw_history_root=raw_root,
        parsed_history_root=history_root,
        fetcher=lambda url, timeout_seconds: (vehicle_positions_feed(invalid_coordinate=True), 200, "application/x-protobuf"),
    )
    alert_meta = collect_gtfs_rt_snapshot(
        "tisseo",
        SOURCE,
        "service_alerts",
        url="https://example.test/alerts.pb",
        raw_history_root=raw_root,
        parsed_history_root=history_root,
        fetcher=lambda url, timeout_seconds: (service_alerts_feed(), 200, "application/x-protobuf"),
    )

    vehicle_run = Path(vehicle_meta["parsed_path"]).parents[2]
    alert_run = Path(alert_meta["parsed_path"]).parents[2]
    assert duplicate["duplicate"] is True
    assert len(discover_committed_snapshots(vehicle_run)) == 1
    assert len(discover_committed_snapshots(alert_run)) == 1

    vehicle_serving = build_serving_database(make_gold_run(tmp_path), serving_root=tmp_path / "serving", history_run=vehicle_run, serving_run_id="vehicles")
    alert_serving = build_serving_database(make_gold_run(tmp_path), serving_root=tmp_path / "serving_alerts", history_run=alert_run, serving_run_id="alerts")

    vehicle_client = TestClient(create_app(vehicle_serving / "mobility_control_tower.duckdb"))
    alert_client = TestClient(create_app(alert_serving / "mobility_control_tower.duckdb"))
    vehicles = vehicle_client.get("/vehicles").json()["data"]
    alerts = alert_client.get("/alerts/active").json()["data"]

    assert vehicles[0]["vehicle_id"] == "V1"
    assert vehicles[0]["invalid_coordinate_flag"] is True
    assert alerts[0]["alert_id"] == "alert-1"
    assert {row["route_id"] for row in alerts} == {"R1", None}


def test_incomplete_snapshot_is_invisible_to_discovery(tmp_path: Path) -> None:
    snapshot_dir = tmp_path / "history" / "tisseo" / "trip_updates" / "date=2026-01-01" / "hour=08" / "snapshot_timestamp=s1"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "metadata.json").write_text(
        json.dumps({"feed_type": "trip_updates", "snapshot_id": "s1", "collection_time": "2026-01-01T08:00:00+00:00"}), encoding="utf-8"
    )

    assert discover_committed_snapshots(tmp_path / "history" / "tisseo" / "trip_updates") == []


def test_incident_lifecycle_is_deduplicated_audited_and_authorized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "phase3-test-secret")
    store = IncidentStore(tmp_path / "incidents")
    incident = store.open_or_update(
        incident_type="SERVICE_GAP",
        source="tisseo",
        entity_type="route",
        entity_id="R1",
        severity="WARNING",
        title="Service gap on route R1",
        summary="Observed headway exceeded configured threshold.",
        evidence={"observed_headway_seconds": 1200, "threshold_seconds": 900},
        rule_id="service_gap",
        rule_version="1",
        deduplication_key="service_gap:tisseo:R1:2026-01-01T08",
    )
    repeated = store.open_or_update(
        incident_type="SERVICE_GAP",
        source="tisseo",
        entity_type="route",
        entity_id="R1",
        severity="WARNING",
        title="Service gap on route R1",
        summary="Still observed.",
        evidence={"observed_headway_seconds": 1260, "threshold_seconds": 900},
        rule_id="service_gap",
        rule_version="1",
        deduplication_key="service_gap:tisseo:R1:2026-01-01T08",
    )
    token = create_access_token("operator@example.test", {"incidents:write"}, expires_in_seconds=60)
    readonly = create_access_token("viewer@example.test", {"public:read"}, expires_in_seconds=60)

    assert repeated["incident_id"] == incident["incident_id"]
    assert repeated["observation_count"] == 2
    assert verify_access_token(token, {"incidents:write"}).subject == "operator@example.test"
    with pytest.raises(AuthenticationError):
        verify_access_token(readonly, {"incidents:write"})

    acknowledged = store.transition(incident["incident_id"], status="ACKNOWLEDGED", operator="operator@example.test", note="Monitoring")
    resolved = store.transition(incident["incident_id"], status="RESOLVED", operator="operator@example.test", note="Recovered")
    events = (tmp_path / "incidents" / "incident_events.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert acknowledged["status"] == "ACKNOWLEDGED"
    assert resolved["status"] == "RESOLVED"
    assert len(events) == 4


def test_incident_api_requires_bearer_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "phase3-test-secret")
    store = IncidentStore(tmp_path / "incidents")
    incident = store.open_or_update(
        incident_type="LOW_COVERAGE",
        source="tisseo",
        entity_type="network",
        entity_id="network",
        severity="CRITICAL",
        title="Low coverage",
        summary="Coverage below threshold.",
        evidence={"coverage_percentage": 40, "threshold_percentage": 80},
        rule_id="low_coverage",
        rule_version="1",
        deduplication_key="low_coverage:tisseo:network:2026-01-01T08",
    )

    import mobility_control_tower.api.routes as route_module

    monkeypatch.setattr(route_module, "IncidentStore", lambda: store)
    client = TestClient(create_app(None, source="tisseo", serving_root=tmp_path / "serving"))
    readonly = create_access_token("viewer@example.test", {"public:read"}, expires_in_seconds=60)
    writer = create_access_token("operator@example.test", {"incidents:write"}, expires_in_seconds=60)

    assert client.post(f"/incidents/{incident['incident_id']}/acknowledge").status_code == 401
    assert client.post(f"/incidents/{incident['incident_id']}/acknowledge", headers={"Authorization": f"Bearer {readonly}"}).status_code == 401
    response = client.post(f"/incidents/{incident['incident_id']}/acknowledge", headers={"Authorization": f"Bearer {writer}"})

    assert response.status_code == 200
    assert response.json()["data"][0]["status"] == "ACKNOWLEDGED"


def test_expired_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "phase3-test-secret")
    token = create_access_token("operator@example.test", {"incidents:write"}, expires_in_seconds=-1)

    with pytest.raises(AuthenticationError):
        verify_access_token(token, {"incidents:write"})


def test_disallowed_feed_host_and_disabled_capability_fail_safely(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.yml"
    config_path.write_text(
        """
sources:
  demo:
    name: Demo
    city: Demo City
    country: FR
    timezone: Europe/Paris
    language: fr
    static_gtfs:
      enabled: true
      url: https://allowed.example/static.zip
    realtime:
      trip_updates:
        enabled: true
        url: https://allowed.example/trips.pb
      vehicle_positions:
        enabled: false
        url:
      service_alerts:
        enabled: false
        url:
""",
        encoding="utf-8",
    )
    source = load_sources(config_path)["demo"]

    with pytest.raises(ValueError, match="No enabled GTFS-Realtime URL"):
        collect_gtfs_rt_snapshot("demo", source, "vehicle_positions", raw_history_root=tmp_path / "raw", parsed_history_root=tmp_path / "history")


def test_automatic_healthy_period_resolution(tmp_path: Path) -> None:
    store = IncidentStore(tmp_path / "incidents")
    incident = store.open_or_update(
        incident_type="STALE_FEED",
        source="tisseo",
        entity_type="feed",
        entity_id="trip_updates",
        severity="WARNING",
        title="Trip Updates stale",
        summary="Feed age over threshold.",
        evidence={"feed_age_seconds": 300},
        rule_id="stale_trip_updates",
        rule_version="1",
        deduplication_key="stale_trip_updates:tisseo:trip_updates",
    )
    for row in store._read():
        row["last_observed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        store._write([row])

    resolved = store.auto_resolve_healthy(healthy_after_seconds=60)

    assert resolved[0]["incident_id"] == incident["incident_id"]
    assert resolved[0]["status"] == "RESOLVED"
