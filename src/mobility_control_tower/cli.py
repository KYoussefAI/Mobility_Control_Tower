"""Command-line interface for the Mobility Control Tower GTFS workflow."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import warnings
from datetime import datetime
from pathlib import Path

import uvicorn

from mobility_control_tower.analytics_engineering import generate_dbt_docs, run_dbt, run_ge_validation, run_quality_validation, test_dbt
from mobility_control_tower.api.app import create_app
from mobility_control_tower.api.report import generate_api_report
from mobility_control_tower.benchmarking import run_benchmarks
from mobility_control_tower.config import load_source
from mobility_control_tower.core.exceptions import cli_failure_message
from mobility_control_tower.core.logging import configure_logging
from mobility_control_tower.incidents import IncidentEvaluationEngine, IncidentStore, evaluation_result_to_dict, migrate_incident_store
from mobility_control_tower.ingestion.gtfs_raw import download_and_preserve_gtfs, preserve_gtfs_zip
from mobility_control_tower.metrics.gtfs_kpis import build_gold
from mobility_control_tower.metrics.historical_kpis import build_historical_kpis
from mobility_control_tower.observability_exporter import create_metrics_exporter_app
from mobility_control_tower.profiling.gtfs_profile import profile_raw_run
from mobility_control_tower.quality.gtfs_quality import validate_silver_run
from mobility_control_tower.realtime.gtfs_rt_charts import generate_rt_charts
from mobility_control_tower.realtime.gtfs_rt_compatibility import check_realtime_compatibility
from mobility_control_tower.realtime.gtfs_rt_kpis import build_rt_gold
from mobility_control_tower.realtime.gtfs_rt_parser import parse_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_raw import FEED_TYPES, fetch_realtime_snapshot
from mobility_control_tower.realtime.gtfs_rt_report import generate_realtime_report
from mobility_control_tower.realtime.gtfs_rt_snapshot_report import generate_rt_snapshot_report
from mobility_control_tower.realtime.historical_storage import run_historical_collection
from mobility_control_tower.reporting.charts import generate_static_charts
from mobility_control_tower.reporting.demo_report import generate_demo_report, generate_static_mvp_report
from mobility_control_tower.reporting.final_report import generate_final_report
from mobility_control_tower.serving.duckdb_loader import build_serving_database, dataframe_to_text_table, query_serving_database
from mobility_control_tower.serving.serving_report import generate_serving_report
from mobility_control_tower.transformations.gtfs_bronze import build_bronze
from mobility_control_tower.transformations.gtfs_silver import build_silver

logger = logging.getLogger(__name__)


def _info(message: str) -> None:
    logger.info(message)


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

    gold = commands.add_parser("build-gold", help="LEGACY diagnostic: build Python static-schedule KPI tables from silver GTFS")
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

    collect_rt = commands.add_parser("collect-gtfs-rt", help="Continuously poll and preserve GTFS-Realtime history")
    collect_rt.add_argument("--source", required=True)
    collect_rt.add_argument("--feed-type", choices=sorted(FEED_TYPES), required=True)
    collect_rt.add_argument("--interval", type=int, default=30)
    collect_rt.add_argument("--url")
    collect_rt.add_argument("--config", type=Path, default=Path("config/sources.yml"))
    collect_rt.add_argument("--raw-history-root", type=Path, default=Path("data/raw_realtime/historical"))
    collect_rt.add_argument("--history-root", type=Path, default=Path("data/realtime_history"))
    collect_rt.add_argument("--timeout-seconds", type=int, default=30)
    collect_rt.add_argument("--max-polls", type=int)

    history_gold = commands.add_parser("build-history-kpis", help="Build historical GTFS-Realtime KPI Parquet tables")
    history_gold.add_argument("--history-run", type=Path, required=True)
    history_gold.add_argument("--history-gold-root", type=Path, default=Path("data/history_gold"))

    dbt_run = commands.add_parser("run-dbt", help="Run dbt models after Silver and/or historical Parquet")
    dbt_run.add_argument("--silver-run", type=Path)
    dbt_run.add_argument("--history-run", type=Path)
    dbt_run.add_argument("--project-dir", type=Path, default=Path("dbt"))
    dbt_run.add_argument("--profiles-dir", type=Path, default=Path("dbt"))
    dbt_run.add_argument("--output-root", type=Path, default=Path("data/dbt_gold"))
    dbt_run.add_argument("--no-installed-dbt", action="store_true")

    dbt_test = commands.add_parser("test-dbt", help="Run dbt tests or validate dbt test declarations")
    dbt_test.add_argument("--project-dir", type=Path, default=Path("dbt"))
    dbt_test.add_argument("--profiles-dir", type=Path, default=Path("dbt"))
    dbt_test.add_argument("--no-installed-dbt", action="store_true")

    dbt_docs = commands.add_parser("generate-dbt-docs", help="Generate dbt documentation artifacts")
    dbt_docs.add_argument("--project-dir", type=Path, default=Path("dbt"))
    dbt_docs.add_argument("--profiles-dir", type=Path, default=Path("dbt"))
    dbt_docs.add_argument("--no-installed-dbt", action="store_true")

    quality_validation = commands.add_parser("run-quality-validation", help="Run MCT quality-contract validation over Silver, dbt Gold, and history")
    quality_validation.add_argument("--suite", choices=["all", "silver", "gold", "history"], default="all")
    quality_validation.add_argument("--silver-run", type=Path)
    quality_validation.add_argument("--gold-run", type=Path)
    quality_validation.add_argument("--history-run", type=Path)
    quality_validation.add_argument("--quality-contracts-root", "--ge-root", dest="ge_root", type=Path, default=Path("quality_contracts"))
    quality_validation.add_argument("--quality-root", type=Path, default=Path("data/quality"))

    ge_validation = commands.add_parser("run-ge-validation", help="LEGACY alias for run-quality-validation")
    ge_validation.add_argument("--suite", choices=["all", "silver", "gold", "history"], default="all")
    ge_validation.add_argument("--silver-run", type=Path)
    ge_validation.add_argument("--gold-run", type=Path)
    ge_validation.add_argument("--history-run", type=Path)
    ge_validation.add_argument("--quality-contracts-root", "--ge-root", dest="ge_root", type=Path, default=Path("quality_contracts"))
    ge_validation.add_argument("--quality-root", type=Path, default=Path("data/quality"))

    benchmark = commands.add_parser("run-benchmarks", help="Run local performance benchmarks over existing artifacts")
    benchmark.add_argument("--raw-run", type=Path)
    benchmark.add_argument("--bronze-run", type=Path)
    benchmark.add_argument("--silver-run", type=Path)
    benchmark.add_argument("--gold-run", type=Path)
    benchmark.add_argument("--history-run", type=Path)
    benchmark.add_argument("--db", type=Path)
    benchmark.add_argument("--output-dir", type=Path, default=Path("data/benchmarks"))

    serving = commands.add_parser("build-serving-db", help="Build a local DuckDB serving database from gold outputs")
    serving.add_argument("--gold-run", type=Path, required=True)
    serving.add_argument("--rt-gold-run", type=Path)
    serving.add_argument("--serving-root", type=Path, default=Path("data/serving"))
    serving.add_argument("--history-run", type=Path)
    serving.add_argument("--history-gold-run", type=Path)
    serving.add_argument("--quality-status", default="unknown")
    serving.add_argument("--serving-run-id")

    serving_query = commands.add_parser("query-serving-db", help="Run a predefined query against the serving DuckDB database")
    serving_query.add_argument("--db", type=Path, required=True)
    serving_query.add_argument("--query-name", required=True)
    serving_query.add_argument("--limit", type=int, default=10)

    serving_report = commands.add_parser("generate-serving-report", help="Generate a Markdown report for a serving database run")
    serving_report.add_argument("--serving-run", type=Path, required=True)
    serving_report.add_argument("--reports-dir", type=Path, default=Path("data/reports"))

    api = commands.add_parser("serve-api", help="Start the local read-only FastAPI server")
    api.add_argument("--db", type=Path)
    api.add_argument("--source", default="tisseo")
    api.add_argument("--serving-root", type=Path, default=Path("data/serving"))
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)

    metrics_exporter = commands.add_parser("serve-metrics", help="Start the durable MCT Prometheus metrics exporter")
    metrics_exporter.add_argument("--source", default="tisseo")
    metrics_exporter.add_argument("--feed-type", default="trip_updates")
    metrics_exporter.add_argument("--serving-root", type=Path, default=Path("data/serving"))
    metrics_exporter.add_argument("--history-root", type=Path, default=Path("data/realtime_history"))
    metrics_exporter.add_argument("--watermark-root", type=Path, default=Path("data/watermarks"))
    metrics_exporter.add_argument("--quality-root", type=Path, default=Path("data/quality"))
    metrics_exporter.add_argument("--host", default="127.0.0.1")
    metrics_exporter.add_argument("--port", type=int, default=9108)

    migrate_incidents = commands.add_parser("migrate-incident-store", help="Apply incident-store migrations")
    migrate_incidents.add_argument("--incident-root", type=Path, default=Path("data/incidents"))
    migrate_incidents.add_argument("--json", action="store_true")

    evaluate_incidents = commands.add_parser("evaluate-incidents", help="Evaluate incident rules from authoritative serving outputs")
    evaluate_incidents.add_argument("--source")
    evaluate_incidents.add_argument("--evaluation-time")
    evaluate_incidents.add_argument("--correlation-id")
    evaluate_incidents.add_argument("--dry-run", action="store_true")
    evaluate_incidents.add_argument("--json", action="store_true")
    evaluate_incidents.add_argument("--incident-root", type=Path, default=Path("data/incidents"))
    evaluate_incidents.add_argument("--serving-root", type=Path, default=Path("data/serving"))
    evaluate_incidents.add_argument("--history-root", type=Path, default=Path("data/realtime_history"))
    evaluate_incidents.add_argument("--quality-root", type=Path, default=Path("data/quality"))

    list_incidents = commands.add_parser("list-incidents", help="List persisted incidents")
    list_incidents.add_argument("--source")
    list_incidents.add_argument("--status")
    list_incidents.add_argument("--rule")
    list_incidents.add_argument("--severity")
    list_incidents.add_argument("--limit", type=int, default=100)
    list_incidents.add_argument("--json", action="store_true")
    list_incidents.add_argument("--incident-root", type=Path, default=Path("data/incidents"))

    show_incident = commands.add_parser("show-incident", help="Show one incident and its event history")
    show_incident.add_argument("--incident-id", required=True)
    show_incident.add_argument("--json", action="store_true")
    show_incident.add_argument("--incident-root", type=Path, default=Path("data/incidents"))

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
    configure_logging()
    args = build_parser().parse_args()
    try:
        if args.command == "ingest-gtfs":
            source = load_source(args.source, args.config)
            if args.download:
                run_dir = download_and_preserve_gtfs(args.source, source, args.raw_root)
            else:
                run_dir = preserve_gtfs_zip(args.local_zip, args.source, source, args.raw_root)
            _info(f"Raw GTFS preserved in: {run_dir}")
            _info(f"Metadata written to: {run_dir / 'metadata.json'}")
        elif args.command == "profile-gtfs":
            json_path, markdown_path = profile_raw_run(args.raw_run, args.reports_dir)
            _info(f"JSON report written to: {json_path}")
            _info(f"Markdown report written to: {markdown_path}")
        elif args.command == "build-bronze":
            run_dir = build_bronze(args.raw_run, args.bronze_root)
            _info(f"Bronze GTFS written to: {run_dir}")
            _info(f"Manifest written to: {run_dir / 'bronze_manifest.json'}")
        elif args.command == "build-silver":
            run_dir = build_silver(args.bronze_run, args.silver_root)
            _info(f"Silver GTFS written to: {run_dir}")
            _info(f"Manifest written to: {run_dir / 'silver_manifest.json'}")
        elif args.command == "validate-gtfs":
            json_path, markdown_path = validate_silver_run(args.silver_run, args.reports_dir)
            _info(f"JSON quality report written to: {json_path}")
            _info(f"Markdown quality report written to: {markdown_path}")
        elif args.command == "build-gold":
            warnings.warn(
                "build-gold is a legacy diagnostic command. Production Gold marts are built by run-dbt.",
                DeprecationWarning,
                stacklevel=2,
            )
            run_dir = build_gold(args.silver_run, args.gold_root)
            _info(f"Gold KPI tables written to: {run_dir}")
            _info(f"Manifest written to: {run_dir / 'gold_manifest.json'}")
        elif args.command == "generate-demo-report":
            report_path = generate_demo_report(args.gold_run, args.reports_dir)
            _info(f"Demo report written to: {report_path}")
        elif args.command == "generate-static-charts":
            figures_dir = generate_static_charts(args.gold_run, args.reports_dir)
            _info(f"Static charts written to: {figures_dir}")
        elif args.command == "generate-static-mvp-report":
            report_path = generate_static_mvp_report(args.gold_run, args.reports_dir)
            _info(f"Static MVP evidence report written to: {report_path}")
        elif args.command == "fetch-gtfs-rt":
            source = load_source(args.source, args.config)
            run_dir = fetch_realtime_snapshot(args.source, source, args.feed_type, args.url, args.raw_rt_root)
            _info(f"Raw GTFS-Realtime snapshot preserved in: {run_dir}")
            _info(f"Metadata written to: {run_dir / 'metadata.json'}")
        elif args.command == "parse-gtfs-rt":
            run_dir = parse_realtime_snapshot(args.raw_rt_run, args.rt_root)
            _info(f"Parsed GTFS-Realtime tables written to: {run_dir}")
            _info(f"Manifest written to: {run_dir / 'realtime_manifest.json'}")
        elif args.command == "report-gtfs-rt":
            report_path = generate_realtime_report(args.rt_run, args.reports_dir)
            _info(f"GTFS-Realtime report written to: {report_path}")
        elif args.command == "check-rt-compatibility":
            json_path, markdown_path = check_realtime_compatibility(args.silver_run, args.rt_run, args.reports_dir)
            _info(f"JSON compatibility report written to: {json_path}")
            _info(f"Markdown compatibility report written to: {markdown_path}")
        elif args.command == "build-rt-gold":
            run_dir = build_rt_gold(args.silver_run, args.rt_run, args.rt_gold_root)
            _info(f"Real-time gold snapshot tables written to: {run_dir}")
            _info(f"Manifest written to: {run_dir / 'rt_gold_manifest.json'}")
        elif args.command == "generate-rt-charts":
            figures_dir = generate_rt_charts(args.rt_gold_run, args.reports_dir)
            _info(f"Real-time snapshot charts written to: {figures_dir}")
        elif args.command == "generate-rt-snapshot-report":
            report_path = generate_rt_snapshot_report(args.rt_gold_run, args.reports_dir)
            _info(f"Real-time snapshot report written to: {report_path}")
        elif args.command == "collect-gtfs-rt":
            source = load_source(args.source, args.config)
            run_historical_collection(
                args.source,
                source,
                args.feed_type,
                interval_seconds=args.interval,
                url=args.url,
                raw_history_root=args.raw_history_root,
                parsed_history_root=args.history_root,
                timeout_seconds=args.timeout_seconds,
                max_polls=args.max_polls,
            )
        elif args.command == "build-history-kpis":
            run_dir = build_historical_kpis(args.history_run, args.history_gold_root)
            _info(f"Historical KPI Parquet tables written to: {run_dir}")
            _info(f"Manifest written to: {run_dir / 'history_gold_manifest.json'}")
        elif args.command == "run-dbt":
            run_dir = run_dbt(
                silver_run=args.silver_run,
                history_run=args.history_run,
                project_dir=args.project_dir,
                profiles_dir=args.profiles_dir,
                output_root=args.output_root,
                use_installed=not args.no_installed_dbt,
            )
            _info(f"dbt gold output written to: {run_dir}")
            _info(f"dbt run manifest written to: {run_dir / 'dbt_run_manifest.json'}")
        elif args.command == "test-dbt":
            result_path = test_dbt(args.project_dir, args.profiles_dir, use_installed=not args.no_installed_dbt)
            _info(f"dbt test results written to: {result_path}")
        elif args.command == "generate-dbt-docs":
            docs_path = generate_dbt_docs(args.project_dir, args.profiles_dir, use_installed=not args.no_installed_dbt)
            _info(f"dbt docs generated at: {docs_path}")
        elif args.command in {"run-quality-validation", "run-ge-validation"}:
            if args.command == "run-ge-validation":
                warnings.warn(
                    "run-ge-validation is a legacy alias. Use run-quality-validation for MCT quality contracts.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            runner = run_ge_validation if args.command == "run-ge-validation" else run_quality_validation
            result_path = runner(
                suite_name=args.suite,
                silver_run=args.silver_run,
                gold_run=args.gold_run,
                history_run=args.history_run,
                ge_root=args.ge_root,
                quality_root=args.quality_root,
            )
            _info(f"MCT quality validation written to: {result_path}")
            _info(f"Latest validation summary written to: {args.quality_root / 'latest_validation_summary.json'}")
        elif args.command == "run-benchmarks":
            report_path = run_benchmarks(
                raw_run=args.raw_run,
                bronze_run=args.bronze_run,
                silver_run=args.silver_run,
                gold_run=args.gold_run,
                history_run=args.history_run,
                db_path=args.db,
                output_dir=args.output_dir,
            )
            _info(f"Benchmark report written to: {report_path}")
        elif args.command == "build-serving-db":
            serving_run = build_serving_database(
                args.gold_run,
                args.rt_gold_run,
                args.serving_root,
                history_run=args.history_run,
                history_gold_run=args.history_gold_run,
                quality_status=args.quality_status,
                serving_run_id=args.serving_run_id,
            )
            _info(f"Serving database written to: {serving_run / 'mobility_control_tower.duckdb'}")
            _info(f"Manifest written to: {serving_run / 'serving_manifest.json'}")
        elif args.command == "query-serving-db":
            frame = query_serving_database(args.db, args.query_name, args.limit)
            _info(dataframe_to_text_table(frame))
        elif args.command == "generate-serving-report":
            report_path = generate_serving_report(args.serving_run, args.reports_dir)
            _info(f"Serving report written to: {report_path}")
        elif args.command == "serve-api":
            app = create_app(args.db, source=args.source, serving_root=args.serving_root)
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.command == "serve-metrics":
            app = create_metrics_exporter_app(
                source=args.source,
                feed_type=args.feed_type,
                serving_root=args.serving_root,
                history_root=args.history_root,
                watermark_root=args.watermark_root,
                quality_root=args.quality_root,
            )
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.command == "migrate-incident-store":
            migration_result = migrate_incident_store(args.incident_root)
            if getattr(args, "json", False):
                print(json.dumps(migration_result, indent=2, sort_keys=True))
            else:
                _info(
                    "Incident store migrated: "
                    f"backend={migration_result['backend']} target={migration_result['target']} "
                    f"schema={migration_result['ending_schema_version']} status={migration_result['status']}"
                )
        elif args.command == "evaluate-incidents":
            evaluation_time = datetime.fromisoformat(args.evaluation_time.replace("Z", "+00:00")) if args.evaluation_time else None
            engine = IncidentEvaluationEngine(
                repository=IncidentStore(args.incident_root).repository,
                serving_root=args.serving_root,
                history_root=args.history_root,
                quality_root=args.quality_root,
            )
            result = engine.evaluate(source=args.source, evaluation_time=evaluation_time, correlation_id=args.correlation_id, dry_run=args.dry_run)
            payload = evaluation_result_to_dict(result)
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                _info(
                    f"Incident evaluation {result.status}: {result.candidate_count} candidates, "
                    f"{result.opened_count} opened, {result.updated_count} updated, {result.resolved_count} resolved"
                )
        elif args.command == "list-incidents":
            store = IncidentStore(args.incident_root)
            rows = store.list_incidents(status=args.status, source=args.source, rule_id=args.rule, severity=args.severity, limit=args.limit)
            payload = {"data": rows, "count": len(rows), "source": args.source or "all"}
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True, default=str))
            else:
                for row in rows:
                    _info(f"{row['incident_id']} {row['status']} {row['severity']} {row['rule_id']} {row['source']} {row['title']}")
        elif args.command == "show-incident":
            store = IncidentStore(args.incident_root)
            incident_row = store.get_by_id(args.incident_id)
            if incident_row is None:
                raise ValueError(f"Incident not found: {args.incident_id}")
            payload = {"data": [incident_row], "events": store.list_events(args.incident_id), "count": 1}
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True, default=str))
            else:
                _info(json.dumps(payload, indent=2, sort_keys=True, default=str))
        elif args.command == "generate-api-report":
            report_path = generate_api_report(args.db, args.reports_dir)
            _info(f"API report written to: {report_path}")
        elif args.command == "serve-dashboard":
            env = dict(os.environ)
            env["MCT_API_URL"] = args.api_url
            dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
            subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)], check=True, env=env)
        else:
            report_path = generate_final_report(args.serving_run, args.reports_dir)
            _info(f"Final project report written to: {report_path}")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error(cli_failure_message(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
