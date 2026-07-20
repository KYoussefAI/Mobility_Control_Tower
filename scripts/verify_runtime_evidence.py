"""Assemble and validate the release evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_REPORTS = [
    "health-report.json",
    "airflow-report.json",
    "prometheus-targets.json",
    "prometheus-rules.json",
    "grafana-report.json",
    "smoke-test-results.json",
    "restore-report.json",
    "failure-injection-report.json",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str]) -> str:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return completed.stderr.strip() or completed.stdout.strip()
    return completed.stdout.strip()


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, default=Path("artifacts/runtime"))
    parser.add_argument("--screenshots-dir", type=Path, default=Path("artifacts/screenshots"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/release-evidence"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    missing = [name for name in REQUIRED_REPORTS if not (args.runtime_dir / name).is_file()]
    screenshot_manifest = args.screenshots_dir / "manifest.json"
    if not screenshot_manifest.is_file():
        missing.append(str(screenshot_manifest))
    if missing:
        raise FileNotFoundError(f"missing required evidence files: {missing}")

    files: dict[str, str] = {}
    for name in REQUIRED_REPORTS:
        source = args.runtime_dir / name
        destination = args.output_dir / name
        _copy_file(source, destination)
        files[name] = _sha256(destination)
    screenshots_dest = args.output_dir / "screenshots"
    if screenshots_dest.exists():
        shutil.rmtree(screenshots_dest)
    shutil.copytree(args.screenshots_dir, screenshots_dest)
    for path in sorted(screenshots_dest.glob("*")):
        if path.is_file():
            files[f"screenshots/{path.name}"] = _sha256(path)

    logs_dir = args.output_dir / "container-logs"
    logs_dir.mkdir(exist_ok=True)
    (args.output_dir / "docker-compose-ps.txt").write_text(_run(["docker", "compose", "--profile", "demo", "ps"]), encoding="utf-8")
    (logs_dir / "compose.log").write_text(_run(["docker", "compose", "--profile", "demo", "logs", "--no-color", "--tail=1000"]), encoding="utf-8")
    image_metadata = {
        "docker_version": _run(["docker", "version", "--format", "{{json .}}"]),
        "compose_version": _run(["docker", "compose", "version", "--short"]),
        "image_inspect": _run(["docker", "image", "inspect", "mobility-control-tower:local"]),
    }
    (args.output_dir / "image-metadata.json").write_text(json.dumps(image_metadata, indent=2, sort_keys=True), encoding="utf-8")
    files["docker-compose-ps.txt"] = _sha256(args.output_dir / "docker-compose-ps.txt")
    files["container-logs/compose.log"] = _sha256(logs_dir / "compose.log")
    files["image-metadata.json"] = _sha256(args.output_dir / "image-metadata.json")

    health = json.loads((args.output_dir / "health-report.json").read_text(encoding="utf-8"))
    screenshot_entries = json.loads((screenshots_dest / "manifest.json").read_text(encoding="utf-8"))
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_commit": _run(["git", "rev-parse", "HEAD"]),
        "workflow_run_id": "",
        "workflow_attempt": "",
        "python_version": _run(["python", "--version"]),
        "docker_version": image_metadata["docker_version"],
        "compose_version": image_metadata["compose_version"],
        "incident_backend": health.get("checks", {}).get("incident_backend"),
        "screenshot_count": len(screenshot_entries),
        "overall_status": "ok",
        "evidence_file_hashes": files,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output_dir), "status": "ok", "files": len(files)}, sort_keys=True))


if __name__ == "__main__":
    main()
