"""Capture deterministic runtime screenshots from the running demo stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import Page, sync_playwright

from mobility_control_tower.security import create_access_token


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    return struct.unpack(">II", header[16:24])


def _capture(page: Page, path: Path, *, page_name: str, manifest: list[dict[str, Any]], fixture_version: str, serving_run_id: str) -> None:
    page.wait_for_load_state("networkidle", timeout=45_000)
    body = page.locator("body").inner_text(timeout=30_000)
    forbidden = ["/app/", "/mnt/", "Traceback", "Unhandled exception"]
    if any(token in body for token in forbidden):
        raise AssertionError(f"{page_name} contains path leakage or exception text")
    page.screenshot(path=str(path), full_page=True)
    if path.stat().st_size < 10_000:
        raise AssertionError(f"{path} is too small to be a real screenshot")
    width, height = _png_dimensions(path)
    manifest.append(
        {
            "filename": path.name,
            "page": page_name,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "fixture_version": fixture_version,
            "serving_run_id": serving_run_id,
            "viewport": {"width": 1440, "height": 1000},
            "dimensions": {"width": width, "height": height},
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    )


def _select_dashboard(page: Page, label: str) -> None:
    page.get_by_label("Page").click()
    page.get_by_text(label, exact=True).click()
    page.wait_for_load_state("networkidle", timeout=45_000)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=f"http://127.0.0.1:{os.getenv('API_PORT', '8000')}")
    parser.add_argument("--dashboard-url", default=f"http://127.0.0.1:{os.getenv('DASHBOARD_PORT', '8501')}")
    parser.add_argument("--grafana-url", default=f"http://127.0.0.1:{os.getenv('GRAFANA_PORT', '3000')}")
    parser.add_argument("--airflow-url", default=f"http://127.0.0.1:{os.getenv('AIRFLOW_PORT', '8080')}")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/screenshots"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    health = requests.get(f"{args.api_url}/health/ready", timeout=15).json()
    serving_run_id = str(health.get("validation", {}).get("run_id") or health.get("validation", {}).get("serving_run_id") or "unknown")
    fixture_version = "release-proof-v1"
    token = create_access_token("screenshot-operator", {"operations:read", "incidents:write"}, expires_in_seconds=900)
    incidents = requests.get(f"{args.api_url}/v1/incidents?limit=20", headers={"Authorization": f"Bearer {token}"}, timeout=15).json().get("data", [])
    incident_id = incidents[0]["incident_id"] if incidents else ""
    manifest: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, timezone_id="UTC", locale="en-US")
        page = context.new_page()
        page.goto(args.dashboard_url, wait_until="networkidle", timeout=60_000)
        page.get_by_text("Mobility Control Tower", exact=False).first.wait_for(timeout=60_000)
        _capture(
            page,
            args.output_dir / "control-tower.png",
            page_name="Control Tower",
            manifest=manifest,
            fixture_version=fixture_version,
            serving_run_id=serving_run_id,
        )

        _select_dashboard(page, "Incident Queue")
        _capture(
            page,
            args.output_dir / "incident-queue.png",
            page_name="Incident Queue",
            manifest=manifest,
            fixture_version=fixture_version,
            serving_run_id=serving_run_id,
        )
        if incident_id:
            page.get_by_label("Operator bearer token").fill(token)
            page.get_by_label("Incident ID").fill(incident_id)
            page.wait_for_timeout(1000)
            _capture(
                page,
                args.output_dir / "incident-detail.png",
                page_name="Incident Detail",
                manifest=manifest,
                fixture_version=fixture_version,
                serving_run_id=serving_run_id,
            )

        _select_dashboard(page, "Route Reliability")
        _capture(
            page,
            args.output_dir / "route-reliability.png",
            page_name="Route Reliability",
            manifest=manifest,
            fixture_version=fixture_version,
            serving_run_id=serving_run_id,
        )
        _select_dashboard(page, "Data Trust")
        _capture(
            page, args.output_dir / "data-trust.png", page_name="Data Trust", manifest=manifest, fixture_version=fixture_version, serving_run_id=serving_run_id
        )

        page.goto(f"{args.grafana_url}/d/mct-operations/mobility-control-tower-operations", wait_until="networkidle", timeout=60_000)
        page.get_by_text("Mobility Control Tower Operations", exact=False).first.wait_for(timeout=60_000)
        _capture(
            page,
            args.output_dir / "grafana-overview.png",
            page_name="Grafana Overview",
            manifest=manifest,
            fixture_version=fixture_version,
            serving_run_id=serving_run_id,
        )

        page.goto(f"{args.api_url}/docs", wait_until="networkidle", timeout=60_000)
        page.get_by_text("OpenAPI", exact=False).first.wait_for(timeout=60_000)
        _capture(
            page,
            args.output_dir / "api-openapi.png",
            page_name="API OpenAPI",
            manifest=manifest,
            fixture_version=fixture_version,
            serving_run_id=serving_run_id,
        )

        page.goto(f"{args.airflow_url}/login/", wait_until="networkidle", timeout=60_000)
        if page.get_by_label("Username").count():
            page.get_by_label("Username").fill(os.getenv("AIRFLOW_ADMIN_USERNAME", "admin"))
            page.get_by_label("Password").fill(os.getenv("AIRFLOW_ADMIN_PASSWORD", "admin"))
            page.get_by_role("button", name="Sign In").click()
            page.wait_for_load_state("networkidle", timeout=60_000)
        page.goto(f"{args.airflow_url}/dags", wait_until="networkidle", timeout=60_000)
        page.get_by_text("DAGs", exact=False).first.wait_for(timeout=60_000)
        _capture(
            page,
            args.output_dir / "airflow-dags.png",
            page_name="Airflow DAGs",
            manifest=manifest,
            fixture_version=fixture_version,
            serving_run_id=serving_run_id,
        )
        browser.close()

    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"screenshots": len(manifest), "manifest": str(args.output_dir / "manifest.json")}, sort_keys=True))
    if len(manifest) < 8:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
