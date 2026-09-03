"""Command-line interface for the available Mobility Control Tower workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from mobility_control_tower.config import load_source
from mobility_control_tower.ingestion.gtfs_raw import download_and_preserve_gtfs, preserve_gtfs_zip
from mobility_control_tower.profiling.gtfs_profile import profile_raw_run
from mobility_control_tower.transformations.gtfs_bronze import build_bronze
from mobility_control_tower.transformations.gtfs_silver import build_silver
from mobility_control_tower.quality.gtfs_quality import validate_silver_run
from mobility_control_tower.metrics.gtfs_kpis import build_gold
from mobility_control_tower.reporting.charts import generate_static_charts
from mobility_control_tower.reporting.demo_report import generate_demo_report, generate_static_mvp_report
from mobility_control_tower.analytics_engineering import generate_dbt_docs, run_dbt, run_quality_validation, test_dbt


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
    validate = commands.add_parser("validate-gtfs")
    validate.add_argument("--silver-run", type=Path, required=True)
    validate.add_argument("--reports-dir", type=Path, default=Path("data/reports"))
    gold = commands.add_parser("build-gold", help="Build initial static KPI tables")
    gold.add_argument("--silver-run", type=Path, required=True)
    gold.add_argument("--gold-root", type=Path, default=Path("data/gold"))
    report = commands.add_parser("generate-demo-report")
    report.add_argument("--gold-run", type=Path, required=True)
    report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))
    charts = commands.add_parser("generate-static-charts")
    charts.add_argument("--gold-run", type=Path, required=True)
    charts.add_argument("--reports-dir", type=Path, default=Path("data/reports"))
    mvp = commands.add_parser("generate-static-mvp-report")
    mvp.add_argument("--gold-run", type=Path, required=True)
    mvp.add_argument("--reports-dir", type=Path, default=Path("data/reports"))
    dbt_run = commands.add_parser("run-dbt")
    dbt_run.add_argument("--silver-run", type=Path, required=True)
    dbt_run.add_argument("--project-dir", type=Path, default=Path("dbt"))
    dbt_run.add_argument("--profiles-dir", type=Path, default=Path("dbt"))
    dbt_run.add_argument("--output-root", type=Path, default=Path("data/dbt_gold"))
    dbt_test = commands.add_parser("test-dbt")
    dbt_test.add_argument("--project-dir", type=Path, default=Path("dbt"))
    dbt_test.add_argument("--profiles-dir", type=Path, default=Path("dbt"))
    dbt_docs = commands.add_parser("generate-dbt-docs")
    dbt_docs.add_argument("--project-dir", type=Path, default=Path("dbt"))
    dbt_docs.add_argument("--profiles-dir", type=Path, default=Path("dbt"))
    quality = commands.add_parser("run-quality-validation")
    quality.add_argument("--suite", choices=["silver", "gold", "all"], default="all")
    quality.add_argument("--silver-run", type=Path)
    quality.add_argument("--gold-run", type=Path)
    quality.add_argument("--ge-root", type=Path, default=Path("quality_contracts"))
    quality.add_argument("--quality-root", type=Path, default=Path("data/quality"))
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
        elif args.command == "validate-gtfs": result = validate_silver_run(args.silver_run, args.reports_dir)
        elif args.command == "build-gold": result = build_gold(args.silver_run, args.gold_root)
        elif args.command == "generate-demo-report": result = generate_demo_report(args.gold_run, args.reports_dir)
        elif args.command == "generate-static-charts": result = generate_static_charts(args.gold_run, args.reports_dir)
        elif args.command == "generate-static-mvp-report": result = generate_static_mvp_report(args.gold_run, args.reports_dir)
        elif args.command == "run-dbt": result = run_dbt(silver_run=args.silver_run, project_dir=args.project_dir, profiles_dir=args.profiles_dir, output_root=args.output_root)
        elif args.command == "test-dbt": result = test_dbt(args.project_dir, args.profiles_dir)
        elif args.command == "generate-dbt-docs": result = generate_dbt_docs(args.project_dir, args.profiles_dir)
        elif args.command == "run-quality-validation": result = run_quality_validation(suite_name=args.suite, silver_run=args.silver_run, gold_run=args.gold_run, ge_root=args.ge_root, quality_root=args.quality_root)
        if result is not None:
            print(result)
        return 0
    except Exception as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
