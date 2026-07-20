"""Emit and validate one local OpenLineage-compatible event."""

from __future__ import annotations

import json
from pathlib import Path

from mobility_control_tower.lineage import append_event, dataset, run_event


def main() -> None:
    event = run_event(
        job_namespace="mobility-control-tower.local",
        job_name="lineage_smoke",
        event_type="COMPLETE",
        inputs=[dataset("mct://raw", "tisseo/trip_updates")],
        outputs=[dataset("mct://serving", "tisseo/current")],
        correlation_id="lineage-smoke",
    )
    path = append_event(event)
    latest = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    if latest["job"]["name"] != "lineage_smoke" or not latest["outputs"]:
        raise SystemExit("lineage smoke failed")
    status = json.loads(Path("data/lineage/status.json").read_text(encoding="utf-8"))
    print(f"lineage smoke passed: backend={status['backend']} enabled={status['enabled']}")


if __name__ == "__main__":
    main()
