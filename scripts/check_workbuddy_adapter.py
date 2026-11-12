#!/usr/bin/env python3
"""Verify that the SDD Harness WorkBuddy adapter is actually live, not just on disk.

Why this script exists
----------------------
WorkBuddy splits its adapter state across two different places, and the two
behave differently. Without a single check, people debug the wrong layer for
hours:

  | 链路                | 仓库位置                        | 运行时位置              | 生效方式            |
  |---------------------|---------------------------------|-------------------------|---------------------|
  | 入口指令 AGENTS.md  | AGENTS.md                       | （工作区根，直接读）    | 会话启动时快照      |
  | 子智能体            | .workbuddy/agents/*.md          | ~/.workbuddy/agents/    | 变更后即时生效      |
  | 入口 Skill          | .workbuddy/skills/.../SKILL.md  | ~/.workbuddy/skills/... | 新会话 / 手动刷新   |
  | 斜杠命令            | .codebuddy/commands/*.md        | （工作区根，直接读）    | 新会话              |

The important asymmetry: **subagents hot-load, skills do not** (both verified
empirically). So "did my edit take effect?" has a different answer per layer.

This script answers it per layer, and tells you exactly what to do about it.

Usage
-----
    python scripts/check_workbuddy_adapter.py           # 人读报告
    python scripts/check_workbuddy_adapter.py --quiet   # 仅退出码
    python scripts/check_workbuddy_adapter.py --json    # 机读输出

Exit codes: 0 = all layers live, 1 = at least one layer needs action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("planner", "developer", "tester")
SKILL_NAME = "sdd-harness"

# Model names must exist in models.json, otherwise the runtime silently falls
# back and the role may behave differently than intended.
REQUIRED_MODELS = ("EB-DeepSeek-Flash", "EB-DeepSeek-Pro", "EB-GLM-Pro")


def config_dir() -> Path:
    override = os.environ.get("WORKBUDDY_CONFIG_DIR") or os.environ.get("CODEBUDDY_CONFIG_DIR")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return Path.home() / ".workbuddy"


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def frontmatter_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    for line in parts[1].splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def check_agents(cfg: Path) -> dict:
    """Subagents: repo source must match user-level copy. Hot-loads."""
    rows = []
    ok = True
    for role in ROLES:
        src = ROOT / ".workbuddy" / "agents" / f"{role}.md"
        dst = cfg / "agents" / f"{role}.md"
        row = {"role": role, "source": src.exists(), "installed": dst.exists()}

        if not src.exists():
            row["state"] = "源文件缺失"
            ok = False
        elif not dst.exists():
            row["state"] = "未安装"
            ok = False
        elif md5(src) != md5(dst):
            row["state"] = "已过期（需重装）"
            ok = False
        else:
            declared = frontmatter_name(dst)
            if declared != role:
                row["state"] = f"name 不符（声明为 {declared}）"
                ok = False
            else:
                row["state"] = "已生效"
        rows.append(row)
    return {"name": "子智能体", "ok": ok, "rows": rows, "reload": "即时生效"}


def check_skill(cfg: Path) -> dict:
    """Entry skill: repo source vs user-level copy, plus registry cache."""
    src = ROOT / ".workbuddy" / "skills" / SKILL_NAME / "SKILL.md"
    dst = cfg / "skills" / SKILL_NAME / "SKILL.md"
    cache = cfg / ".skill-list-cache.json"

    detail = {}
    problems = []

    if not src.exists():
        problems.append("仓库源文件缺失")
    if not dst.exists():
        problems.append("未安装到用户级（Skills 根不扫描工作区）")
    elif src.exists() and md5(src) != md5(dst):
        problems.append("已安装副本与仓库源不一致（需重装）")

    registered = False
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            names = [r.get("name") for r in data.get("results", []) if isinstance(r, dict)]
            registered = SKILL_NAME in names
            detail["cache_saved_at"] = data.get("savedAt")
            detail["watching"] = any(
                SKILL_NAME in str(x) for x in data.get("watch", {}).get("dirs", [])
            )
        except (ValueError, OSError):
            problems.append("技能缓存无法解析")

    if not registered:
        problems.append("尚未出现在技能列表中（需新会话或手动刷新）")

    detail.update(problems=problems, registered=registered)
    return {
        "name": "入口 Skill",
        "ok": not problems,
        "rows": [detail],
        "reload": "新会话 / 手动刷新",
    }


def check_commands() -> dict:
    """The single adapted slash command."""
    cmd_dir = ROOT / ".codebuddy" / "commands"
    cmd = cmd_dir / "sdd-bugfix.md"
    wrong_dir = ROOT / ".workbuddy" / "commands"

    problems = []
    if not cmd.exists():
        problems.append(".codebuddy/commands/sdd-bugfix.md 缺失")
    if wrong_dir.exists():
        problems.append(".workbuddy/commands 不应存在（客户端只读 .codebuddy/commands）")

    return {
        "name": "斜杠命令",
        "ok": not problems,
        "rows": [{"file": str(cmd.relative_to(ROOT)), "problems": problems}],
        "reload": "新会话",
    }


def check_models(cfg: Path) -> dict:
    """Declared models must exist in models.json."""
    models_file = cfg / "models.json"
    known: list[str] = []
    problems: list[str] = []

    if models_file.exists():
        try:
            data = json.loads(models_file.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("models", [])
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("id")
                    if name:
                        known.append(str(name))
        except (ValueError, OSError):
            problems.append("models.json 无法解析")

    if known:
        for model in REQUIRED_MODELS:
            if model not in known:
                problems.append(f"模型 {model} 不在 models.json 中")

    return {
        "name": "角色模型",
        "ok": not problems,
        "rows": [{"known": known, "problems": problems}],
        "reload": "-",
    }


def check_entry(cfg: Path) -> dict:
    """AGENTS.md presence. Content is snapshotted at session start."""
    agents_md = ROOT / "AGENTS.md"
    problems = []
    if not agents_md.exists():
        problems.append("AGENTS.md 缺失")
    elif "harness-core/router.md" not in agents_md.read_text(encoding="utf-8", errors="replace"):
        problems.append("AGENTS.md 未指向 harness-core/router.md")

    return {
        "name": "根入口 AGENTS.md",
        "ok": not problems,
        "rows": [{"problems": problems}],
        "reload": "会话启动时快照",
    }


def render(results: list[dict]) -> None:
    print("=" * 66)
    print("WorkBuddy 适配层生效状态")
    print("=" * 66)
    for r in results:
        mark = "OK  " if r["ok"] else "FAIL"
        print(f"\n[{mark}] {r['name']}   （生效方式：{r['reload']}）")
        for row in r["rows"]:
            for key, value in row.items():
                if key == "problems":
                    for p in value:
                        print(f"        - {p}")
                elif isinstance(value, bool):
                    print(f"        {key}: {'是' if value else '否'}")
                elif isinstance(value, list):
                    if value:
                        print(f"        {key}: {', '.join(map(str, value))}")
                elif value not in (None, ""):
                    print(f"        {key}: {value}")

    bad = [r["name"] for r in results if not r["ok"]]
    print("\n" + "=" * 66)
    if bad:
        print("需要处理：", "、".join(bad))
        print("\n提示：子智能体改动即时生效；Skill 与斜杠命令需新会话。")
    else:
        print("全部链路已生效。")
    print("=" * 66)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 WorkBuddy 适配层是否真正生效")
    parser.add_argument("--quiet", action="store_true", help="只输出退出码")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    cfg = config_dir()
    results = [
        check_entry(cfg),
        check_agents(cfg),
        check_skill(cfg),
        check_commands(),
        check_models(cfg),
    ]
    ok = all(r["ok"] for r in results)

    if args.json:
        print(json.dumps({"ok": ok, "configDir": str(cfg), "layers": results},
                         ensure_ascii=False, indent=2))
    elif not args.quiet:
        render(results)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
