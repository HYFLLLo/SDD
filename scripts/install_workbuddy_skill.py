#!/usr/bin/env python3
"""Install the SDD Harness WorkBuddy entry skill into the user-level skill dir.

Why this script exists
---------------------
WorkBuddy discovers skills only from a fixed set of roots, all under the user
config dir or the builtin plugin dir. The project workspace is NOT scanned.
This was verified empirically:

  - `.skill-list-cache.json` scopeKey lists exactly:
      <configDir>, <configDir>/skills, <builtin>/skills, <configDir>/skills-marketplace
    with no workspace entry.
  - `sdd-harness` appears 0 times in `.skill-list-cache.json` and 0 times in
    `logs/main.log`, while `.workbuddy/skills/sdd-harness/SKILL.md` exists on disk.

So a skill living at `<repo>/.workbuddy/skills/sdd-harness/SKILL.md` is never
registered, no matter how correct its frontmatter is.

The canonical, version-controlled copy stays in the repo. This script syncs it
into `~/.workbuddy/skills/sdd-harness/` so the runtime actually sees it.

Scope safety
------------
User-level skills are visible in EVERY workspace. The installed SKILL.md
therefore starts with a mandatory "workspace guard" (阶段 0) that aborts unless
`harness-core/router.md` exists in the current cwd. This script refuses to
install a copy that lacks that guard.

Usage
-----
    python scripts/install_workbuddy_skill.py            # install / update
    python scripts/install_workbuddy_skill.py --check    # verify only, no writes
    python scripts/install_workbuddy_skill.py --remove   # uninstall

The script is idempotent: re-running only rewrites content that differs.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".workbuddy" / "skills" / "sdd-harness" / "SKILL.md"
SKILL_NAME = "sdd-harness"

# The guard text that makes a globally-visible skill safe. Kept as a literal so
# the installer fails loudly if someone strips it during an edit.
GUARD_MARKER = "harness-core/router.md"
GUARD_SECTION = "阶段 0"


def user_config_dir() -> Path:
    override = os.environ.get("WORKBUDDY_CONFIG_DIR") or os.environ.get("CODEBUDDY_CONFIG_DIR")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return Path.home() / ".workbuddy"


def target_dir() -> Path:
    return user_config_dir() / "skills" / SKILL_NAME


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_source(text: str) -> list[str]:
    """Enforce the contract: valid frontmatter + workspace guard present."""
    problems: list[str] = []

    if not text.startswith("---"):
        return [f"{SKILL_NAME}/SKILL.md: missing YAML frontmatter"]

    parts = text.split("---", 2)
    if len(parts) < 3:
        return [f"{SKILL_NAME}/SKILL.md: unterminated YAML frontmatter"]

    front = parts[1]
    for field in ("name:", "description:"):
        if field not in front:
            problems.append(f"{SKILL_NAME}/SKILL.md: frontmatter missing {field}")

    declared = ""
    for line in front.splitlines():
        if line.startswith("name:"):
            declared = line.split(":", 1)[1].strip()
            break
    if declared != SKILL_NAME:
        problems.append(f"{SKILL_NAME}/SKILL.md: name is {declared!r}, expected {SKILL_NAME!r}")

    body = parts[2]
    if GUARD_SECTION not in body:
        problems.append(
            f"{SKILL_NAME}/SKILL.md: missing '{GUARD_SECTION}' workspace guard. "
            "User-level skills are globally visible; installing without it would "
            "hijack unrelated workspaces."
        )
    elif GUARD_MARKER not in body:
        problems.append(
            f"{SKILL_NAME}/SKILL.md: workspace guard must test for {GUARD_MARKER}"
        )

    return problems


def install(text: str, dest_file: Path, check_only: bool) -> str:
    if dest_file.exists() and read(dest_file) == text:
        return f"unchanged: {dest_file}"
    if check_only:
        return f"DRIFT: {dest_file} missing or out of date"
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, dest_file)
    return f"installed: {dest_file}"


def remove() -> list[str]:
    messages: list[str] = []
    directory = target_dir()
    if not directory.exists():
        return [f"absent: {directory}"]
    for entry in sorted(directory.iterdir(), reverse=True):
        if entry.is_file():
            entry.unlink()
        else:
            shutil.rmtree(entry)
    directory.rmdir()
    messages.append(f"removed: {directory}")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync the SDD WorkBuddy entry skill to user level.")
    parser.add_argument("--check", action="store_true", help="verify only, do not write")
    parser.add_argument("--remove", action="store_true", help="remove the installed skill")
    args = parser.parse_args()

    if args.remove:
        for m in remove():
            print(m)
        return 0

    if not SOURCE.exists():
        print(f"FAIL: source skill missing: {SOURCE}")
        return 1

    text = read(SOURCE)
    problems = validate_source(text)
    if problems:
        print("FAIL: source skill problems found")
        for p in problems:
            print(f"- {p}")
        return 1

    dest_file = target_dir() / "SKILL.md"
    message = install(text, dest_file, args.check)
    print(message)
    print(f"\ntarget dir: {dest_file.parent}")

    if args.check and message.startswith("DRIFT"):
        print("RESULT: drift detected, run without --check to install")
        return 1
    print("RESULT: OK" if args.check else "RESULT: installed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
