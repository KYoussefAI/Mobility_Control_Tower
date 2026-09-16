"""Smoke-test authoritative dbt reliability views in a serving DuckDB database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

REQUIRED_VIEWS = (
    "v_network_reliability",
    "v_route_reliability",
    "v_route_on_time_performance",
    "v_route_delay_distribution",
    "v_explicit_cancellations",
    "v_observed_headways",
    "v_headway_reliability_events",
    "v_excess_waiting_time",
    "v_realtime_trip_coverage",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--source", default="tisseo")
    args = parser.parse_args()
    if not args.database.is_file():
        print(f"Serving database not found: {args.database}")
        return 1
    with duckdb.connect(str(args.database), read_only=True) as connection:
        views = {row[0] for row in connection.execute("show tables").fetchall()}
        missing = sorted(set(REQUIRED_VIEWS) - views)
        if missing:
            print(f"Missing reliability views: {', '.join(missing)}")
            return 1
        coverage = connection.execute(
            "select eligible_scheduled_trip_count, observed_eligible_trip_count, coverage_percentage from v_realtime_trip_coverage where source = ? order by route_id limit 1",
            [args.source],
        ).fetchone()
        if not coverage:
            print("No realtime coverage rows found")
            return 1
        eligible, observed, coverage_percentage = coverage
        if observed > eligible:
            print("Coverage numerator exceeds denominator")
            return 1
        if coverage_percentage is not None and not (0 <= coverage_percentage <= 100):
            print("Coverage percentage outside 0..100")
            return 1
    print("Reliability serving smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
