#!/usr/bin/env python3
"""Tiny project manager for SDD V7.1.

This script intentionally uses only the Python standard library so students can
inspect and run it without installing dependencies.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ROOT / "Projects_Repo"
REGISTRY_PATH = ROOT / "project-registry.json"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_registry() -> dict:
    return {
        "version": 1,
        "projects_root": "Projects_Repo",
        "active_project_id": None,
        "projects": [],
    }


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return default_registry()
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry.setdefault("version", 1)
    registry.setdefault("projects_root", "Projects_Repo")
    registry.setdefault("active_project_id", None)
    registry.setdefault("projects", [])
    return registry


def save_registry(registry: dict) -> None:
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def get_project(registry: dict, project_id: str) -> dict | None:
    return next((p for p in registry.get("projects", []) if p["id"] == project_id), None)


def ensure_project_dirs(project_dir: Path) -> None:
    for rel in [
        ".sdd",
        ".sdd/test-reports",
        ".sdd/reviews",
        ".sdd/experience-audit",
        ".sdd/bug-logs",
        ".sdd/bug_fix",
        ".sdd/release",
        ".sdd/refactor",
        ".sdd/tmp",
        "docs",
        "docs/prototypes",
        "docs/澄清文档",
    ]:
        (project_dir / rel).mkdir(parents=True, exist_ok=True)


def copy_harness(project_dir: Path) -> None:
    """Copy project runtime scaffolding.

    Platform adapters (.cursor/.claude/.codex) stay in the Harness root.
    Copying them into every managed project causes rule drift.
    """
    for name in ["pycore"]:
        src = ROOT / name
        dst = project_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        shutil.copy2(pyproject, project_dir / "pyproject.toml")


def write_project_entrypoints(project_dir: Path) -> None:
    """Write lightweight project-local entrypoints for users who open a project directly."""
    agents = project_dir / "AGENTS.md"
    if not agents.exists():
        agents.write_text(
            """# Managed Project Entry

This project is managed by SDD Harness V7.1.

Recommended workflow: open the Harness root, not this project folder:

```text
../../
```

Core rules live in:

```text
../../harness-core/
```

Project files live here:

```text
.sdd/
docs/
frontend/
backend/
```

