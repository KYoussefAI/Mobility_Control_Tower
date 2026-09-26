from pathlib import Path
import py_compile
import shutil
from datetime import datetime

root = Path(r"D:\wsl\projects\Mobility_Control_Tower")
target = root / "mct_publish.py"

if not target.is_file():
    raise SystemExit(f"ERROR: not found: {target}")

text = target.read_text(encoding="utf-8")
original = text

backup = target.with_name(
    f"mct_publish.py.before_direct_main_{datetime.now():%Y%m%d_%H%M%S}.bak"
)
shutil.copy2(target, backup)

old_menu = '''            elif choice == "2":
                if remote >= 11:
                    publish_pull_request(progress, repo, branch, commits, state, remote + 1, assume_yes=False)
                else:
                    publish_next(progress, repo, branch, commits, state)
                state = load_json(STATE_FILE, {"published_snapshot": 0, "history": []})
'''

new_menu = '''            elif choice == "2":
                publish_next(progress, repo, branch, commits, state)
                state = load_json(STATE_FILE, {"published_snapshot": 0, "history": []})
'''

old_cmd = '''        elif args.command == "publish":
            remote = remote_snapshot(repo, branch, commits)
            if remote >= 11:
                publish_pull_request(progress, repo, branch, commits, state, remote + 1, assume_yes=False)
            else:
                publish_next(progress, repo, branch, commits, state)
'''

new_cmd = '''        elif args.command == "publish":
            publish_next(progress, repo, branch, commits, state)
'''

if old_menu not in text:
    raise SystemExit("ERROR: menu publish block not found; nothing changed.")
if old_cmd not in text:
    raise SystemExit("ERROR: command publish block not found; nothing changed.")

text = text.replace(old_menu, new_menu, 1)
text = text.replace(old_cmd, new_cmd, 1)

target.write_text(text, encoding="utf-8")

try:
    py_compile.compile(str(target), doraise=True)
except Exception as exc:
    target.write_text(original, encoding="utf-8")
    raise SystemExit(f"ERROR: patch failed compile; original restored: {exc}")

print("DONE: mct-publish now publishes directly to main.")
print("Option 2 = preview -> confirm -> commit -> push.")
print("No PR/merge step for future updates.")
print(f"Backup: {backup}")
