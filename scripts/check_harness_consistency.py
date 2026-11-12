#!/usr/bin/env python3
"""Check SDD Harness V7.1 platform adapter consistency."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_PATTERNS = [
    ".output/Plan.md",
    ".output/plan.md",
    ".output/startup.md",
    "继续推进后端开发吗",
    "是否继续推进后端",
    "用户确认满意后进入后端开发",
    "用户确认后才进入后端开发",
    "前端全部完成",
    "Developer 不允许自行装包",
    "禁止安装依赖（列出需要的依赖命令即可）",
    "scenario-alignment",
    "docs/需求文档",
    "harness-core/skills/scenario-alignment",
    "gpt-5.4",
    "gpt-5.5",
    "V7_2",
    "SDD V6",
    "SDD_V6",
    '"harness_version": "V6"',
    '"success": false',
    '"success": true',
    "Vue 3",
    "Pinia",
    "Vue Router",
    "Vuex",
    "vue-tsc",
    "花叔",
    "huashu",
    "Huashu",
    "V6.1",
    "Industrial Refinement",
    "Clinical Curator",
    "Stitch VIBE",
]


REQUIRED_PATHS = [
    ROOT / "AGENTS.md",
    ROOT / ".claude" / "README.md",
    ROOT / ".claude" / "CLAUDE.md",
    ROOT / ".claude" / "agents" / "planner.md",
    ROOT / ".claude" / "agents" / "developer.md",
    ROOT / ".claude" / "agents" / "tester.md",
    ROOT / ".claude" / "commands" / "sdd-bugfix.md",
    ROOT / ".cursor" / "rules" / "00-harness-router.mdc",
    ROOT / ".cursor" / "agents" / "planner.md",
    ROOT / ".cursor" / "agents" / "developer.md",
    ROOT / ".cursor" / "agents" / "tester.md",
    ROOT / ".cursor" / "commands" / "sdd-bugfix.md",
    ROOT / ".cursor" / "dev-standards" / "backend-dev.mdc",
    ROOT / ".cursor" / "dev-standards" / "backend-layers.mdc",
    ROOT / ".cursor" / "dev-standards" / "backend-plugin.mdc",
    ROOT / ".cursor" / "dev-standards" / "frontend.mdc",
    ROOT / ".cursor" / "skills" / "alignment" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "git-workflow" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-bugfix" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-code-review" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-product-design" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-project-maintenance" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-project-import" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-project-delete" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-experience-governance" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-refactor" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "sdd-release" / "SKILL.md",
    ROOT / ".cursor" / "skills" / "ui-design-standard" / "SKILL.md",
    ROOT / ".codex" / "README.md",
    ROOT / ".codex" / "config.toml",
    ROOT / ".codex" / "agents" / "planner.toml",
    ROOT / ".codex" / "agents" / "developer.toml",
    ROOT / ".codex" / "agents" / "tester.toml",
    ROOT / ".codex" / "commands" / "sdd-bugfix.md",
    ROOT / ".workbuddy" / "README.md",
    ROOT / ".workbuddy" / "skills" / "sdd-harness" / "SKILL.md",
    ROOT / ".workbuddy" / "agents" / "planner.md",
    ROOT / ".workbuddy" / "agents" / "developer.md",
    ROOT / ".workbuddy" / "agents" / "tester.md",
    ROOT / ".codebuddy" / "commands" / "sdd-bugfix.md",
    ROOT / "scripts" / "install_workbuddy_agents.py",
    ROOT / "scripts" / "install_workbuddy_skill.py",
    ROOT / "scripts" / "check_workbuddy_adapter.py",
    ROOT / "harness-core" / "protocols" / "codex-subagents.md",
    ROOT / "harness-core" / "protocols" / "workbuddy-subagents.md",
    ROOT / "harness-core" / "skills" / "sdd-project-maintenance" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "sdd-project-delete" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "alignment" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "sdd-bugfix" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "sdd-code-review" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "sdd-experience-governance" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "sdd-refactor" / "SKILL.md",
    ROOT / "harness-core" / "skills" / "sdd-release" / "SKILL.md",
    ROOT / "harness-core" / "router.md",
    ROOT / "scripts" / "check_project_state.py",
    ROOT / "templates" / "project" / "docs" / "澄清文档",
]


FORBIDDEN_PATHS = [
    ROOT / "templates" / "project" / "docs" / "需求文档",
    ROOT / "harness-core" / "skills" / "scenario-alignment",
    ROOT / ".cursor" / "skills" / "scenario-alignment",
    ROOT / ".codex" / "commands" / "sdd-new-project.md",
    ROOT / ".codex" / "commands" / "sdd-align.md",
    ROOT / ".codex" / "commands" / "sdd-start.md",
    ROOT / ".codex" / "commands" / "sdd-maintain.md",
    ROOT / ".codex" / "commands" / "sdd-delete-project.md",
    ROOT / ".claude" / "commands" / "sdd-new-project.md",
    ROOT / ".claude" / "commands" / "sdd-align.md",
    ROOT / ".claude" / "commands" / "sdd-start.md",
    ROOT / ".cursor" / "commands" / "sdd-new-project.md",
    ROOT / ".cursor" / "commands" / "sdd-align.md",
    ROOT / ".cursor" / "commands" / "sdd-start.md",
    ROOT / ".workbuddy" / "commands",
    ROOT / "harness-core" / "commands" / "sdd-new-project.md",
    ROOT / "harness-core" / "commands" / "sdd-align.md",
    ROOT / "harness-core" / "commands" / "sdd-start.md",
]


ADAPTER_DIRS = [
    ROOT / ".cursor",
    ROOT / ".claude",
    ROOT / ".codex",
    ROOT / ".workbuddy",
    ROOT / ".codebuddy",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def is_host_memory(path: Path) -> bool:
    """WorkBuddy host session memory is runtime data, not adapter content."""
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] == ".workbuddy" and parts[1] == "memory"


# Vendor tooling and eval workspaces live under platform skill dirs but are not
# SDD adapters. They are third-party packages or historical evaluation snapshots,
# so they must not be judged by the "adapters must point at harness-core" rule.
NON_ADAPTER_PREFIXES = [
    (".claude", "skills", "skill-creator"),
    (".claude", "skills", "sdd-product-design-optimize-workspace"),
]


def is_non_adapter_content(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return False
    return any(parts[: len(prefix)] == prefix for prefix in NON_ADAPTER_PREFIXES)


def scan_forbidden_patterns() -> list[str]:
    problems: list[str] = []
    scan_roots = [
        ROOT / "AGENTS.md",
        ROOT / "harness-core",
        ROOT / ".cursor",
        ROOT / ".claude",
        ROOT / ".codex",
        ROOT / ".workbuddy",
        ROOT / "scripts",
        ROOT / "templates",
    ]

    for target in scan_roots:
        paths = [target] if target.is_file() else list(target.rglob("*")) if target.exists() else []
        for path in paths:
            if not path.is_file():
                continue
            if path == Path(__file__).resolve():
                continue
            if is_host_memory(path):
                continue
            text = read_text(path)
            for pattern in FORBIDDEN_PATTERNS:
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if pattern not in line:
                        continue
                    if "不得" in line or "不要" in line or "禁止" in line:
                        continue
                    problems.append(f"{path.relative_to(ROOT)}:{line_no} contains forbidden pattern: {pattern}")
    return problems


def scan_required_and_forbidden_paths() -> list[str]:
    problems: list[str] = []
    for path in REQUIRED_PATHS:
        if not path.exists():
            problems.append(f"missing required path: {path.relative_to(ROOT)}")
    for path in FORBIDDEN_PATHS:
        if path.exists():
            problems.append(f"forbidden legacy path exists: {path.relative_to(ROOT)}")
    return problems


def scan_dev_standard_references() -> list[str]:
    problems: list[str] = []
    scan_roots = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "START.md",
        ROOT / "HARNESS.md",
        ROOT / "harness-core",
        ROOT / ".cursor",
        ROOT / ".claude",
        ROOT / ".codex",
        ROOT / ".workbuddy",
        ROOT / "scripts",
        ROOT / "templates",
    ]

    for target in scan_roots:
        paths = [target] if target.is_file() else list(target.rglob("*")) if target.exists() else []
        for path in paths:
            if not path.is_file() or path == Path(__file__).resolve():
                continue
            if is_host_memory(path):
                continue
            text = read_text(path)
            for line_no, line in enumerate(text.splitlines(), start=1):
                if "harness-core/dev-standards/" in line and ".mdc" in line:
                    problems.append(f"{path.relative_to(ROOT)}:{line_no} references core dev-standards .mdc")
    return problems


def scan_project_platform_copies() -> list[str]:
    problems: list[str] = []
    projects_root = ROOT / "Projects_Repo"
    if not projects_root.exists():
        return problems

    for project in projects_root.iterdir():
        if not project.is_dir():
            continue
        for name in [".cursor", ".claude", ".codex", ".workbuddy"]:
            if (project / name).exists():
                problems.append(f"{project.relative_to(ROOT)} contains platform adapter copy: {name}")
    return problems


def scan_workbuddy_adapter() -> list[str]:
    """`.workbuddy/` must stay a thin entry adapter.

    It may point at `harness-core/` and declare platform constraints, but must not
    host a copy of core routing, agent rules, dev standards or skill flows.
    """
    problems: list[str] = []
    adapter = ROOT / ".workbuddy"
    if not adapter.exists():
        return [".workbuddy adapter dir missing"]

    # WorkBuddy's project-level slash-command dir is hardcoded to `.codebuddy/commands`
    # in the client (verified empirically), NOT `.workbuddy/commands`. Keeping the
    # mismatch explicit here so nobody "fixes" it into the wrong path.
    if (adapter / "commands").exists():
        problems.append(
            ".workbuddy/commands must not exist; WorkBuddy reads project commands "
            "from .codebuddy/commands instead"
        )

    problems.extend(scan_workbuddy_commands())

    skill_dir = adapter / "skills" / "sdd-harness" / "SKILL.md"
    if not skill_dir.exists():
        problems.append(".workbuddy/skills/sdd-harness/SKILL.md missing")
    else:
        text = read_text(skill_dir)
        if "harness-core/router.md" not in text:
            problems.append(".workbuddy/skills/sdd-harness/SKILL.md must point to harness-core/router.md")
        if not text.startswith("---"):
            problems.append(".workbuddy/skills/sdd-harness/SKILL.md must start with YAML frontmatter")
        for field in ["name:", "description:"]:
            if field not in text.split("---")[1]:
                problems.append(f".workbuddy/skills/sdd-harness/SKILL.md frontmatter missing {field}")

        # This skill gets installed into ~/.workbuddy/skills/, where it is visible
        # in EVERY workspace. Without a workspace guard it would hijack unrelated
        # projects. scripts/install_workbuddy_skill.py refuses to install a copy
        # missing the guard; this check keeps the source honest too.
        if "阶段 0" not in text:
            problems.append(
                ".workbuddy/skills/sdd-harness/SKILL.md must keep the '阶段 0' workspace guard "
                "(user-level install is globally visible)"
            )

    core_skill_dir = ROOT / "harness-core" / "skills"
    if core_skill_dir.exists():
        core_names = {p.name for p in core_skill_dir.iterdir() if p.is_dir()}
        wb_skills = adapter / "skills"
        if wb_skills.exists():
            for entry in wb_skills.iterdir():
                if entry.is_dir() and entry.name in core_names and entry.name != "sdd-harness":
                    problems.append(
                        f".workbuddy/skills/{entry.name} duplicates harness-core/skills/{entry.name}"
                    )

    problems.extend(scan_workbuddy_agents(adapter))

    protocol = ROOT / "harness-core" / "protocols" / "workbuddy-subagents.md"
    if not protocol.exists():
        problems.append("harness-core/protocols/workbuddy-subagents.md missing")
    return problems


def scan_workbuddy_agents(adapter: Path) -> list[str]:
    """Validate the three role adapters: naming, frontmatter, no core-rule copies."""
    problems: list[str] = []
    agents_dir = adapter / "agents"
    expected_roles = ["planner", "developer", "tester"]

    if not agents_dir.exists():
        return [".workbuddy/agents dir missing"]

    for role in expected_roles:
        path = agents_dir / f"{role}.md"
        if not path.exists():
            problems.append(f".workbuddy/agents/{role}.md missing")
            continue

        text = read_text(path)
        if not text.startswith("---"):
            problems.append(f".workbuddy/agents/{role}.md must start with YAML frontmatter")
            continue

        parts = text.split("---", 2)
        if len(parts) < 3:
            problems.append(f".workbuddy/agents/{role}.md has unterminated frontmatter")
            continue

        front = parts[1]
        for field in ("name:", "description:", "model:"):
            if field not in front:
                problems.append(f".workbuddy/agents/{role}.md frontmatter missing {field}")

        declared_name = ""
        for line in front.splitlines():
            if line.startswith("name:"):
                declared_name = line.split(":", 1)[1].strip()
                break
        if declared_name != role:
            problems.append(
                f".workbuddy/agents/{role}.md declares name {declared_name!r}, expected {role!r}"
            )

        core_ref = f"harness-core/agents/{role}.md"
        if core_ref not in text:
            problems.append(f".workbuddy/agents/{role}.md must point to {core_ref}")

    return problems


def scan_workbuddy_commands() -> list[str]:
    """Validate `.codebuddy/commands/` -- WorkBuddy's real project command dir.

    Contract: exactly one command (`sdd-bugfix`), and it must stay a thin adapter
    that points at `harness-core/` rather than copying the fix procedure.
    """
    problems: list[str] = []
    commands_dir = ROOT / ".codebuddy" / "commands"

    if not commands_dir.exists():
        problems.append(".codebuddy/commands dir missing")
        return problems

    found = {p.stem for p in commands_dir.glob("*.md")}
    if "sdd-bugfix" not in found:
        problems.append(".codebuddy/commands/sdd-bugfix.md missing")
    extra = found - {"sdd-bugfix"}
    for name in sorted(extra):
        problems.append(
            f".codebuddy/commands/{name}.md not allowed (only sdd-bugfix is adapted)"
        )

    command = commands_dir / "sdd-bugfix.md"
    if command.exists():
        text = read_text(command)
        if not text.startswith("---"):
            problems.append(".codebuddy/commands/sdd-bugfix.md must start with YAML frontmatter")
        else:
            parts = text.split("---", 2)
            if len(parts) < 3:
                problems.append(".codebuddy/commands/sdd-bugfix.md has unterminated frontmatter")
            elif "description:" not in parts[1]:
                problems.append(".codebuddy/commands/sdd-bugfix.md frontmatter missing description:")
        if "harness-core/commands/sdd-bugfix.md" not in text:
            problems.append(
                ".codebuddy/commands/sdd-bugfix.md must point to harness-core/commands/sdd-bugfix.md"
            )
        if "工作区校验" not in text:
            problems.append(
                ".codebuddy/commands/sdd-bugfix.md must keep the workspace guard "
                "(it is the only adapted command and must not fire outside the Harness repo)"
            )

    return problems


HARNESS_REF_PATTERN = re.compile(r"harness-core/[A-Za-z0-9_\-./*]+")


def scan_core_reference_resolution() -> list[str]:
    """Every `harness-core/...` path cited by an adapter must resolve.

    Adapters are thin pointers, so a broken pointer silently disables the whole
    platform without any file going missing. Platform-neutral by design: one scan
    covers Codex, Claude Code, Cursor and WorkBuddy.
    """
    problems: list[str] = []
    for adapter_dir in ADAPTER_DIRS:
        if not adapter_dir.exists():
            continue
        for path in adapter_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".mdc", ".toml"}:
                continue
            if is_host_memory(path) or is_non_adapter_content(path):
                continue
            text = read_text(path)
            for line_no, line in enumerate(text.splitlines(), start=1):
                for match in HARNESS_REF_PATTERN.findall(line):
                    ref = match.rstrip(".,;:)`*")
                    target = ROOT / ref
                    if "*" in ref:
                        resolved = list(ROOT.glob(ref))
                    else:
                        resolved = [target] if target.exists() else []
                    if not resolved:
                        problems.append(
                            f"{path.relative_to(ROOT)}:{line_no} cites missing core path: {ref}"
                        )
    return problems


def scan_static_agent_adapters(adapter_rel: str) -> list[str]:
    """Validate a platform's static subagent adapters.

    Codex (TOML) and WorkBuddy (user-level install) have their own scanners, but
    Claude Code and Cursor were previously unguarded: every adapter could be
    deleted or repointed at a nonexistent core file and the suite still passed.
    Contract for both: one file per role, `name` matching the filename, a
    `description`, a `model`, and a pointer to `harness-core/agents/<role>.md`.
    """
    problems: list[str] = []
    agents_dir = ROOT / adapter_rel / "agents"
    expected_roles = ["planner", "developer", "tester"]

    if not agents_dir.exists():
        return [f"{adapter_rel}/agents dir missing"]

    for role in expected_roles:
        path = agents_dir / f"{role}.md"
        rel = f"{adapter_rel}/agents/{role}.md"
        if not path.exists():
            problems.append(f"{rel} missing")
            continue

        text = read_text(path)
        if not text.startswith("---"):
            problems.append(f"{rel} must start with YAML frontmatter")
            continue

        parts = text.split("---", 2)
        if len(parts) < 3:
            problems.append(f"{rel} has unterminated frontmatter")
            continue

        front = parts[1]
        for field in ("name:", "description:", "model:"):
            if field not in front:
                problems.append(f"{rel} frontmatter missing {field}")

        declared_name = ""
        for line in front.splitlines():
            if line.startswith("name:"):
                declared_name = line.split(":", 1)[1].strip()
                break
        if declared_name != role:
            problems.append(f"{rel} declares name {declared_name!r}, expected {role!r}")

        core_ref = f"harness-core/agents/{role}.md"
        if core_ref not in text:
            problems.append(f"{rel} must point to {core_ref}")

    return problems


def scan_adapter_core_leakage() -> list[str]:
    problems: list[str] = []
    allowed_phrases = [
        "harness-core/",
        "SDD Harness",
        "适配器",
        "adapter",
    ]

    for adapter_dir in ADAPTER_DIRS:
        if not adapter_dir.exists():
            problems.append(f"missing adapter dir: {adapter_dir.relative_to(ROOT)}")
            continue
        for path in adapter_dir.rglob("*"):
            if not path.is_file():
                continue
            if is_host_memory(path) or is_non_adapter_content(path):
                continue
            text = read_text(path)
            if path.suffix in {".md", ".mdc", ".toml"} and "harness-core/" not in text and path.name != "config.toml":
                if not any(phrase in text for phrase in allowed_phrases):
                    problems.append(f"{path.relative_to(ROOT)} may not reference harness-core")
    return problems


def scan_tasks_template() -> list[str]:
    problems: list[str] = []
    path = ROOT / "templates" / "tasks.json"
    if not path.exists():
        return ["missing tasks template: templates/tasks.json"]

    data = json.loads(path.read_text(encoding="utf-8"))
    tasks = data.get("tasks", [])
    if not tasks:
        return ["templates/tasks.json has no sample task"]

    task = tasks[0]
    acceptance = task.get("acceptanceCriteria", [])
    technical = task.get("technicalChecks", [])
    for item in ["Typecheck passes", "Lint passes"]:
        if item in acceptance:
            problems.append(f"templates/tasks.json keeps technical check in acceptanceCriteria: {item}")
        if item not in technical:
            problems.append(f"templates/tasks.json missing technicalChecks item: {item}")
    if "user_gate" not in task:
        problems.append("templates/tasks.json missing user_gate")
    return problems


def scan_pycore_contracts() -> list[str]:
    problems: list[str] = []
    response_path = ROOT / "pycore" / "api" / "responses.py"
    config_path = ROOT / "pycore" / "core" / "config.py"
    logger_path = ROOT / "pycore" / "core" / "logger.py"

    response_text = read_text(response_path)
    if "code: int = 200" not in response_text or 'message: str = "success"' not in response_text:
        problems.append("pycore/api/responses.py must expose code/message/data response format")
    if "success: bool" in response_text or "error_code: Optional[str] = Field" in response_text:
        problems.append("pycore/api/responses.py still contains legacy success/error_code response fields")

    config_text = read_text(config_path)
    if "use_env: bool = False" not in config_text:
        problems.append("pycore/core/config.py ConfigManager.load must default use_env=False")
    if "os.environ" in config_text or "PYCORE_" in config_text:
        problems.append("pycore/core/config.py must not read process environment variables")

    logger_text = read_text(logger_path)
    if "os.getenv" in logger_text or "ENV_MODE" in logger_text:
        problems.append("pycore/core/logger.py must not read ENV_MODE from process environment")
    return problems


def scan_frontend_stack_contracts() -> list[str]:
    problems: list[str] = []
    frontend_path = ROOT / "harness-core" / "dev-standards" / "frontend.md"
    phase_c_path = ROOT / "harness-core" / "skills" / "sdd-product-design" / "phase-C.md"

    frontend_text = read_text(frontend_path)
    required_frontend_terms = [
        "React + TypeScript + Vite",
        "react-router",
        "Zustand",
        "Axios",
        "Ant Design",
        "Ant Design Mobile",
        "TanStack Query",
        "ESLint + Prettier",
    ]
    for term in required_frontend_terms:
        if term not in frontend_text:
            problems.append(f"harness-core/dev-standards/frontend.md missing React stack term: {term}")

    phase_c_text = read_text(phase_c_path)
    for term in ["React", "Ant Design", "Ant Design Mobile", "TanStack Query"]:
        if term not in phase_c_text:
            problems.append(f"harness-core/skills/sdd-product-design/phase-C.md missing frontend selection term: {term}")
    return problems


def scan_cursor_skill_coverage() -> list[str]:
    """Every `harness-core/skills/<name>` must have a Cursor thin pointer.

    Cursor discovers skills by scanning `.cursor/skills/**`, so a core skill with
    no pointer is invisible on that platform even though the file exists. This
    drifted once already (three skills were missing pointers while the docs
    claimed "four platforms are identical"), so it is checked mechanically now.

    Pointer contract: YAML frontmatter with `name` matching the directory, a
    `description`, and a reference to the core SKILL.md path. Pointers may not
    host a copy of the flow -- `scan_adapter_core_leakage` covers that side.
    """
    problems: list[str] = []
    core_skills = ROOT / "harness-core" / "skills"
    cursor_skills = ROOT / ".cursor" / "skills"

    if not core_skills.exists():
        return [f"missing core skills dir: {core_skills.relative_to(ROOT)}"]
    if not cursor_skills.exists():
        return [f"missing cursor skills dir: {cursor_skills.relative_to(ROOT)}"]

    core_names = {p.name for p in core_skills.iterdir() if p.is_dir()}
    cursor_names = {p.name for p in cursor_skills.iterdir() if p.is_dir()}

    for name in sorted(core_names - cursor_names):
        problems.append(
            f".cursor/skills/{name}/SKILL.md missing "
            f"(harness-core/skills/{name} has no Cursor pointer)"
        )

    for name in sorted(cursor_names - core_names):
        problems.append(
            f".cursor/skills/{name}/ exists but harness-core/skills/{name} does not "
            f"(stale pointer)"
        )

    for name in sorted(core_names & cursor_names):
        path = cursor_skills / name / "SKILL.md"
        rel = f".cursor/skills/{name}/SKILL.md"
        if not path.exists():
            problems.append(f"{rel} missing")
            continue
        text = read_text(path)
        if not text.startswith("---"):
            problems.append(
                f"{rel} must start with YAML frontmatter (Cursor discovers skills by frontmatter)"
            )
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            problems.append(f"{rel} has unterminated frontmatter")
            continue
        if f"name: {name}" not in parts[1]:
            problems.append(f"{rel} frontmatter must declare name: {name}")
        if "description:" not in parts[1]:
            problems.append(f"{rel} frontmatter missing description:")
        if f"harness-core/skills/{name}/SKILL.md" not in text:
            problems.append(f"{rel} must point to harness-core/skills/{name}/SKILL.md")

    return problems


def main() -> int:
    problems = []
    problems.extend(scan_forbidden_patterns())
    problems.extend(scan_required_and_forbidden_paths())
    problems.extend(scan_dev_standard_references())
    problems.extend(scan_project_platform_copies())
    problems.extend(scan_adapter_core_leakage())
    problems.extend(scan_core_reference_resolution())
    problems.extend(scan_static_agent_adapters(".claude"))
    problems.extend(scan_static_agent_adapters(".cursor"))
    problems.extend(scan_cursor_skill_coverage())
    problems.extend(scan_workbuddy_adapter())
    problems.extend(scan_tasks_template())
    problems.extend(scan_pycore_contracts())
    problems.extend(scan_frontend_stack_contracts())

    if problems:
        print("FAIL: SDD Harness consistency problems found")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("PASS: SDD Harness consistency checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
