# Platform Adapters

SDD Harness V7.1 uses one core and four thin platform adapters.

## Core

The only source of truth is:

```text
harness-core/
```

Core files contain platform-neutral rules for routing, product design, development loop, agents, skills, and dev standards.

## Codex

Codex entry files:

```text
AGENTS.md
.codex/README.md
.codex/config.toml
.codex/agents/planner.toml
.codex/agents/developer.toml
.codex/agents/tester.toml
.codex/commands/sdd-bugfix.md
```

Codex subagents are configured as TOML files. Their `developer_instructions` must only point to `harness-core/agents/*.md`.
Codex 只保留 `sdd-bugfix` 命令适配。新建项目、需求对齐、开始开发、已有项目修整和删除项目由 `harness-core/router.md` 根据自然语言意图分发。

If a Codex runtime does not support custom subagent TOML, follow:

```text
harness-core/protocols/codex-subagents.md
```

## Claude Code

Claude Code entry files:

```text
.claude/CLAUDE.md
.claude/agents/*.md
.claude/commands/sdd-bugfix.md
```

Claude files are adapters. They must only point to `harness-core/`.

Each `.claude/agents/*.md` must declare `name` (equal to the file stem), `description` and `model`, and point to `harness-core/agents/<role>.md`. `scripts/check_harness_consistency.py` enforces the required paths, the frontmatter contract and the resolvability of every cited `harness-core/` path.

Claude Code does not register `harness-core/skills/**` as platform skills; the Router reaches them by reading the files directly. Do not add core skill copies under `.claude/skills/` to "mirror" Cursor — a nested `SKILL.md` such as `.claude/skills/<workspace>/skill-snapshot/SKILL.md` is never discovered by the runtime and only risks drift.

## Cursor

Cursor entry files:

```text
.cursor/rules/*.mdc
.cursor/agents/*.md
.cursor/commands/sdd-bugfix.md
.cursor/skills/**
.cursor/dev-standards/*.mdc
```

Cursor files are adapters. They must only point to `harness-core/`.

Each `.cursor/agents/*.md` follows the same frontmatter contract as the Claude Code adapters: `name` (equal to the file stem), `description`, `model`, and a pointer to `harness-core/agents/<role>.md`. `.cursor/dev-standards/*.mdc` and `.cursor/skills/**/SKILL.md` are likewise thin pointers — never copies of the core file. `scripts/check_harness_consistency.py` enforces the required paths and the resolvability of every cited `harness-core/` path.

Cursor subagents are invoked via the Task tool, with `subagent_type` mapping to `.cursor/agents/*.md`. Their instructions must only point to `harness-core/agents/*.md`. The orchestration rules live in:

```text
harness-core/protocols/cursor-subagents.md
```

## WorkBuddy

WorkBuddy entry files:

```text
AGENTS.md
.workbuddy/README.md
.workbuddy/skills/sdd-harness/SKILL.md
.workbuddy/agents/planner.md
.workbuddy/agents/developer.md
.workbuddy/agents/tester.md
```

WorkBuddy subagents are declared as Markdown files with YAML frontmatter (`name`, `description`, `model`), mirroring the Claude Code adapter format. Critical difference: the runtime only discovers subagents from the **user-level** config dir (`~/.workbuddy/agents/`), not from the project-level `.workbuddy/agents/`. The in-repo copies are the version-controlled source and must be synced before use:

```text
python scripts/install_workbuddy_agents.py          # install / update
python scripts/install_workbuddy_agents.py --check  # verify only

python scripts/install_workbuddy_skill.py           # install / update entry skill
python scripts/install_workbuddy_skill.py --check   # verify only
```

The same restriction applies to skills: WorkBuddy discovers skills only from `<configDir>`, `<configDir>/skills`, the builtin plugin dir and `<configDir>/skills-marketplace` — never from the current workspace. So `.workbuddy/skills/sdd-harness/` is likewise a version-controlled source that must be installed to `~/.workbuddy/skills/sdd-harness/` to take effect.

Orchestration rules live in:

```text
harness-core/protocols/workbuddy-subagents.md
```

WorkBuddy 端只保留 `sdd-bugfix` 一个命令适配，位于 `.codebuddy/commands/sdd-bugfix.md`。新建项目、需求对齐、开始开发、已有项目修整、导入已有项目、删除项目由 `harness-core/router.md` 根据自然语言意图分发。

**为什么目录叫 `.codebuddy` 而不是 `.workbuddy`**：WorkBuddy 的项目级斜杠命令目录在客户端内被硬编码为 `.codebuddy/commands`（已实测确认），与其适配目录 `.workbuddy/` 不同名。另一可选位置是用户级 `<configDir>/commands`，但那会让 `/sdd-bugfix` 出现在所有无关项目的斜杠菜单中，因此选择项目级。

该命令文件同样是薄适配器，只允许：工作区校验、指向 `harness-core/commands/sdd-bugfix.md` 与对应 Skill、声明约束。不得复制修复流程正文。

`.workbuddy/skills/sdd-harness/SKILL.md` 是入口薄适配器，其正文只允许：指向 `harness-core/router.md`、声明平台约束、声明禁止项。不得包含路由判断、任务拆分、验收标准或开发规范。

由于该 Skill 安装到用户级后对**所有工作区可见**，其正文必须保留「阶段 0：工作区校验」：确认当前目录存在 `harness-core/router.md` 与 `AGENTS.md`，否则静默退出。`install_workbuddy_skill.py` 拒绝安装缺少该守卫的副本，`scripts/check_harness_consistency.py` 同步校验源文件。

强制约束：

1. `.workbuddy/skills/` 下不得出现 `harness-core/skills/**` 的流程副本。
2. `.workbuddy/memory/` 是宿主会话记忆，不得替代 `.sdd/experience.md` 与 `<harness 根>/memory/harness-experience.md`。
3. `.workbuddy/agents/*.md` 只允许声明 `name` / `description` / `model` / `category` / `version` / `tags` 与指向 `harness-core/agents/*.md` 的引用，不得复制 Agent 核心规则。
4. 若 WorkBuddy 无法拉起子智能体，先按 `workbuddy-subagents.md`「调用前置条件」排查用户级安装，仍失败才进入降级模式；不得改由主会话直接写功能代码。

## Project Directories

Managed projects under `Projects_Repo/<project-id>/` must not contain copied platform adapters:

```text
Projects_Repo/<project-id>/.cursor/
Projects_Repo/<project-id>/.claude/
Projects_Repo/<project-id>/.codex/
Projects_Repo/<project-id>/.workbuddy/
```

Project-local state belongs in:

```text
.sdd/
docs/
frontend/
backend/
mobile/
```
