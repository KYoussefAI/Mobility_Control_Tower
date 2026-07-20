"""Export selected reliability tables from a dbt DuckDB database."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
from compare_reliability_outputs import RELIABILITY_EXPORTS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(args.database), read_only=True) as connection:
        for filename in RELIABILITY_EXPORTS:
            table = filename.removesuffix(".csv")
            exists = connection.execute(
                "select count(*) from information_schema.tables where table_name = ?",
                [table],
            ).fetchone()[0]
            if exists:
                connection.execute(f"copy (select * from {table}) to ? (header, delimiter ',')", [str(args.output_dir / filename)])
    print(args.output_dir)


if __name__ == "__main__":
    main()
