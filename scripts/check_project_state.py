#!/usr/bin/env python3
"""Inspect a managed SDD project's on-disk state and report problems.

The Harness itself has had `check_harness_consistency.py` from early on, but the
per-project side had nothing equivalent. Real incidents that this would have
caught (or did catch only by accident):

- `tasks.json` saved with a BOM, so `json.load` failed with "Invalid object".
- `tasks.json` status disagreeing with `Plan.md` checkboxes.
- Leftover `*.patch` / `.sdd/tmp/` files shipped inside a delivered project.
- `[Mock]` markers surviving into a project that was declared delivered.
- Business dirs (`docs/`, `.sdd/`) appearing under the Harness root.

Usage:
    python scripts/check_project_state.py            # active project
    python scripts/check_project_state.py novel      # named project
    python scripts/check_project_state.py --all      # every registered project
    python scripts/check_project_state.py --json     # machine-readable output

Exit code is 0 only when no ERROR-level problem is found. WARN does not fail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "project-registry.json"

# Directories that must never appear at the Harness root; they belong to a project.
# NOTE: `pycore/` is deliberately absent -- the Harness root hosts the framework
# source that `sdd_project.py::copy_harness` copies into each project. Flagging it
# would be a false positive on the framework's own layout.
MISPLACED_DIRS = ["docs", ".sdd", "frontend", "backend", "mobile"]

# Artifacts a project must have before multi-agent development is allowed.
# Mirrors router.md "开发门禁" items 1-4 (prototypes is optional if waived).
REQUIRED_ARTIFACTS = [
    ("docs/PRD.md", "PRD"),
    ("docs/api-contracts.md", "接口契约"),
    ("docs/Plan.md", "开发计划"),
]

VALID_STATUSES = {"pending", "in_progress", "passed", "failed", "fixing", "blocked"}

MAX_EXPERIENCE_BYTES = 32 * 1024  # hard threshold from sdd-experience-governance
WARN_EXPERIENCE_BYTES = 20 * 1024


class Finding:
    __slots__ = ("level", "code", "message")

    def __init__(self, level: str, code: str, message: str) -> None:
        self.level = level
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message}


def err(code: str, message: str) -> Finding:
    return Finding("ERROR", code, message)


def warn(code: str, message: str) -> Finding:
    return Finding("WARN", code, message)


def info(code: str, message: str) -> Finding:
    return Finding("INFO", code, message)


def read_json(path: Path) -> tuple[object | None, list[Finding]]:
    """Load JSON while separating encoding problems from structural problems.

    A BOM is the single most damaging encoding fault here: the file looks fine in
    an editor, but every `json.load` in the toolchain fails. Report it by name so
    the fix is obvious instead of "invalid object at line 1".
    """
    findings: list[Finding] = []
    if not path.exists():
        findings.append(err("json.missing", f"{path.name} 不存在"))
        return None, findings

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        findings.append(
            err("encoding.bom", f"{path.name} 含 UTF-8 BOM，会导致 json.load 失败（应存为 UTF-8 无 BOM）")
        )
    if b"\r\n" in raw:
        findings.append(warn("encoding.crlf", f"{path.name} 使用 CRLF 换行（建议 LF，避免 diff 噪音）"))

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        findings.append(err("encoding.not_utf8", f"{path.name} 不是合法 UTF-8：{exc}"))
        return None, findings

    if "\ufffd" in text:
        findings.append(err("encoding.replacement", f"{path.name} 含 U+FFFD 替换字符，说明曾按错误编码读写"))

    try:
        return json.loads(text), findings
    except json.JSONDecodeError as exc:
        findings.append(err("json.invalid", f"{path.name} 解析失败：{exc}"))
        return None, findings


def scan_misplaced_dirs(findings: list[Finding]) -> None:
    """Business dirs at the Harness root mean a project wrote outside its sandbox."""
    for name in MISPLACED_DIRS:
        path = ROOT / name
        if path.exists():
            # `docs/` at the Harness root legitimately holds framework analysis
            # documents, so only flag it when it looks like project business docs.
            if name == "docs":
                business = ["PRD.md", "api-contracts.md", "Plan.md"]
                hits = [b for b in business if (path / b).exists()]
                if not hits:
                    continue
                findings.append(
                    err(
                        "misplaced.project_docs",
                        f"Harness 根目录出现业务文档 docs/{{{','.join(hits)}}}，应位于 Projects_Repo/<id>/ 内",
                    )
                )
                continue
            findings.append(
                err("misplaced.dir", f"Harness 根目录出现业务目录 {name}/，应位于 Projects_Repo/<id>/ 内")
            )


def scan_registry(findings: list[Finding]) -> dict:
    data, json_findings = read_json(REGISTRY)
    findings.extend(json_findings)
    return data if isinstance(data, dict) else {}


def resolve_projects(registry: dict, target: str | None, use_all: bool) -> list[str]:
    projects = registry.get("projects", [])
    ids = [p.get("id") for p in projects if p.get("id")]
    if use_all:
        return ids
    if target:
        return [target]
    active = registry.get("active_project_id")
    return [active] if active else []


def check_task_states(tasks_data: object, findings: list[Finding]) -> dict:
    """Validate the task state machine and return a small summary."""
    summary = {"total": 0, "by_status": {}, "passed": 0, "user_gate_passed": 0}
    if not isinstance(tasks_data, dict):
        return summary
    tasks = tasks_data.get("tasks", [])
    if not isinstance(tasks, list):
        findings.append(err("tasks.invalid", "tasks 字段不是数组"))
        return summary

    summary["total"] = len(tasks)
    seen: set[str] = set()
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            findings.append(err("tasks.item", f"tasks[{idx}] 不是对象"))
            continue
        tid = task.get("id") or f"tasks[{idx}]"
        if tid in seen:
            findings.append(err("tasks.duplicate_id", f"任务 ID 重复：{tid}"))
        seen.add(tid)

        status = task.get("status")
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        if status == "passed":
            summary["passed"] += 1
            if task.get("user_gate"):
                summary["user_gate_passed"] += 1

        if status not in VALID_STATUSES:
            findings.append(err("tasks.bad_status", f"{tid} 的 status={status!r} 不在允许值内"))
        if status == "blocked" and task.get("blocked") is not True:
            findings.append(
                warn("tasks.blocked_flag", f"{tid} status=blocked 但 blocked 字段未置 true（状态机字段不一致）")
            )
        if status == "passed" and task.get("blocked") is True:
            findings.append(err("tasks.passed_but_blocked", f"{tid} 同时是 passed 与 blocked=true"))
        if status == "fixing":
            rc = task.get("retry_count", 0)
            if isinstance(rc, int) and rc > 3:
                findings.append(warn("tasks.retry_exceeded", f"{tid} retry_count={rc} 已超 3 次上限"))
        if not task.get("acceptanceCriteria"):
            findings.append(warn("tasks.no_ac", f"{tid} 缺少 acceptanceCriteria"))
        # Mixing technical checks into acceptance criteria breaks the
        # human-vs-machine split the framework relies on.
        ac = task.get("acceptanceCriteria") or []
        for item in ("Typecheck passes", "Lint passes"):
            if isinstance(ac, list) and item in ac:
                findings.append(
                    err("tasks.ac_pollution", f"{tid} 把技术检查 {item!r} 写进了 acceptanceCriteria")
                )
    return summary


def check_plan_alignment(tasks_summary: dict, project: Path, findings: list[Finding]) -> None:
    """Cross-check tasks.json against Plan.md checkbox counts.

    Plan.md is the human-facing progress file, tasks.json the machine one; they
    drift in practice. Compare coarse counts rather than trying to map titles,
    because that mapping fails on any renamed task.

    Two traps learned from real projects:

    1. Count mismatch is usually a **granularity** difference, not a bug. A real
       project had 8 feature-level checkboxes in Plan.md against 25 task-level
       entries in tasks.json, all 25 passed -- perfectly healthy, yet a naive
       comparison screams. So `total != task_total` is INFO only.

    2. Direction matters for progress. Plan claiming MORE done than tasks.json
       proves (`done > passed`) is the dangerous one: the human-facing file
       overstates delivery. The reverse (`done < passed`) just means Plan.md
       was not updated after the last task -- annoying, not risky.
    """
    plan = project / "docs" / "Plan.md"
    if not plan.exists():
        return
    try:
        text = plan.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        findings.append(err("plan.encoding", "docs/Plan.md 不是合法 UTF-8"))
        return
    total = text.count("- [ ]") + text.count("- [x]") + text.count("- [X]")
    done = text.count("- [x]") + text.count("- [X]")
    task_total = tasks_summary.get("total", 0)
    passed = tasks_summary.get("passed", 0)
    if not total or not task_total:
        return
    if total != task_total:
        findings.append(
            info(
                "state.plan_task_mismatch",
                f"Plan.md 有 {total} 个勾选项，tasks.json 有 {task_total} 个任务"
                f"（通常为功能级 vs 任务级的口径差异，非缺陷）",
            )
        )
    if done > passed:
        findings.append(
            err(
                "state.plan_overstates",
                f"Plan.md 勾选完成 {done} 项，但 tasks.json 仅 {passed} 个 passed"
                f"——Plan.md 虚报进度，验收前须核实并回改",
            )
        )
    elif done < passed:
        findings.append(
            info(
                "state.plan_stale",
                f"tasks.json 已 {passed} 个 passed，Plan.md 只勾了 {done} 项（Plan 未同步，收口时补勾）",
            )
        )


def check_status_json(status_data: object, tasks_summary: dict, findings: list[Finding]) -> None:
    if not isinstance(status_data, dict):
        return
    stage = status_data.get("stage")
    blocked = status_data.get("blocked")
    by_status = tasks_summary.get("by_status", {})
    if blocked is True and not by_status.get("blocked"):
        findings.append(
            warn("state.blocked_mismatch", f"status.json blocked=true 但 tasks.json 无 blocked 任务（stage={stage}）")
        )
    if blocked is False and by_status.get("blocked"):
        findings.append(
            warn(
                "state.blocked_mismatch",
                f"tasks.json 有 {by_status['blocked']} 个 blocked 任务，但 status.json blocked=false",
            )
        )
    total = tasks_summary.get("total", 0)
    passed = tasks_summary.get("passed", 0)
    if stage in {"completed", "development-complete"} and total and passed < total:
        findings.append(
            err(
                "state.stage_claim",
                f"status.json stage={stage} 声称完成，但 tasks.json 仅 {passed}/{total} 为 passed",
            )
        )


def check_artifacts(project: Path, findings: list[Finding]) -> None:
    for rel, label in REQUIRED_ARTIFACTS:
        if not (project / rel).exists():
            findings.append(warn("artifact.missing", f"缺少 {label}：{rel}"))
    if not (project / "docs" / "prototypes").exists():
        findings.append(info("artifact.prototypes", "docs/prototypes/ 不存在（如用户已放弃原型要求可忽略）"))
    if not (project / "docs" / "startup.md").exists():
        findings.append(info("artifact.startup", "docs/startup.md 尚未产出（交付前需按 sdd-release 补齐）"))


def _gitignore_covers(project: Path, target: Path) -> tuple[bool, str]:
    """Approximate git's own rule: nearest .gitignore wins, walking up to root.

    Checking only the project-root `.gitignore` produces false negatives -- a
    real case was `novel/frontend/.gitignore` listing `.env.local` and
    `.env.*.local` while `.env.production` existed and was NOT ignored. Under git
    semantics that file is tracked; a root-only check would never notice.

    Returns (covered, which_gitignore).
    """
    rel_dir = target.parent
    while True:
        gi = rel_dir / ".gitignore"
        if gi.exists():
            try:
                lines = [ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()]
            except UnicodeDecodeError:
                lines = []
            name = target.name
            for line in lines:
                if not line or line.startswith("#"):
                    continue
                pattern = line.rstrip("/")
                if pattern in {name, "*"}:
                    return True, str(gi.relative_to(project))
                if pattern.startswith("*.") and name.endswith(pattern[1:]):
                    return True, str(gi.relative_to(project))
                # `.env.*.local` style: prefix + wildcard + suffix
                if "*" in pattern:
                    prefix, _, suffix = pattern.partition("*")
                    if name.startswith(prefix) and name.endswith(suffix):
                        return True, str(gi.relative_to(project))
                # A bare `.env` line does not cover `.env.production` in git.
                if pattern == name:
                    return True, str(gi.relative_to(project))
        if rel_dir == project or rel_dir.parent == rel_dir:
            return False, ""
        rel_dir = rel_dir.parent


def check_residue(project: Path, findings: list[Finding]) -> None:
    sdd = project / ".sdd"
    tmp = sdd / "tmp"
    if tmp.exists():
        leftovers = [p for p in tmp.rglob("*") if p.is_file()]
        if leftovers:
            findings.append(
                warn(
                    "residue.tmp",
                    f".sdd/tmp/ 有 {len(leftovers)} 个未清理文件（如 visual-research.md 属正常过程产物，其余应清理）",
                )
            )

    patch_like: list[str] = []
    for pattern in ("*.patch", "*.bak", "*.orig", "*.rej"):
        for path in project.rglob(pattern):
            if "node_modules" in path.parts or ".git" in path.parts:
                continue
            patch_like.append(str(path.relative_to(project)))
    if patch_like:
        findings.append(
            err(
                "residue.patch",
                f"存在临时补丁/备份文件 {len(patch_like)} 个：{', '.join(sorted(patch_like)[:5])}",
            )
        )

    env_files = [".env", ".env.local", ".env.production", ".env.development.local", ".env.production.local"]
    for name in env_files:
        for path in project.rglob(name):
            if "node_modules" in path.parts or ".git" in path.parts:
                continue
            rel = str(path.relative_to(project))
            covered, by = _gitignore_covers(project, path)
            if covered:
                findings.append(info("residue.env", f"{rel} 存在（已被 {by} 覆盖，属正常本地配置）"))
            else:
                findings.append(
                    err(
                        "residue.env_unignored",
                        f"{rel} 存在但未被任何 .gitignore 覆盖，存在密钥误提交风险",
                    )
                )


def check_mock_residue(project: Path, status_data: object, findings: list[Finding]) -> None:
    """`[Mock]` markers are legal during development, not after delivery."""
    stage = status_data.get("stage") if isinstance(status_data, dict) else None
    delivered = stage in {"completed", "development-complete", "delivered"}
    if not delivered:
        return
    hits = 0
    samples: list[str] = []
    for sub in ("frontend/src", "backend/src"):
        base = project / sub
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".py"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "[Mock]" in text:
                hits += 1
                if len(samples) < 3:
                    samples.append(str(path.relative_to(project)))
    if hits:
        findings.append(
            warn(
                "residue.mock_marker",
                f"项目状态为 {stage}，但仍有 {hits} 个源文件含 [Mock] 标记：{', '.join(samples)}",
            )
        )


def check_experience_size(project: Path, findings: list[Finding]) -> None:
    path = project / ".sdd" / "experience.md"
    if not path.exists():
        return
    size = path.stat().st_size
    if size > MAX_EXPERIENCE_BYTES:
        findings.append(
            err(
                "experience.oversize",
                f".sdd/experience.md 已 {size:,} 字节，超过 32KB 硬阈值，"
                f"须按 sdd-experience-governance 治理",
            )
        )
    elif size > WARN_EXPERIENCE_BYTES:
        findings.append(
            warn(
                "experience.warn",
                f".sdd/experience.md 已 {size:,} 字节，超过 20KB 预警线",
            )
        )


def check_reviews_gate(project: Path, status_data: object, findings: list[Finding]) -> None:
    """Delivered projects should have review reports; Blocker must be closed."""
    stage = status_data.get("stage") if isinstance(status_data, dict) else None
    reviews = project / ".sdd" / "reviews"
    has_reviews = reviews.exists() and any(reviews.glob("*.md"))
    if stage in {"completed", "development-complete", "delivered"} and not has_reviews:
        findings.append(
            info(
                "review.none",
                "项目已声明完成，但 .sdd/reviews/ 无审查报告（大改按规范应有 Code Review）",
            )
        )


def inspect_project(project_id: str) -> list[Finding]:
    findings: list[Finding] = []
    project = ROOT / "Projects_Repo" / project_id

    if not project.exists():
        findings.append(err("project.missing", f"项目目录不存在：Projects_Repo/{project_id}"))
        return findings

    sdd = project / ".sdd"
    if not sdd.exists():
        findings.append(err("project.uninitialized", f"Projects_Repo/{project_id}/.sdd 不存在，项目未初始化"))
        return findings

    project_data, f1 = read_json(sdd / "project.json")
    findings.extend(f1)
    tasks_data, f2 = read_json(sdd / "tasks.json")
    findings.extend(f2)
    status_data, f3 = read_json(sdd / "status.json")
    findings.extend(f3)

    if isinstance(project_data, dict):
        pid = project_data.get("id")
        if pid and pid != project_id:
            findings.append(err("project.id_mismatch", f"project.json id={pid!r} 与目录名 {project_id!r} 不一致"))

    tasks_summary = check_task_states(tasks_data, findings)
    check_plan_alignment(tasks_summary, project, findings)
    check_status_json(status_data, tasks_summary, findings)
    check_artifacts(project, findings)
    check_residue(project, findings)
    check_mock_residue(project, status_data, findings)
    check_experience_size(project, findings)
    check_reviews_gate(project, status_data, findings)

    findings.append(
        info(
            "summary",
            f"任务 {tasks_summary['passed']}/{tasks_summary['total']} passed；"
            f"状态分布 {tasks_summary['by_status']}",
        )
    )
    return findings


def emit_text(project_id: str, findings: list[Finding]) -> int:
    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]
    infos = [f for f in findings if f.level == "INFO"]

    print("=" * 62)
    print(f"项目状态巡检：{project_id}")
    print("=" * 62)
    for finding in errors:
        print(f"[ERROR] {finding.message}")
    for finding in warns:
        print(f"[WARN ] {finding.message}")
    for finding in infos:
        print(f"[INFO ] {finding.message}")
    if not findings:
        print("未发现问题。")
    print("-" * 62)
    verdict = "FAIL" if errors else ("WARN" if warns else "PASS")
    print(f"结果：{verdict}（ERROR {len(errors)} / WARN {len(warns)} / INFO {len(infos)}）")
    return 1 if errors else 0


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    use_all = "--all" in argv
    as_json = "--json" in argv
    positional = [a for a in argv if not a.startswith("-")]
    target = positional[0] if positional else None

    registry_findings: list[Finding] = []
    registry = scan_registry(registry_findings)
    scan_misplaced_dirs(registry_findings)

    project_ids = resolve_projects(registry, target, use_all)
    if not project_ids:
        registry_findings.append(
            err("registry.no_active", "project-registry.json 无 active_project_id，且未指定项目名")
        )

    results: dict[str, list[Finding]] = {}
    for pid in project_ids:
        results[pid] = inspect_project(pid)

    if as_json:
        payload = {
            "harness": [f.to_dict() for f in registry_findings],
            "projects": {pid: [f.to_dict() for f in fs] for pid, fs in results.items()},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if registry_findings:
            print("=" * 62)
            print("Harness 根目录检查")
            print("=" * 62)
            for finding in registry_findings:
                print(f"[{finding.level:5}] {finding.message}")
            print()
        for pid, findings in results.items():
            emit_text(pid, findings)
            print()

    has_error = any(f.level == "ERROR" for f in registry_findings) or any(
        f.level == "ERROR" for fs in results.values() for f in fs
    )
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
