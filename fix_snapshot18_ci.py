from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess
import sys

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


def patch_cli(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"ERROR: file not found: {path}")

    text = path.read_text(encoding="utf-8")
    original = text

    replacements = [
        (
            '    dbt_run.add_argument("--silver-run", type=Path)\n'
            '    dbt_run.add_argument("--history-run", type=Path)\n',
            '    dbt_run.add_argument("--silver-run", type=Path, required=True)\n',
        ),
        (
            '    quality.add_argument("--suite", choices=["silver", "gold", "history", "all"], default="all")\n'
            '    quality.add_argument("--history-run", type=Path)\n',
            '    quality.add_argument("--suite", choices=["silver", "gold", "all"], default="all")\n',
        ),
        (
            '    serving.add_argument("--rt-gold-run", type=Path)\n'
            '    serving.add_argument("--history-run", type=Path)\n'
            '    serving.add_argument("--history-gold-run", type=Path)\n'
            '    serving.add_argument("--quality-status", default="unknown")\n',
            '    serving.add_argument("--rt-gold-run", type=Path)\n'
            '    serving.add_argument("--quality-status", default="unknown")\n',
        ),
        (
            '                silver_run=args.silver_run,\n'
            '                history_run=args.history_run,\n'
            '                project_dir=args.project_dir,\n',
            '                silver_run=args.silver_run,\n'
            '                project_dir=args.project_dir,\n',
        ),
        (
            '                silver_run=args.silver_run,\n'
            '                gold_run=args.gold_run,\n'
            '                history_run=args.history_run,\n'
            '                ge_root=args.ge_root,\n',
            '                silver_run=args.silver_run,\n'
            '                gold_run=args.gold_run,\n'
            '                ge_root=args.ge_root,\n',
        ),
        (
            '                rt_gold_run=args.rt_gold_run,\n'
            '                history_run=args.history_run,\n'
            '                history_gold_run=args.history_gold_run,\n'
            '            )\n',
            '                rt_gold_run=args.rt_gold_run,\n'
            '            )\n',
        ),
    ]

    for old, new in replacements:
        if old not in text:
            raise SystemExit(
                f"ERROR: expected Snapshot 18 CLI pattern not found in {path}.\n"
                "Nothing was committed or pushed."
            )
        text = text.replace(old, new, 1)

    if text == original:
        raise SystemExit(f"ERROR: no changes made to {path}")

    path.write_text(text, encoding="utf-8", newline="\n")
    py_compile.compile(str(path), doraise=True)


# Safety checks.
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
        "ERROR: local main does not match origin/main. "
        "Run mct-publish/status first and inspect before retrying."
    )

title = run("git", "log", "-1", "--format=%s").stdout.strip()
if title != EXPECTED_TITLE:
    raise SystemExit(
        f"ERROR: latest commit is {title!r}, not {EXPECTED_TITLE!r}. "
        "This fixer only applies while Snapshot 18 is the latest commit."
    )

# Patch both the private source snapshot and the public working copy.
patch_cli(SNAP18_CLI)
patch_cli(PUB_CLI)

run("git", "diff", "--check")
run("git", "add", str(REL).replace("\\", "/"))
run("git", "commit", "--amend", "--no-edit")
run("git", "push", "--force-with-lease", "origin", "main")

new_head = run("git", "rev-parse", "--short", "HEAD").stdout.strip()

print()
print("FIXED.")
print(f"Snapshot 18 amended and pushed: {new_head}  {EXPECTED_TITLE}")
print("The premature Snapshot 19 CLI arguments were removed from Snapshot 18.")
print("GitHub CI should rerun automatically. Do not publish #19 until #18 is green.")
