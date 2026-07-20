"""Run local security guardrails that do not require external services."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"),
]
EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "data",
    "dbt_packages",
    "logs",
    "target",
    "htmlcov",
    "mobility_control_tower.egg-info",
    "quality_contracts/validation_results",
}


def main() -> int:
    findings: list[str] = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIR_NAMES]
        for filename in files:
            path = Path(root) / filename
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts) or not path.is_file():
                continue
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".duckdb", ".parquet", ".pb", ".zip"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append(str(path))
                    break
    if os.getenv("MCT_ENV", "local") == "production" and not os.getenv("MCT_AUTH_SECRET"):
        findings.append("MCT_AUTH_SECRET must be set in production")
    if findings:
        print("Security check failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print("Security check passed: no committed secret patterns found and production auth settings are guarded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
