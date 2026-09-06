"""Generate a small report for the static analytical API."""

from pathlib import Path

from mobility_control_tower.api.db import query_view, view_exists


def generate_api_report(db_path: Path, reports_dir: Path = Path("data/reports")) -> Path:
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {db_path}")
    sections = ["# Mobility Control Tower API", "", f"Database: `{db_path}`", ""]
    for view in ("v_network_overview", "v_top_routes_static", "v_route_hourly_headway", "v_route_type_daily_summary"):
        rows = query_view(db_path, view, 3) if view_exists(db_path, view) else []
        sections.extend([f"## {view}", "", f"Rows sampled: {len(rows)}", ""])
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / "api_report.md"
    output.write_text("\n".join(sections), encoding="utf-8")
    return output
