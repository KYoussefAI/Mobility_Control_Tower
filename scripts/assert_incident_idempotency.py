"""Assert that repeated incident evaluation did not duplicate durable state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mobility_control_tower.incidents import IncidentStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-root", type=Path, default=Path("data/incidents"))
    parser.add_argument("--max-duplicate-events", type=int, default=0)
    args = parser.parse_args()

    store = IncidentStore(args.incident_root)
    incidents = store.list_incidents(limit=500)
    keys = [incident["deduplication_key"] for incident in incidents]
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    if duplicate_keys:
        print(f"incident idempotency failed: duplicate deduplication keys: {duplicate_keys}")
        return 1

    event_ids = [event["event_id"] for event in store.list_events(limit=1000)]
    duplicate_events = sorted({event_id for event_id in event_ids if event_ids.count(event_id) > 1})
    if len(duplicate_events) > args.max_duplicate_events:
        print(f"incident idempotency failed: duplicate event IDs: {duplicate_events}")
        return 1

    print(f"incident idempotency passed: {len(incidents)} incidents, {len(event_ids)} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
