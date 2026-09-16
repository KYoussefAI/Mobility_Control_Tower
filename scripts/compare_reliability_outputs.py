"""Compare dbt reliability exports from two runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RELIABILITY_EXPORTS = (
    "realtime_trip_coverage.csv",
    "route_delay_distribution.csv",
    "network_delay_distribution.csv",
    "route_on_time_performance.csv",
    "network_reliability_summary.csv",
    "fct_explicit_trip_cancellations.csv",
)


def _read(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"missing reliability export: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False).sort_index(axis=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-refresh", type=Path, required=True)
    parser.add_argument("--incremental", type=Path, required=True)
    args = parser.parse_args()
    failures: list[str] = []
    if not args.full_refresh.is_dir():
        failures.append(f"missing full-refresh export directory: {args.full_refresh}")
    if not args.incremental.is_dir():
        failures.append(f"missing incremental export directory: {args.incremental}")
    for filename in RELIABILITY_EXPORTS:
        try:
            left = _read(args.full_refresh / filename)
            right = _read(args.incremental / filename)
        except FileNotFoundError as exc:
            failures.append(str(exc))
            continue
        left = left.sort_values(list(left.columns)).reset_index(drop=True)
        right = right.sort_values(list(right.columns)).reset_index(drop=True)
        try:
            pd.testing.assert_frame_equal(left, right, check_dtype=False)
        except AssertionError as exc:
            failures.append(f"{filename}: {exc}")
    if failures:
        print("Reliability output comparison failed:")
        print("\n".join(failures))
        return 1
    print("Reliability output comparison passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
