"""Create deterministic local Silver and historical fixtures for dbt/serving tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def main() -> None:
    silver = Path("data/fixtures/silver/tisseo/phase1")
    history_root = Path("data/fixtures/realtime_history/tisseo/trip_updates")
    write_csv(
        silver / "routes.csv",
        [
            {"route_id": "R1", "route_short_name": "A", "route_long_name": "Airport", "route_type": "3"},
            {"route_id": "R2", "route_short_name": "M", "route_long_name": "Metro", "route_type": "1"},
        ],
    )
    write_csv(
        silver / "trips.csv",
        [
            {"route_id": "R1", "service_id": "WK", "trip_id": "T1"},
            {"route_id": "R1", "service_id": "WK", "trip_id": "T2"},
            {"route_id": "R2", "service_id": "SPECIAL", "trip_id": "T3"},
        ],
    )
    write_csv(
        silver / "stop_times.csv",
        [
            {"trip_id": "T1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "S1", "stop_sequence": 1, "departure_time_seconds": 28800},
            {"trip_id": "T1", "arrival_time": "08:10:00", "departure_time": "08:10:00", "stop_id": "S2", "stop_sequence": 2, "departure_time_seconds": 29400},
            {"trip_id": "T2", "arrival_time": "25:10:00", "departure_time": "25:10:00", "stop_id": "S1", "stop_sequence": 1, "departure_time_seconds": 90600},
            {"trip_id": "T2", "arrival_time": "25:20:00", "departure_time": "25:20:00", "stop_id": "S3", "stop_sequence": 2, "departure_time_seconds": 91200},
            {"trip_id": "T3", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "S2", "stop_sequence": 1, "departure_time_seconds": 32400},
            {"trip_id": "T3", "arrival_time": "09:10:00", "departure_time": "09:10:00", "stop_id": "S3", "stop_sequence": 2, "departure_time_seconds": 33000},
        ],
    )
    write_csv(
        silver / "stops.csv",
        [
            {"stop_id": "S1", "stop_name": "Central", "stop_lat": 43.6, "stop_lon": 1.44},
            {"stop_id": "S2", "stop_name": "North", "stop_lat": 43.61, "stop_lon": 1.45},
            {"stop_id": "S3", "stop_name": "South", "stop_lat": 43.62, "stop_lon": 1.46},
        ],
    )
    write_csv(
        silver / "calendar.csv",
        [
            {
                "service_id": "WK",
                "monday": 1,
                "tuesday": 1,
                "wednesday": 0,
                "thursday": 0,
                "friday": 0,
                "saturday": 0,
                "sunday": 0,
                "start_date": 20260105,
                "end_date": 20260106,
            }
        ],
    )
    write_csv(
        silver / "calendar_dates.csv",
        [
            {"service_id": "WK", "date": 20260106, "exception_type": 2},
            {"service_id": "WK", "date": 20260107, "exception_type": 1},
            {"service_id": "SPECIAL", "date": 20260108, "exception_type": 1},
        ],
    )
    snapshots = [
        {
            "snapshot_timestamp": "fixture-1",
            "collection_time": "2026-01-05T08:00:00+00:00",
            "feed_age_seconds": 30,
            "poll_number": 1,
            "collection_date": "2026-01-05",
            "collection_hour": "08",
            "delay": 60,
            "checksum": "fixture-checksum-1",
        },
        {
            "snapshot_timestamp": "fixture-2",
            "collection_time": "2026-01-05T08:05:00+00:00",
            "feed_age_seconds": 35,
            "poll_number": 2,
            "collection_date": "2026-01-05",
            "collection_hour": "08",
            "delay": 120,
            "checksum": "fixture-checksum-2",
        },
        {
            "snapshot_timestamp": "fixture-3",
            "collection_time": "2026-01-05T09:10:00+00:00",
            "feed_age_seconds": 45,
            "poll_number": 3,
            "collection_date": "2026-01-05",
            "collection_hour": "09",
            "delay": 0,
            "checksum": "fixture-checksum-3",
        },
    ]
    for snapshot in snapshots:
        history = (
            history_root
            / f"date={snapshot['collection_date']}"
            / f"hour={snapshot['collection_hour']}"
            / f"snapshot_timestamp={snapshot['snapshot_timestamp']}"
        )
        history.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "source": "tisseo",
                    "feed_type": "trip_updates",
                    "snapshot_id": snapshot["snapshot_timestamp"],
                    "snapshot_timestamp": snapshot["snapshot_timestamp"],
                    "collection_time": snapshot["collection_time"],
                    "feed_header_timestamp": "2026-01-05T07:59:30+00:00",
                    "payload_checksum": snapshot["checksum"],
                    "feed_age_seconds": snapshot["feed_age_seconds"],
                    "poll_number": snapshot["poll_number"],
                    "collection_date": snapshot["collection_date"],
                    "collection_hour": snapshot["collection_hour"],
                    "trip_id": "T1",
                    "route_id": "R1",
                    "schedule_relationship": "SCHEDULED",
                }
            ]
        ).to_parquet(history / "trip_updates.parquet", index=False)
        pd.DataFrame(
            [
                {
                    "source": "tisseo",
                    "feed_type": "trip_updates",
                    "snapshot_id": snapshot["snapshot_timestamp"],
                    "snapshot_timestamp": snapshot["snapshot_timestamp"],
                    "collection_time": snapshot["collection_time"],
                    "feed_header_timestamp": "2026-01-05T07:59:30+00:00",
                    "payload_checksum": snapshot["checksum"],
                    "feed_age_seconds": snapshot["feed_age_seconds"],
                    "poll_number": snapshot["poll_number"],
                    "collection_date": snapshot["collection_date"],
                    "collection_hour": snapshot["collection_hour"],
                    "trip_id": "T1",
                    "route_id": "R1",
                    "stop_id": "S1",
                    "stop_sequence": 1,
                    "arrival_delay": snapshot["delay"],
                    "departure_delay": snapshot["delay"],
                    "arrival_time": "2026-01-05T08:01:00+00:00",
                    "departure_time": "2026-01-05T08:01:05+00:00",
                    "schedule_relationship": "SCHEDULED",
                }
            ]
        ).to_parquet(history / "stop_time_updates.parquet", index=False)
        pd.DataFrame(
            [
                {
                    "source": "tisseo",
                    "snapshot_id": snapshot["snapshot_timestamp"],
                    "snapshot_timestamp": snapshot["snapshot_timestamp"],
                    "collection_time": snapshot["collection_time"],
                    "feed_header_timestamp": "2026-01-05T07:59:30+00:00",
                    "payload_checksum": snapshot["checksum"],
                    "feed_age_seconds": snapshot["feed_age_seconds"],
                    "poll_number": snapshot["poll_number"],
                    "collection_date": snapshot["collection_date"],
                    "collection_hour": snapshot["collection_hour"],
                    "feed_type": "trip_updates",
                    "gtfs_realtime_version": "2.0",
                    "header_timestamp": 1767600000,
                    "header_timestamp_iso": "2026-01-05T07:59:30+00:00",
                    "entity_count": 1,
                    "parsed_entity_count": 1,
                    "skipped_entity_count": 0,
                }
            ]
        ).to_parquet(history / "feed_summary.parquet", index=False)
        (history / "metadata.json").write_text(
            pd.Series(
                {
                    "source_id": "tisseo",
                    "feed_type": "trip_updates",
                    "snapshot_id": snapshot["snapshot_timestamp"],
                    "snapshot_timestamp": snapshot["snapshot_timestamp"],
                    "collection_time": snapshot["collection_time"],
                    "collection_date": snapshot["collection_date"],
                    "collection_hour": snapshot["collection_hour"],
                    "sha256": snapshot["checksum"],
                    "trip_update_rows": 1,
                    "stop_time_update_rows": 1,
                }
            ).to_json(indent=2)
            + "\n",
            encoding="utf-8",
        )
        (history / "_SUCCESS").write_text("ok\n", encoding="utf-8")


if __name__ == "__main__":
    main()
