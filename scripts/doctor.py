"""Print local environment diagnostics without mutating state."""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path


def _version(command: list[str]) -> str:
    binary = shutil.which(command[0])
    if not binary:
        return "not found"
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
    except Exception as exc:
        return f"error: {exc}"
    return (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "available"


def _port_status(port: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return "in use" if sock.connect_ex(("127.0.0.1", port)) == 0 else "free"


def main() -> None:
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Platform: {platform.platform()}")
    print(f"WSL: {'yes' if 'microsoft' in platform.uname().release.lower() else 'no'}")
    print(f"dbt: {_version(['dbt', '--version'])}")
    print(f"Docker: {_version(['docker', 'version', '--format', '{{.Server.Version}}'])}")
    print(f"Docker Compose: {_version(['docker', 'compose', 'version'])}")
    import_check = [sys.executable, "-c", "import mobility_control_tower; print('ok')"]
    print(f"Package import: {_version(import_check)}")
    for port in (8000, 8501, 8080, 9090, 3000, 9108, 5432):
        print(f"Port {port}: {_port_status(port)}")
    for path in (Path("data"), Path("data/serving"), Path("data/realtime_history"), Path("data/watermarks")):
        try:
            path.mkdir(parents=True, exist_ok=True)
            writable = os.access(path, os.W_OK)
        except OSError:
            writable = False
        print(f"Write access {path}: {'yes' if writable else 'no'}")
    pointer = Path("data/serving/tisseo/current.json")
    print(f"Serving pointer: {pointer if pointer.is_file() else 'not published'}")
    print("Docker is required for Compose smoke tests. Non-Docker checks can still run locally; GitHub Actions runs the mandatory container smoke gate.")


if __name__ == "__main__":
    main()
