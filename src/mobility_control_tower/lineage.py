"""Small OpenLineage-compatible local event writer.

This does not replace a real lineage backend. It gives local demo and tests a stable
event shape while the optional lineage profile can forward the same metadata later.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LINEAGE_SCHEMA_URL = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/definitions/RunEvent"


def dataset(namespace: str, name: str, facets: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"namespace": namespace, "name": name, "facets": facets or {}}


def run_event(
    *,
    job_namespace: str,
    job_name: str,
    event_type: str,
    inputs: list[dict[str, Any]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "eventType": event_type,
        "eventTime": now,
        "producer": "mobility-control-tower",
        "schemaURL": LINEAGE_SCHEMA_URL,
        "run": {
            "runId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{job_namespace}:{job_name}:{correlation_id or now}")),
            "facets": {"correlation": {"_producer": "mobility-control-tower", "_schemaURL": "", "correlationId": correlation_id}},
        },
        "job": {"namespace": job_namespace, "name": job_name},
        "inputs": inputs or [],
        "outputs": outputs or [],
    }


def append_event(event: dict[str, Any], root: Path = Path("data/lineage")) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    status = {
        "enabled": os.getenv("MCT_LINEAGE_ENABLED", "false").lower() in {"1", "true", "yes"},
        "backend": os.getenv("MCT_LINEAGE_BACKEND", "local_file"),
        "last_event_time": event.get("eventTime"),
        "event_count": sum(1 for _ in path.open(encoding="utf-8")),
    }
    (root / "status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
