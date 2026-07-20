"""Browser and API smoke tests for the deterministic runtime stack."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import Page, sync_playwright

from mobility_control_tower.security import create_access_token

RAW_PATH_PATTERN = re.compile(r"(/app/|/mnt/|C:\\\\|Traceback|Unhandled exception)", re.IGNORECASE)


def _api_json(method: str, api_url: str, path: str, *, token: str | None = None, json_body: dict[str, Any] | None = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.request(method, f"{api_url}{path}", headers=headers, json=json_body, timeout=15)


def _assert_clean_page(page: Page) -> None:
    body = page.locator("body").inner_text(timeout=30_000)
    if RAW_PATH_PATTERN.search(body):
        raise AssertionError("page contains path leakage or unhandled exception text")


def _select_page(page: Page, label: str) -> None:
    page.get_by_label("Page").click()
    page.get_by_text(label, exact=True).click()
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.get_by_text(label, exact=False).first.wait_for(timeout=30_000)
    _assert_clean_page(page)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=f"http://127.0.0.1:{os.getenv('API_PORT', '8000')}")
    parser.add_argument("--dashboard-url", default=f"http://127.0.0.1:{os.getenv('DASHBOARD_PORT', '8501')}")
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/smoke-test-results.json"))
    parser.add_argument("--trace-dir", type=Path, default=Path("artifacts/runtime/browser-test-results"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.trace_dir.mkdir(parents=True, exist_ok=True)

    writer_token = create_access_token("release-proof-operator", {"incidents:write", "operations:read"}, expires_in_seconds=900)
    readonly_token = create_access_token("release-proof-reader", {"operations:read"}, expires_in_seconds=900)
    admin_token = create_access_token("release-proof-admin", {"admin"}, expires_in_seconds=900)
    incidents = _api_json("GET", args.api_url, "/v1/incidents?limit=100", token=readonly_token).json().get("data", [])
    if not incidents:
        raise AssertionError("deterministic incident fixture is empty")
    target = next((incident for incident in incidents if incident.get("status") == "OPEN"), incidents[0])
    incident_id = target["incident_id"]

    missing_token = _api_json("POST", args.api_url, f"/v1/incidents/{incident_id}/acknowledge", json_body={"reason": "no token"})
    readonly_mutation = _api_json(
        "POST",
        args.api_url,
        f"/v1/incidents/{incident_id}/acknowledge",
        token=readonly_token,
        json_body={"reason": "readonly token"},
    )
    acknowledge = _api_json(
        "POST",
        args.api_url,
        f"/v1/incidents/{incident_id}/acknowledge",
        token=writer_token,
        json_body={"reason": "Release proof acknowledgement."},
    )
    acknowledge_repeat = _api_json(
        "POST",
        args.api_url,
        f"/v1/incidents/{incident_id}/acknowledge",
        token=writer_token,
        json_body={"reason": "Release proof acknowledgement."},
    )
    events = _api_json("GET", args.api_url, f"/v1/incidents/{incident_id}/events", token=readonly_token).json().get("data", [])
    evaluation = _api_json("POST", args.api_url, "/v1/incidents/evaluate?dry_run=true", token=admin_token)
    openapi = _api_json("GET", args.api_url, "/openapi.json")
    if missing_token.status_code not in {401, 403}:
        raise AssertionError("protected mutation without token did not fail")
    if readonly_mutation.status_code not in {401, 403}:
        raise AssertionError("readonly token was allowed to mutate incidents")
    if acknowledge.status_code >= 300 or acknowledge_repeat.status_code >= 300:
        raise AssertionError("incidents-write token could not acknowledge incident")
    if not any(event.get("event_type") == "ACKNOWLEDGED" for event in events):
        raise AssertionError("acknowledgement audit event was not visible")
    if sum(1 for event in events if event.get("event_type") == "ACKNOWLEDGED") > 1:
        raise AssertionError("repeated acknowledgement created duplicate audit events")
    if evaluation.status_code >= 300:
        raise AssertionError("admin dry-run evaluation failed")
    if openapi.status_code >= 300 or "Incident" not in openapi.text:
        raise AssertionError("OpenAPI schema did not load expected incident contracts")

    browser_status = "not_run"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, timezone_id="UTC", locale="en-US")
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()
        try:
            page.goto(args.dashboard_url, wait_until="networkidle", timeout=60_000)
            page.get_by_text("Mobility Control Tower", exact=False).first.wait_for(timeout=60_000)
            page.get_by_text("Serving ready", exact=False).first.wait_for(timeout=30_000)
            _assert_clean_page(page)
            for label in ("Incident Queue", "Route Reliability", "Data Trust"):
                _select_page(page, label)
            browser_status = "ok"
        except Exception:
            context.tracing.stop(path=str(args.trace_dir / "browser-smoke-failure.zip"))
            raise
        else:
            context.tracing.stop(path=str(args.trace_dir / "browser-smoke.zip"))
        finally:
            browser.close()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "browser": browser_status,
        "incident_id": incident_id,
        "missing_token_status": missing_token.status_code,
        "readonly_mutation_status": readonly_mutation.status_code,
        "acknowledge_status": acknowledge.status_code,
        "acknowledge_repeat_status": acknowledge_repeat.status_code,
        "event_count": len(events),
        "openapi_status": openapi.status_code,
        "status": "ok",
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
