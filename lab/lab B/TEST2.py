from pathlib import Path

project_root = Path(__file__).resolve().parents[2]

bad = project_root / "data" / "phase2_lab" / "not_really_a_zip.zip"
bad.write_text("this is ordinary text", encoding="utf-8")

print(bad)