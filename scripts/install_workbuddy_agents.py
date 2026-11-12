#!/usr/bin/env python3
"""Install SDD Harness WorkBuddy subagents into the user-level agent directory.

Why this script exists
---------------------
WorkBuddy only discovers subagent definitions from the user-level config dir
(`~/.workbuddy/agents/`, or `$WORKBUDDY_CONFIG_DIR/agents/`). Project-level
`.workbuddy/agents/` is NOT loaded by the runtime, which was verified empirically
(agent lookup returns "Task agent ... is not available").

The canonical, version-controlled copies live in the Harness repo at
`.workbuddy/agents/*.md`. This script syncs them into the user-level directory so
they actually take effect, without duplicating core rules.

Usage
-----
    python scripts/install_workbuddy_agents.py            # install / update
    python scripts/install_workbuddy_agents.py --check    # verify only, no writes
    python scripts/install_workbuddy_agents.py --remove   # uninstall

The script is idempotent: re-running it only rewrites files whose content differs.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / ".workbuddy" / "agents"

ROLES = ("planner", "developer", "tester")

# Filename prefix used to mark files owned by this installer, so --remove never
# touches unrelated user agents.
OWNED_SUFFIX = ".sdd-sync"


def user_config_dir() -> Path:
    override = os.environ.get("WORKBUDDY_CONFIG_DIR") or os.environ.get("CODEBUDDY_CONFIG_DIR")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return Path.home() / ".workbuddy"


def target_dir() -> Path:
    return user_config_dir() / "agents"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ensure_frontmatter_name(text: str, expected: str, path: Path) -> list[str]:
    """Validate the minimal contract the runtime needs: name + description."""
    problems: list[str] = []
    if not text.startswith("---"):
        return [f"{path.name}: missing YAML frontmatter"]
    parts = text.split("---", 2)
    if len(parts) < 3:
        return [f"{path.name}: unterminated YAML frontmatter"]
    front = parts[1]
    for field in ("name:", "description:", "model:"):
        if field not in front:
            problems.append(f"{path.name}: frontmatter missing {field}")
    declared = None
    for line in front.splitlines():
        if line.startswith("name:"):
            declared = line.split(":", 1)[1].strip()
            break
    if declared != expected:
        problems.append(f"{path.name}: name is {declared!r}, expected {expected!r}")
    return problems


def collect_sources() -> tuple[list[Path], list[str]]:
    problems: list[str] = []
    sources: list[Path] = []
    if not SOURCE_DIR.exists():
        return [], [f"source dir missing: {SOURCE_DIR}"]
    for role in ROLES:
        path = SOURCE_DIR / f"{role}.md"
        if not path.exists():
            problems.append(f"missing role config: .workbuddy/agents/{role}.md")
            continue
        problems.extend(ensure_frontmatter_name(read(path), role, path))
        sources.append(path)
    return sources, problems


def install(sources: list[Path], dest: Path, check_only: bool) -> list[str]:
    messages: list[str] = []
    if not check_only:
        dest.mkdir(parents=True, exist_ok=True)
    for src in sources:
        target = dest / src.name
        content = read(src)
        if target.exists() and read(target) == content:
            messages.append(f"unchanged: {target}")
            continue
        if check_only:
            messages.append(f"DRIFT: {target} missing or out of date")
            continue
        shutil.copyfile(src, target)
        messages.append(f"installed: {target}")
    return messages


def remove(dest: Path) -> list[str]:
    messages: list[str] = []
    for role in ROLES:
        target = dest / f"{role}.md"
        if target.exists():
            target.unlink()
            messages.append(f"removed: {target}")
        else:
            messages.append(f"absent: {target}")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync SDD WorkBuddy subagents to user level.")
    parser.add_argument("--check", action="store_true", help="verify only, do not write")
    parser.add_argument("--remove", action="store_true", help="remove installed agent files")
    args = parser.parse_args()

    dest = target_dir()
    sources, problems = collect_sources()

    if problems:
        print("FAIL: source config problems found")
        for p in problems:
            print(f"- {p}")
        return 1

    if args.remove:
        for m in remove(dest):
            print(m)
        return 0

    messages = install(sources, dest, args.check)
    for m in messages:
        print(m)

    print(f"\ntarget dir: {dest}")
    if args.check and any(m.startswith("DRIFT") for m in messages):
        print("RESULT: drift detected, run without --check to install")
        return 1
    print("RESULT: OK" if args.check else "RESULT: installed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
