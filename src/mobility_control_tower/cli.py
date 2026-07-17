"""Command-line interface for the Mobility Control Tower GTFS workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from mobility_control_tower.api.app import create_app
from mobility_control_tower.api.report import generate_api_report
from mobility_control_tower.config import load_source
from mobility_control_tower.ingestion.gtfs_raw import download_and_preserve_gtfs, preserve_gtfs_zip
from mobility_control_tower.metrics.gtfs_kpis import build_gold
from mobility_control_tower.profiling.gtfs_profile import profile_raw_run
from mobility_control_tower.quality.gtfs_quality import validate_silver_run
from mobility_control_tower.realtime.gtfs_rt_compatibility import check_realtime_compatibility
from mobility_control_tower.realtime.gtfs_rt_charts import generate_rt_charts
from mobility_control_tower.realtime.gtfs_rt_kpis import build_rt_gold
from mobility_control_tower.realtime.gtfs_rt_parser import parse_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_raw import FEED_TYPES, fetch_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_report import generate_realtime_report
from mobility_control_tower.realtime.gtfs_rt_snapshot_report import generate_rt_snapshot_report
from mobility_control_tower.reporting.charts import generate_static_charts
from mobility_control_tower.reporting.demo_report import generate_demo_report, generate_static_mvp_report
from mobility_control_tower.reporting.final_report import generate_final_report
from mobility_control_tower.serving.duckdb_loader import build_serving_database, dataframe_to_text_table, query_serving_database
from mobility_control_tower.serving.serving_report import generate_serving_report
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

    profile = commands.add_parser("profile-gtfs", help="Profile a preserved raw GTFS run")
    profile.add_argument("--raw-run", type=Path, required=True)
    profile.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    bronze = commands.add_parser("build-bronze", help="Extract a raw GTFS run into bronze files")
    bronze.add_argument("--raw-run", type=Path, required=True)
    bronze.add_argument("--bronze-root", type=Path, default=Path("data/bronze"))

    silver = commands.add_parser("build-silver", help="Clean a bronze GTFS run into silver CSV tables")
    silver.add_argument("--bronze-run", type=Path, required=True)
    silver.add_argument("--silver-root", type=Path, default=Path("data/silver"))

    validate = commands.add_parser("validate-gtfs", help="Run basic checks on a silver GTFS run")
    validate.add_argument("--silver-run", type=Path, required=True)
    validate.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    gold = commands.add_parser("build-gold", help="Build static-schedule KPI tables from silver GTFS")
    gold.add_argument("--silver-run", type=Path, required=True)
    gold.add_argument("--gold-root", type=Path, default=Path("data/gold"))

    report = commands.add_parser("generate-demo-report", help="Generate a Markdown report from a gold run")
    report.add_argument("--gold-run", type=Path, required=True)
    report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    charts = commands.add_parser("generate-static-charts", help="Generate static PNG charts from gold KPI tables")
    charts.add_argument("--gold-run", type=Path, required=True)
    charts.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    static_mvp = commands.add_parser("generate-static-mvp-report", help="Generate a concise static MVP evidence report")
    static_mvp.add_argument("--gold-run", type=Path, required=True)
    static_mvp.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    fetch_rt = commands.add_parser("fetch-gtfs-rt", help="Fetch and preserve one GTFS-Realtime protobuf snapshot")
    fetch_rt.add_argument("--source", required=True)
    fetch_rt.add_argument("--feed-type", choices=sorted(FEED_TYPES), required=True)
    fetch_rt.add_argument("--url")
    fetch_rt.add_argument("--config", type=Path, default=Path("config/sources.yml"))
    fetch_rt.add_argument("--raw-rt-root", type=Path, default=Path("data/raw_realtime"))

    parse_rt = commands.add_parser("parse-gtfs-rt", help="Parse a preserved GTFS-Realtime snapshot into CSV tables")
    parse_rt.add_argument("--raw-rt-run", type=Path, required=True)
    parse_rt.add_argument("--rt-root", type=Path, default=Path("data/realtime"))

    report_rt = commands.add_parser("report-gtfs-rt", help="Generate a Markdown report for a parsed GTFS-Realtime run")
    report_rt.add_argument("--rt-run", type=Path, required=True)
    report_rt.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    compat_rt = commands.add_parser("check-rt-compatibility", help="Compare parsed real-time IDs with static silver GTFS")
    compat_rt.add_argument("--silver-run", type=Path, required=True)
    compat_rt.add_argument("--rt-run", type=Path, required=True)
    compat_rt.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    rt_gold = commands.add_parser("build-rt-gold", help="Build snapshot KPI tables from parsed GTFS-Realtime and static silver GTFS")
    rt_gold.add_argument("--silver-run", type=Path, required=True)
    rt_gold.add_argument("--rt-run", type=Path, required=True)
    rt_gold.add_argument("--rt-gold-root", type=Path, default=Path("data/realtime_gold"))

    rt_charts = commands.add_parser("generate-rt-charts", help="Generate static PNG charts from real-time gold tables")
    rt_charts.add_argument("--rt-gold-run", type=Path, required=True)
    rt_charts.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    rt_snapshot_report = commands.add_parser("generate-rt-snapshot-report", help="Generate a Markdown report from real-time gold tables")
    rt_snapshot_report.add_argument("--rt-gold-run", type=Path, required=True)
    rt_snapshot_report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    serving = commands.add_parser("build-serving-db", help="Build a local DuckDB serving database from gold outputs")
    serving.add_argument("--gold-run", type=Path, required=True)
    serving.add_argument("--rt-gold-run", type=Path)
    serving.add_argument("--serving-root", type=Path, default=Path("data/serving"))

    serving_query = commands.add_parser("query-serving-db", help="Run a predefined query against the serving DuckDB database")
    serving_query.add_argument("--db", type=Path, required=True)
    serving_query.add_argument("--query-name", required=True)
    serving_query.add_argument("--limit", type=int, default=10)

    serving_report = commands.add_parser("generate-serving-report", help="Generate a Markdown report for a serving database run")
    serving_report.add_argument("--serving-run", type=Path, required=True)
    serving_report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    api = commands.add_parser("serve-api", help="Start the local read-only FastAPI server")
    api.add_argument("--db", type=Path, required=True)
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)

    api_report = commands.add_parser("generate-api-report", help="Generate a Markdown report for the local API")
    api_report.add_argument("--db", type=Path, required=True)
    api_report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    dashboard = commands.add_parser("serve-dashboard", help="Start the local read-only Streamlit dashboard")
    dashboard.add_argument("--api-url", default="http://127.0.0.1:8000")

    final_report = commands.add_parser("generate-final-report", help="Generate the final academic project report")
    final_report.add_argument("--serving-run", type=Path, required=True)
    final_report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "ingest-gtfs":
            source = load_source(args.source, args.config)
            if args.download:
                run_dir = download_and_preserve_gtfs(args.source, source, args.raw_root)
            else:
                run_dir = preserve_gtfs_zip(args.local_zip, args.source, source, args.raw_root)
            print(f"Raw GTFS preserved in: {run_dir}")
            print(f"Metadata written to: {run_dir / 'metadata.json'}")
        elif args.command == "profile-gtfs":
            json_path, markdown_path = profile_raw_run(args.raw_run, args.reports_dir)
            print(f"JSON report written to: {json_path}")
            print(f"Markdown report written to: {markdown_path}")
        elif args.command == "build-bronze":
            run_dir = build_bronze(args.raw_run, args.bronze_root)
            print(f"Bronze GTFS written to: {run_dir}")
            print(f"Manifest written to: {run_dir / 'bronze_manifest.json'}")
        elif args.command == "build-silver":
            run_dir = build_silver(args.bronze_run, args.silver_root)
            print(f"Silver GTFS written to: {run_dir}")
            print(f"Manifest written to: {run_dir / 'silver_manifest.json'}")
        elif args.command == "validate-gtfs":
            json_path, markdown_path = validate_silver_run(args.silver_run, args.reports_dir)
            print(f"JSON quality report written to: {json_path}")
            print(f"Markdown quality report written to: {markdown_path}")
        elif args.command == "build-gold":
            run_dir = build_gold(args.silver_run, args.gold_root)
            print(f"Gold KPI tables written to: {run_dir}")
            print(f"Manifest written to: {run_dir / 'gold_manifest.json'}")
        elif args.command == "generate-demo-report":
            report_path = generate_demo_report(args.gold_run, args.reports_dir)
            print(f"Demo report written to: {report_path}")
        elif args.command == "generate-static-charts":
            figures_dir = generate_static_charts(args.gold_run, args.reports_dir)
            print(f"Static charts written to: {figures_dir}")
        elif args.command == "generate-static-mvp-report":
            report_path = generate_static_mvp_report(args.gold_run, args.reports_dir)
            print(f"Static MVP evidence report written to: {report_path}")
        elif args.command == "fetch-gtfs-rt":
            source = load_source(args.source, args.config)
            run_dir = fetch_realtime_snapshot(args.source, source, args.feed_type, args.url, args.raw_rt_root)
            print(f"Raw GTFS-Realtime snapshot preserved in: {run_dir}")
            print(f"Metadata written to: {run_dir / 'metadata.json'}")
        elif args.command == "parse-gtfs-rt":
            run_dir = parse_realtime_snapshot(args.raw_rt_run, args.rt_root)
            print(f"Parsed GTFS-Realtime tables written to: {run_dir}")
            print(f"Manifest written to: {run_dir / 'realtime_manifest.json'}")
        elif args.command == "report-gtfs-rt":
            report_path = generate_realtime_report(args.rt_run, args.reports_dir)
            print(f"GTFS-Realtime report written to: {report_path}")
        elif args.command == "check-rt-compatibility":
            json_path, markdown_path = check_realtime_compatibility(args.silver_run, args.rt_run, args.reports_dir)
            print(f"JSON compatibility report written to: {json_path}")
            print(f"Markdown compatibility report written to: {markdown_path}")
        elif args.command == "build-rt-gold":
            run_dir = build_rt_gold(args.silver_run, args.rt_run, args.rt_gold_root)
            print(f"Real-time gold snapshot tables written to: {run_dir}")
            print(f"Manifest written to: {run_dir / 'rt_gold_manifest.json'}")
        elif args.command == "generate-rt-charts":
            figures_dir = generate_rt_charts(args.rt_gold_run, args.reports_dir)
            print(f"Real-time snapshot charts written to: {figures_dir}")
        elif args.command == "generate-rt-snapshot-report":
            report_path = generate_rt_snapshot_report(args.rt_gold_run, args.reports_dir)
            print(f"Real-time snapshot report written to: {report_path}")
        elif args.command == "build-serving-db":
            serving_run = build_serving_database(args.gold_run, args.rt_gold_run, args.serving_root)
            print(f"Serving database written to: {serving_run / 'mobility_control_tower.duckdb'}")
            print(f"Manifest written to: {serving_run / 'serving_manifest.json'}")
        elif args.command == "query-serving-db":
            frame = query_serving_database(args.db, args.query_name, args.limit)
            print(dataframe_to_text_table(frame))
        elif args.command == "generate-serving-report":
            report_path = generate_serving_report(args.serving_run, args.reports_dir)
            print(f"Serving report written to: {report_path}")
        elif args.command == "serve-api":
            app = create_app(args.db)
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.command == "generate-api-report":
            report_path = generate_api_report(args.db, args.reports_dir)
            print(f"API report written to: {report_path}")
        elif args.command == "serve-dashboard":
            env = dict(os.environ)
            env["MCT_API_URL"] = args.api_url
            dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
            subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)], check=True, env=env)
        else:
            report_path = generate_final_report(args.serving_run, args.reports_dir)
            print(f"Final project report written to: {report_path}")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