Do not create local `.cursor/`, `.claude/`, or `.codex/` rule copies inside this project unless the Harness explicitly asks for it.
""",
            encoding="utf-8",
        )


def init_sdd_files(project_dir: Path, project_id: str, name: str, project_type: str, source: str, repo_url: str | None) -> None:
    ensure_project_dirs(project_dir)

    project_json = project_dir / ".sdd/project.json"
    if not project_json.exists():
        project_json.write_text(
            json.dumps(
                {
                    "id": project_id,
                    "name": name,
                    "project_type": project_type,
                    "source": source,
                    "repo_url": repo_url,
                    "created_at": now(),
                    "last_active": now(),
                    "harness_version": "V7.1",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    status_json = project_dir / ".sdd/status.json"
    if not status_json.exists():
        status_json.write_text(
            json.dumps(
                {
                    "stage": "initialized",
                    "mode": source,
                    "design_ready": False,
                    "development_ready": False,
                    "current_task": None,
                    "blocked": False,
                    "notes": "",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    for filename in ["experience.md", "work-log.md"]:
        dst = project_dir / ".sdd" / filename
        if not dst.exists():
            template = ROOT / "templates/project/.sdd" / filename
            dst.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    readme = project_dir / "README.md"
    if not readme.exists():
        template = ROOT / "templates/project/README.md"
        readme.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")

    write_project_entrypoints(project_dir)


def run_git(project_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=project_dir,
        text=True,
        capture_output=True,
        check=False,
    )


def init_git_repo(project_dir: Path, repo_url: str | None = None) -> None:
    """Initialize a project-local Git repo without relying on Developer."""
    if shutil.which("git") is None:
        print("Warning: git command not found; skipped Git initialization.")
        return

    if (project_dir / ".git").exists():
        print("Git repository already exists; skipped init.")
    else:
        init_result = run_git(project_dir, "init", "-b", "main")
        if init_result.returncode != 0:
            init_result = run_git(project_dir, "init")
        if init_result.returncode != 0:
            print(f"Warning: git init failed: {init_result.stderr.strip()}")
            return

    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "\n".join(
                [
                    ".env",
                    ".env.*",
                    "!.env.example",
                    "__pycache__/",
                    "*.py[cod]",
                    ".pytest_cache/",
                    ".mypy_cache/",
                    "node_modules/",
                    "dist/",
                    "build/",
                    ".DS_Store",
                    "logs/",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if repo_url:
        remotes = run_git(project_dir, "remote")
        remote_names = set(remotes.stdout.split()) if remotes.returncode == 0 else set()
        if "origin" in remote_names:
            set_url = run_git(project_dir, "remote", "set-url", "origin", repo_url)
            if set_url.returncode != 0:
                print(f"Warning: git remote set-url failed: {set_url.stderr.strip()}")
        else:
            add_remote = run_git(project_dir, "remote", "add", "origin", repo_url)
            if add_remote.returncode != 0:
                print(f"Warning: git remote add failed: {add_remote.stderr.strip()}")

    run_git(project_dir, "add", ".gitignore")
    user_name = run_git(project_dir, "config", "user.name")
    user_email = run_git(project_dir, "config", "user.email")
    if user_name.returncode != 0 or user_email.returncode != 0:
        print("Git initialized. Initial commit skipped because user.name/user.email is not configured.")
        return

    commit = run_git(project_dir, "commit", "-m", "chore: init repository")
    if commit.returncode != 0:
        print(f"Git initialized. Initial commit skipped: {commit.stderr.strip()}")


def register_project(project_id: str, name: str, project_type: str, source: str, repo_url: str | None = None, activate: bool = True) -> None:
    registry = load_registry()
    projects = registry.setdefault("projects", [])
    rel_path = f"Projects_Repo/{project_id}"

    existing = get_project(registry, project_id)
    payload = {
        "id": project_id,
        "name": name,
        "path": rel_path,
        "source": source,
        "repo_url": repo_url,
        "project_type": project_type,
        "status": "initialized",
        "created_at": existing.get("created_at") if existing else now(),
        "last_active": now(),
    }

    if existing:
        existing.update(payload)
    else:
        projects.append(payload)

    if activate:
        registry["active_project_id"] = project_id
    save_registry(registry)


def set_active_project(project_id: str) -> dict:
    registry = load_registry()
    project = get_project(registry, project_id)
    if not project:
        raise SystemExit(f"Project not found: {project_id}")

    project_dir = ROOT / project["path"]
    if not (project_dir / ".sdd/project.json").exists():
        raise SystemExit(f"Project is not initialized: {project_dir}")

    registry["active_project_id"] = project_id
    project["last_active"] = now()
    save_registry(registry)
    return project


def write_project_repo_url(project_dir: Path, repo_url: str | None) -> None:
    project_json = project_dir / ".sdd/project.json"
    if not project_json.exists():
        return
    data = json.loads(project_json.read_text(encoding="utf-8"))
    data["repo_url"] = repo_url
    data["last_active"] = now()
    project_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def active_project(registry: dict | None = None) -> dict | None:
    registry = registry or load_registry()
    active_id = registry.get("active_project_id")
    if not active_id:
        return None
    return get_project(registry, active_id)


def cmd_new(args: argparse.Namespace) -> None:
    project_dir = PROJECTS_ROOT / args.id
    project_dir.mkdir(parents=True, exist_ok=True)
    copy_harness(project_dir)
    init_sdd_files(project_dir, args.id, args.name, args.type, "new", args.repo_url)
    init_git_repo(project_dir, args.repo_url)
    register_project(args.id, args.name, args.type, "new", repo_url=args.repo_url, activate=True)
    print(f"Project created: {project_dir}")
    print(f"Active project: {args.id}")
    print(f"active_project_path: Projects_Repo/{args.id}/")
    if args.repo_url:
        print(f"repo_url: {args.repo_url}")


def cmd_use(args: argparse.Namespace) -> None:
    project = set_active_project(args.id)
    print(f"Active project: {project['id']}")
    print(f"active_project_path: {project['path']}/")


def cmd_current(_: argparse.Namespace) -> None:
    registry = load_registry()
    project = active_project(registry)
    if not project:
        print("No active project. Use `python scripts/sdd_project.py list` then `python scripts/sdd_project.py use <id>`.")
        return
    print(f"Active project: {project['id']}")
    print(f"Name: {project['name']}")
    print(f"Type: {project['project_type']}")
    print(f"Status: {project['status']}")
    print(f"Repo URL: {project.get('repo_url') or '(not set)'}")
    print(f"active_project_path: {project['path']}/")


def cmd_repo_url(args: argparse.Namespace) -> None:
    registry = load_registry()
    project_id = args.id or registry.get("active_project_id")
    if not project_id:
        raise SystemExit("No project selected. Pass --id <project-id> or set an active project first.")

    project = get_project(registry, project_id)
    if not project:
        raise SystemExit(f"Project not found: {project_id}")

    project_dir = ROOT / project["path"]
    repo_url = args.url
    project["repo_url"] = repo_url
    project["last_active"] = now()
    save_registry(registry)
    write_project_repo_url(project_dir, repo_url)

    if args.configure_git:
        init_git_repo(project_dir, repo_url)

    print(f"Project repo_url updated: {project_id}")
    print(f"repo_url: {repo_url}")


def cmd_import(args: argparse.Namespace) -> None:
    """Onboard an existing (possibly non-SDD) project under Projects_Repo/<id>.

    Does NOT overwrite existing business files. Only adds the missing `.sdd/`
    scaffolding (project.json / status.json / experience.md / work-log.md) and a
    registry entry, then sets the project active. pycore is NOT copied over an
    existing codebase to avoid clobbering the user's own backend layout.
    """
    project_dir = PROJECTS_ROOT / args.id
    if not project_dir.exists():
        raise SystemExit(
            f"Project directory not found: {project_dir}\n"
            f"Place or clone the existing codebase at {project_dir} first, then run import."
        )

    init_sdd_files(project_dir, args.id, args.name, args.type, "import", args.repo_url)
    if args.configure_git:
        init_git_repo(project_dir, args.repo_url)
    register_project(args.id, args.name, args.type, "import", repo_url=args.repo_url, activate=True)
    print(f"Project imported: {project_dir}")
    print(f"Active project: {args.id}")
    print(f"active_project_path: Projects_Repo/{args.id}/")
    print("Note: existing business files were left untouched; only .sdd/ scaffolding was added if missing.")


def cmd_delete(args: argparse.Namespace) -> None:
    """Remove a project from the registry and (by default) delete its directory.

    Safety: requires --yes. Clears active_project_id if it pointed to this
    project. Does not touch any remote Git repository. Never deletes parent dirs.
    """
    registry = load_registry()
    project = get_project(registry, args.id)
    project_dir = PROJECTS_ROOT / args.id

    if not project and not project_dir.exists():
        raise SystemExit(f"Project not found in registry or on disk: {args.id}")

    if not args.yes:
        raise SystemExit(
            f"Refusing to delete '{args.id}' without --yes.\n"
            f"Target dir: {project_dir}\n"
            f"Registry entry: {'yes' if project else 'no'}\n"
            f"Re-run with --yes to confirm (add --keep-files to only unregister)."
        )

    if project:
        registry["projects"] = [p for p in registry.get("projects", []) if p["id"] != args.id]
    if registry.get("active_project_id") == args.id:
        registry["active_project_id"] = None
        print(f"Cleared active_project_id (was '{args.id}').")
    save_registry(registry)

    if not args.keep_files and project_dir.exists():
        resolved = project_dir.resolve()
        if resolved.parent != PROJECTS_ROOT.resolve():
            raise SystemExit(f"Refusing to delete unexpected path: {resolved}")
        shutil.rmtree(resolved)
        print(f"Deleted project directory: {project_dir}")
    elif args.keep_files:
        print(f"Kept project files on disk: {project_dir}")

    print(f"Project unregistered: {args.id}")


def cmd_list(_: argparse.Namespace) -> None:
    registry = load_registry()
    active_id = registry.get("active_project_id")
    for project in registry.get("projects", []):
        marker = "*" if project["id"] == active_id else " "
        repo_url = project.get("repo_url") or "-"
        print(f"{marker} {project['id']}	{project['project_type']}	{project['status']}	{project['path']}	{repo_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDD V7.1 project manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    new = sub.add_parser("new", help="Create a new managed project and set it active")
    new.add_argument("id", help="project id, e.g. customer-service")
    new.add_argument("--name", required=True, help="human-readable project name")
    new.add_argument("--type", default="unknown", choices=["web", "mobile", "unknown"])
    new.add_argument("--repo-url", default=None, help="remote Git repository URL for this project")
    new.set_defaults(func=cmd_new)

    use = sub.add_parser("use", help="Set active project")
    use.add_argument("id", help="project id")
    use.set_defaults(func=cmd_use)

    current = sub.add_parser("current", help="Show active project")
    current.set_defaults(func=cmd_current)

    repo_url = sub.add_parser("repo-url", help="Set remote Git repository URL for a project")
    repo_url.add_argument("url", help="remote Git repository URL")
    repo_url.add_argument("--id", default=None, help="project id; defaults to active project")
    repo_url.add_argument(
        "--configure-git",
        action="store_true",
        help="also configure git remote origin in the project repository",
    )
    repo_url.set_defaults(func=cmd_repo_url)

    import_cmd = sub.add_parser("import", help="Onboard an existing project dir under Projects_Repo/<id>")
    import_cmd.add_argument("id", help="project id; the dir Projects_Repo/<id> must already exist")
    import_cmd.add_argument("--name", required=True, help="human-readable project name")
    import_cmd.add_argument("--type", default="unknown", choices=["web", "mobile", "unknown"])
    import_cmd.add_argument("--repo-url", default=None, help="remote Git repository URL for this project")
    import_cmd.add_argument(
        "--configure-git",
        action="store_true",
        help="initialize/attach a git repo in the imported project if missing",
    )
    import_cmd.set_defaults(func=cmd_import)

    delete_cmd = sub.add_parser("delete", help="Unregister a project and delete its directory")
    delete_cmd.add_argument("id", help="project id")
    delete_cmd.add_argument("--yes", action="store_true", help="confirm destructive deletion")
    delete_cmd.add_argument(
        "--keep-files",
        action="store_true",
        help="only remove the registry entry, keep files on disk",
    )
    delete_cmd.set_defaults(func=cmd_delete)

    list_cmd = sub.add_parser("list", help="List registered projects")
    list_cmd.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
