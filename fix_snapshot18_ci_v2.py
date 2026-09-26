from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess

ROOT = Path(r"D:\wsl\projects\Mobility_Control_Tower")
PUB = ROOT / "Mobility_Control_Tower_Publish"
REL = Path("src/mobility_control_tower/cli.py")
PUB_CLI = PUB / REL
SNAP18_CLI = ROOT / "progress" / "18" / REL

EXPECTED_TITLE = "Persist immutable realtime history"


def run(*args: str, cwd: Path = PUB, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and cp.returncode != 0:
        raise SystemExit(
            f"ERROR running {' '.join(args)}\n{cp.stdout}\n{cp.stderr}".strip()
        )
    return cp


def remove_snapshot19_kpi_cli(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"ERROR: file not found: {path}")

    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        "from mobility_control_tower.metrics.historical_kpis import build_historical_kpis\n",
        "",
        1,
    )

    parser_block = '''    history = commands.add_parser("build-history-kpis")
    history.add_argument("--history-run", type=Path, required=True)
    history.add_argument("--output-root", type=Path, default=Path("data/history_gold"))
'''
    text = text.replace(parser_block, "", 1)

    command_block = '''        elif args.command == "build-history-kpis":
            result = build_historical_kpis(args.history_run, args.output_root)
'''
    text = text.replace(command_block, "", 1)

    if "historical_kpis" in text or "build-history-kpis" in text:
        import re

        text = re.sub(
            r"\nfrom mobility_control_tower\.metrics\.historical_kpis import build_historical_kpis\s*\n",
            "\n",
            text,
            count=1,
        )
        text = re.sub(
            r'\n\s*history = commands\.add_parser\("build-history-kpis"\)\s*\n'
            r'\s*history\.add_argument\("--history-run", type=Path, required=True\)\s*\n'
            r'\s*history\.add_argument\("--output-root", type=Path, default=Path\("data/history_gold"\)\)\s*\n',
            "\n",
            text,
            count=1,
        )
        text = re.sub(
            r'\n\s*elif args\.command == "build-history-kpis":\s*\n'
            r'\s*result = build_historical_kpis\(args\.history_run, args\.output_root\)\s*\n',
            "\n",
            text,
            count=1,
        )

    if "historical_kpis" in text or "build-history-kpis" in text:
        raise SystemExit(
            f"ERROR: premature Snapshot 19 historical KPI CLI references remain in {path}."
        )

    if text == original:
        raise SystemExit(
            f"ERROR: no Snapshot 19 historical KPI CLI references were found in {path}."
        )

    path.write_text(text, encoding="utf-8", newline="\n")
    py_compile.compile(str(path), doraise=True)


if not PUB.is_dir():
    raise SystemExit(f"ERROR: publishing clone not found: {PUB}")

branch = run("git", "branch", "--show-current").stdout.strip()
if branch != "main":
    raise SystemExit(f"ERROR: publishing clone is on {branch!r}; expected 'main'.")

if run("git", "status", "--porcelain").stdout.strip():
    raise SystemExit("ERROR: publishing clone is not clean. Stop and inspect it first.")

run("git", "fetch", "origin", "main")

local_head = run("git", "rev-parse", "HEAD").stdout.strip()
remote_head = run("git", "rev-parse", "origin/main").stdout.strip()
if local_head != remote_head:
    raise SystemExit(
        "ERROR: local main does not match origin/main. Sync/inspect before retrying."
    )

title = run("git", "log", "-1", "--format=%s").stdout.strip()
if title != EXPECTED_TITLE:
    raise SystemExit(
        f"ERROR: latest commit is {title!r}, not {EXPECTED_TITLE!r}. "
        "This fixer only applies while Snapshot 18 is latest."
    )

remove_snapshot19_kpi_cli(SNAP18_CLI)
remove_snapshot19_kpi_cli(PUB_CLI)

run("git", "diff", "--check")
run("git", "add", str(REL).replace("\\", "/"))
run("git", "commit", "--amend", "--no-edit")
run("git", "push", "--force-with-lease", "origin", "main")

new_head = run("git", "rev-parse", "--short", "HEAD").stdout.strip()

print()
print("FIXED.")
print(f"Snapshot 18 amended and pushed: {new_head}  {EXPECTED_TITLE}")
print("Removed the Snapshot 19 historical KPI CLI import/command from Snapshot 18.")
print("Historical collection remains in Snapshot 18.")
print("GitHub CI will rerun automatically. Wait for green before publishing #19.")
