"""Parse GTFS-Realtime protobuf snapshots into simple CSV tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from google.transit import gtfs_realtime_pb2


def _enum_name(enum_type: Any, value: int | None) -> str:
    if value is None:
        return ""
    try:
        return enum_type.Name(value)
    except ValueError:
        return str(value)


def _translation_text(translated: Any) -> str:
    if not translated.translation:
        return ""
    for translation in translated.translation:
        if translation.text:
            return translation.text
    return ""


def _metadata(raw_run: Path) -> dict[str, Any]:
    path = raw_run / "metadata.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _feed_type_from_raw_run(raw_run: Path, metadata: dict[str, Any]) -> str:
    return metadata.get("feed_type") or raw_run.parent.name


def _unix_to_iso(value: int | None) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _feed_age_seconds(header_timestamp: int | None, fetched_at: str | None) -> int | None:
    if not header_timestamp or not fetched_at:
        return None
    try:
        fetched = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(fetched.timestamp() - header_timestamp)


def _summary(feed: gtfs_realtime_pb2.FeedMessage, feed_type: str, fetched_at: str | None, parsed_count: int, skipped_count: int) -> pd.DataFrame:
    header_timestamp = feed.header.timestamp if feed.header.HasField("timestamp") else None
    row = {
        "feed_type": feed_type,
        "gtfs_realtime_version": feed.header.gtfs_realtime_version,
        "header_timestamp": header_timestamp or "",
        "header_timestamp_iso": _unix_to_iso(header_timestamp),
        "fetched_at": fetched_at or "",
        "feed_age_seconds": _feed_age_seconds(header_timestamp, fetched_at),
        "entity_count": len(feed.entity),
        "parsed_entity_count": parsed_count,
        "skipped_entity_count": skipped_count,
    }
    return pd.DataFrame([row])


def _trip_updates(feed: gtfs_realtime_pb2.FeedMessage) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    trip_rows: list[dict[str, Any]] = []
    stop_rows: list[dict[str, Any]] = []
    skipped = 0
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            skipped += 1
            continue
        update = entity.trip_update
        trip = update.trip
        trip_rows.append(
            {
                "entity_id": entity.id,
                "trip_id": trip.trip_id,
                "route_id": trip.route_id,
                "start_date": trip.start_date,
                "start_time": trip.start_time,
                "schedule_relationship": _enum_name(gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship, trip.schedule_relationship),
                "trip_update_timestamp": update.timestamp if update.HasField("timestamp") else "",
                "stop_time_update_count": len(update.stop_time_update),
            }
        )
        for stop_update in update.stop_time_update:
            arrival = stop_update.arrival if stop_update.HasField("arrival") else None
            departure = stop_update.departure if stop_update.HasField("departure") else None
            stop_rows.append(
                {
                    "entity_id": entity.id,
                    "trip_id": trip.trip_id,
                    "route_id": trip.route_id,
                    "stop_sequence": stop_update.stop_sequence if stop_update.HasField("stop_sequence") else "",
                    "stop_id": stop_update.stop_id,
                    "arrival_time": arrival.time if arrival and arrival.HasField("time") else "",
                    "arrival_delay": arrival.delay if arrival and arrival.HasField("delay") else "",
                    "departure_time": departure.time if departure and departure.HasField("time") else "",
                    "departure_delay": departure.delay if departure and departure.HasField("delay") else "",
                    "schedule_relationship": _enum_name(gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship, stop_update.schedule_relationship),
                }
            )
    return pd.DataFrame(trip_rows), pd.DataFrame(stop_rows), len(trip_rows), skipped


def _vehicle_positions(feed: gtfs_realtime_pb2.FeedMessage) -> tuple[pd.DataFrame, int, int]:
    rows: list[dict[str, Any]] = []
    skipped = 0
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            skipped += 1
            continue
        vehicle = entity.vehicle
        trip = vehicle.trip
        descriptor = vehicle.vehicle
        position = vehicle.position
        rows.append(
            {
                "entity_id": entity.id,
                "trip_id": trip.trip_id,
                "route_id": trip.route_id,
                "vehicle_id": descriptor.id,
                "label": descriptor.label,
                "latitude": position.latitude if vehicle.HasField("position") else "",
                "longitude": position.longitude if vehicle.HasField("position") else "",
                "bearing": position.bearing if vehicle.HasField("position") and position.HasField("bearing") else "",
                "speed": position.speed if vehicle.HasField("position") and position.HasField("speed") else "",
                "current_stop_sequence": vehicle.current_stop_sequence if vehicle.HasField("current_stop_sequence") else "",
                "stop_id": vehicle.stop_id,
                "current_status": _enum_name(gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus, vehicle.current_status),
                "timestamp": vehicle.timestamp if vehicle.HasField("timestamp") else "",
            }
        )
    return pd.DataFrame(rows), len(rows), skipped


def _alerts(feed: gtfs_realtime_pb2.FeedMessage) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    alert_rows: list[dict[str, Any]] = []
    entity_rows: list[dict[str, Any]] = []
    skipped = 0
    for entity in feed.entity:
        if not entity.HasField("alert"):
            skipped += 1
            continue
        alert = entity.alert
        periods = list(alert.active_period) or [None]
        for period in periods:
            alert_rows.append(
                {
                    "entity_id": entity.id,
                    "cause": _enum_name(gtfs_realtime_pb2.Alert.Cause, alert.cause),
                    "effect": _enum_name(gtfs_realtime_pb2.Alert.Effect, alert.effect),
                    "active_period_start": period.start if period and period.HasField("start") else "",
                    "active_period_end": period.end if period and period.HasField("end") else "",
                    "header_text": _translation_text(alert.header_text),
                    "description_text": _translation_text(alert.description_text),
                    "url": _translation_text(alert.url),
                }
            )
        for informed in alert.informed_entity:
            entity_rows.append(
                {
                    "entity_id": entity.id,
                    "agency_id": informed.agency_id,
                    "route_id": informed.route_id,
                    "route_type": informed.route_type if informed.HasField("route_type") else "",
                    "trip_id": informed.trip.trip_id if informed.HasField("trip") else "",
                    "stop_id": informed.stop_id,
                }
            )
    return pd.DataFrame(alert_rows), pd.DataFrame(entity_rows), len(alert_rows), skipped


def parse_realtime_snapshot(raw_rt_run: Path, output_root: Path = Path("data/realtime")) -> Path:
    feed_path = raw_rt_run / "feed.pb"
    if not feed_path.is_file():
        raise FileNotFoundError(f"GTFS-Realtime feed.pb not found: {feed_path}")
    metadata = _metadata(raw_rt_run)
    source_id = metadata.get("source_id") or raw_rt_run.parents[1].name
    feed_type = _feed_type_from_raw_run(raw_rt_run, metadata)
    output_dir = output_root / source_id / feed_type / raw_rt_run.name
    output_dir.mkdir(parents=True, exist_ok=False)

    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(feed_path.read_bytes())
    except Exception as exc:
        raise ValueError(f"Unable to parse GTFS-Realtime protobuf snapshot: {exc}") from exc

    tables: dict[str, pd.DataFrame] = {}
    if feed_type == "trip_updates":
        trip_updates, stop_updates, parsed, skipped = _trip_updates(feed)
        tables["rt_trip_updates"] = trip_updates
        tables["rt_stop_time_updates"] = stop_updates
    elif feed_type == "vehicle_positions":
        vehicle_positions, parsed, skipped = _vehicle_positions(feed)
        tables["rt_vehicle_positions"] = vehicle_positions
    elif feed_type == "service_alerts":
        alerts, informed, parsed, skipped = _alerts(feed)
        tables["rt_alerts"] = alerts
        tables["rt_alert_informed_entities"] = informed
    else:
        raise ValueError(f"Unsupported GTFS-Realtime feed type in raw run: {feed_type}")

    tables["rt_feed_summary"] = _summary(feed, feed_type, metadata.get("fetched_at"), parsed, skipped)
    manifest_tables: dict[str, dict[str, Any]] = {}
    for name, frame in tables.items():
        path = output_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        manifest_tables[name] = {"file": path.name, "row_count": len(frame), "columns": list(frame.columns)}

    manifest = {
        "source_raw_realtime_run": str(raw_rt_run),
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        "feed_type": feed_type,
        "tables_created": manifest_tables,
        "snapshot_note": "Parsed from a saved local feed.pb snapshot; this is not continuous streaming.",
    }
    (output_dir / "realtime_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_dir
