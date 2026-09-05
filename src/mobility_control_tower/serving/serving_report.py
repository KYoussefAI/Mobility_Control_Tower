"""Generate a concise report for one serving artifact."""

import json
from pathlib import Path


def generate_serving_report(serving_run: Path, reports_dir: Path = Path("data/reports")) -> Path:
    manifest_path = serving_run / "serving_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Serving manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"serving_{serving_run.name}.md"
    output.write_text(
        "# DuckDB serving artifact\n\n"
        f"Database: `{manifest['database_path']}`\n\n"
        f"Tables loaded: {len(manifest.get('tables_loaded', {}))}\n\n"
        f"Views created: {len(manifest.get('views_created', []))}\n",
        encoding="utf-8",
    )
    return output
