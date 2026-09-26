"""Small command-line interface used by developers and Airflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import data_root, latest_run, load_source
from .dbt import build_dbt
from .quality import require_pass, validate_realtime, validate_static
from .realtime_pipeline import download_realtime, ensure_empty_realtime_tables
from .static_pipeline import download_static, transform_static


def _static_pipeline(root: Path, *, run_dbt: bool = True) -> dict[str, str]:
    source = load_source()
    raw = download_static(source, root)
    silver = transform_static(raw, root)
    ensure_empty_realtime_tables(root)
    report_path = root / "quality" / f"static-{silver.name}.json"
    require_pass(validate_static(silver, report_path))
    database = build_dbt(silver, root) if run_dbt else None
    return {"raw_run": str(raw), "silver_run": str(silver), "database": str(database) if database else "not-run"}


def _realtime_pipeline(root: Path, *, run_dbt: bool = True) -> dict[str, object]:
    source = load_source()
    metadata = download_realtime(source, root)
    report_path = root / "quality" / "realtime-latest.json"
    require_pass(validate_realtime(root, report_path))
    static_run = latest_run(root / "silver" / "static")
    database = build_dbt(static_run, root) if run_dbt else None
    return {**metadata, "database": str(database) if database else "not-run"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="mct", description="Tisséo Mobility Control Tower pipelines")
    result.add_argument("--data-root", type=Path, default=data_root())
    subparsers = result.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ingest-static", help="Download and preserve one GTFS archive")
    transform = subparsers.add_parser("transform-static", help="Build Bronze and Silver from a raw run")
    transform.add_argument("raw_run", type=Path)
    subparsers.add_parser("collect-realtime", help="Fetch and preserve one Trip Updates snapshot")
    quality = subparsers.add_parser("quality", help="Run focused Python checks")
    quality.add_argument("layer", choices=("static", "realtime"))
    build = subparsers.add_parser("dbt-build", help="Build and test dbt Gold marts")
    build.add_argument("--static-run", type=Path)
    static = subparsers.add_parser("static-pipeline", help="Run the complete static workflow")
    static.add_argument("--skip-dbt", action="store_true")
    realtime = subparsers.add_parser("realtime-pipeline", help="Run one complete realtime poll")
    realtime.add_argument("--skip-dbt", action="store_true")
    return result


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    root: Path = args.data_root.resolve()
    source = load_source()
    if args.command == "ingest-static":
        output: object = {"raw_run": str(download_static(source, root))}
    elif args.command == "transform-static":
        output = {"silver_run": str(transform_static(args.raw_run.resolve(), root))}
    elif args.command == "collect-realtime":
        output = download_realtime(source, root)
    elif args.command == "quality":
        report = (
            validate_static(latest_run(root / "silver" / "static"))
            if args.layer == "static"
            else validate_realtime(root)
        )
        require_pass(report)
        output = report
    elif args.command == "dbt-build":
        static_run = args.static_run.resolve() if args.static_run else latest_run(root / "silver" / "static")
        ensure_empty_realtime_tables(root)
        output = {"database": str(build_dbt(static_run, root))}
    elif args.command == "static-pipeline":
        output = _static_pipeline(root, run_dbt=not args.skip_dbt)
    else:
        output = _realtime_pipeline(root, run_dbt=not args.skip_dbt)
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
