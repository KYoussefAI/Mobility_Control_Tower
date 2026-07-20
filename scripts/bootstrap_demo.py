"""Bootstrap a deterministic local demonstration without live feed access."""

from __future__ import annotations

import json
from pathlib import Path

from create_deterministic_fixture import main as create_fixture

from mobility_control_tower.analytics_engineering import run_dbt, run_quality_validation
from mobility_control_tower.operations.watermarks import advance_watermark_after_publish, watermark_lock
from mobility_control_tower.realtime.historical_storage import discover_committed_snapshots
from mobility_control_tower.serving.duckdb_loader import build_serving_database


def main() -> None:
    source = "tisseo"
    feed_type = "trip_updates"
    create_fixture()
    silver = Path("data/fixtures/silver/tisseo/phase1")
    history = Path("data/fixtures/realtime_history/tisseo/trip_updates")
    dbt_gold = run_dbt(silver_run=silver, history_run=history, output_root=Path("data/fixtures/dbt_gold"))
    quality_path = run_quality_validation(suite_name="all", silver_run=silver, gold_run=dbt_gold, history_run=history, quality_root=Path("data/quality"))
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality_status = "passed" if quality.get("success") else "failed"
    serving_run = build_serving_database(
        dbt_gold,
        serving_root=Path("data/serving"),
        history_run=history,
        history_gold_run=dbt_gold,
        quality_status=quality_status,
    )
    snapshots = discover_committed_snapshots(history)
    with watermark_lock(Path("data/watermarks"), source, feed_type, "incremental_refresh"):
        advance_watermark_after_publish(
            Path("data/watermarks"),
            source=source,
            feed_type=feed_type,
            workflow="incremental_refresh",
            snapshot=snapshots[-1] if snapshots else None,
            serving_run_id=serving_run.name,
            status="success",
        )
    print(f"Demo serving run published: {serving_run}")


if __name__ == "__main__":
    main()
