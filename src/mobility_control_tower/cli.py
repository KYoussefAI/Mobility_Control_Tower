"""Command-line interface for the available Mobility Control Tower workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from mobility_control_tower.config import load_source
from mobility_control_tower.ingestion.gtfs_raw import download_and_preserve_gtfs, preserve_gtfs_zip
from mobility_control_tower.profiling.gtfs_profile import profile_raw_run
from mobility_control_tower.transformations.gtfs_bronze import build_bronze
from mobility_control_tower.transformations.gtfs_silver import build_silver


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mobility-control-tower")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest-gtfs", help="Preserve a static GTFS ZIP")
    ingest.add_argument("--source", required=True)
    mode = ingest.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-zip", type=Path)
    mode.add_argument("--download", action="store_true")
    ingest.add_argument("--config", type=Path, default=Path("config/sources.yml"))
    ingest.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    profile = commands.add_parser("profile-gtfs")
    profile.add_argument("--raw-run", type=Path, required=True)
    profile.add_argument("--reports-dir", type=Path, default=Path("data/reports"))
    bronze = commands.add_parser("build-bronze")
    bronze.add_argument("--raw-run", type=Path, required=True)
    bronze.add_argument("--bronze-root", type=Path, default=Path("data/bronze"))
    silver = commands.add_parser("build-silver")
    silver.add_argument("--bronze-run", type=Path, required=True)
    silver.add_argument("--silver-root", type=Path, default=Path("data/silver"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = None
        if args.command == "ingest-gtfs":
            source = load_source(args.source, args.config)
            result = preserve_gtfs_zip(args.local_zip, args.source, source, args.raw_root) if args.local_zip else download_and_preserve_gtfs(args.source, source, args.raw_root)
        elif args.command == "profile-gtfs": result = profile_raw_run(args.raw_run, args.reports_dir)
        elif args.command == "build-bronze": result = build_bronze(args.raw_run, args.bronze_root)
        elif args.command == "build-silver": result = build_silver(args.bronze_run, args.silver_root)
        if result is not None:
            print(result)
        return 0
    except Exception as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
