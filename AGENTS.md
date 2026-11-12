# SDD Harness V7.1 — 统一入口（Codex / Claude Code / Cursor / WorkBuddy）

你是 SDD Harness V7.1 在当前宿主平台下的入口。本文件是**平台中立**入口，不再绑定单一平台。

本项目支持四端使用：Codex、Claude Code、Cursor、WorkBuddy。核心规则只允许维护在 `harness-core/`，平台目录只做适配。

## 启动顺序

处理任何项目管理、产品设计、已有项目修整、删除项目、Bugfix 或开发任务前，先读取唯一入口：

1. `harness-core/router.md`

`development-rules.md`、`platform-adapters.md` 及各平台子智能体协议等其余规范，由 `router.md` 在进入对应阶段时按需路由读取，不在启动时预读。

## 平台自识别

进入 Router 后，按当前宿主平台选择对应的子智能体协议。**不要假设自己一定是 Codex。**

| 宿主平台 | 入口文件（已自动加载） | 子智能体协议 |
|----------|------------------------|--------------|
| WorkBuddy | `AGENTS.md` + `sdd-harness` SKILL（需已安装到用户级） | `harness-core/protocols/workbuddy-subagents.md` |
| Codex | `AGENTS.md` + `.codex/config.toml` | `harness-core/protocols/codex-subagents.md` |
| Claude Code | `.claude/CLAUDE.md` | `harness-core/protocols/codex-subagents.md`（编排与降级语义通用） |
| Cursor | `.cursor/rules/00-harness-router.mdc` | `harness-core/protocols/cursor-subagents.md` |

判断依据：能调用 Agent 工具拉起隔离上下文的子智能体时按 WorkBuddy / Cursor 协议执行；只能声明自定义 subagent TOML 时按 Codex 协议执行；仅能通过文件形式声明子智能体时按 Claude Code 协议执行。

若无法确定平台，或当前环境不支持任何形式的子智能体调度，按对应协议进入**降级模式**：主会话逐角色声明、逐角色读取 `harness-core/agents/*.md`，但不得抹平 Planner / Developer / Tester 的角色边界。

## 平台命令适配

各平台只保留一个手动命令适配，且只做路由提示：

```text
.codex/commands/sdd-bugfix.md
.claude/commands/sdd-bugfix.md
.cursor/commands/sdd-bugfix.md
.codebuddy/commands/sdd-bugfix.md   # WorkBuddy 的项目级命令目录名
```

新建项目、需求对齐、开始开发、已有项目修整、导入已有项目和删除项目，在**所有平台**都不通过手动命令触发，必须由 `harness-core/router.md` 根据用户自然语言意图进入对应 Skill。

Bugfix 命令只负责路由到 `harness-core/commands/sdd-bugfix.md`，不得维护核心流程。

## 子智能体与开发

当用户说"开始开发 / 进入开发阶段 / 继续多智能体开发"时，视为明确授权使用子智能体的情形之一；除此之外，按 `harness-core/router.md`「开发循环启用判断」主动判断复杂度与风险：大改 / 复杂需求可不必等这些关键词而启用，小改 / 中间改可直接执行、不强制启动子智能体。

开发阶段由三个角色承担：

- `planner`
- `developer`
- `tester`

按 `harness-core/router.md`、`harness-core/protocols/development-rules.md` 和当前平台对应的子智能体协议推进。若当前宿主环境不支持子智能体调度，在主会话中模拟三个角色，但必须保持角色边界。

## 路径原则

业务文件只能写入当前活动项目：

```text
Projects_Repo/<active_project_id>/
```

不得把业务 `docs/`、`.sdd/`、`frontend/`、`backend/`、`mobile/`、`pycore/` 写到 Harness 根目录。

## 核心规则位置

- Router：`harness-core/router.md`
- 开发全局规则：`harness-core/protocols/development-rules.md`
- 平台适配层边界：`harness-core/protocols/platform-adapters.md`
- WorkBuddy 子智能体协议：`harness-core/protocols/workbuddy-subagents.md`
- Codex 子智能体协议：`harness-core/protocols/codex-subagents.md`
- Cursor 子智能体协议：`harness-core/protocols/cursor-subagents.md`
- 开发循环：由 `harness-core/router.md` 和 `harness-core/protocols/development-rules.md` 触发
- Planner：`harness-core/agents/planner.md`
- Developer：`harness-core/agents/developer.md`
- Tester：`harness-core/agents/tester.md`
- 经验沉淀链条：`harness-core/protocols/development-rules.md`「经验沉淀链条」（系统级 `<harness 根>/memory/harness-experience.md` + 项目级 `.sdd/experience.md`）
- 产品设计（新建）：`harness-core/skills/sdd-product-design/SKILL.md`
- 已有项目修整：`harness-core/skills/sdd-project-maintenance/SKILL.md`
- 导入已有项目：`harness-core/skills/sdd-project-import/SKILL.md`
- 删除项目：`harness-core/skills/sdd-project-delete/SKILL.md`
- Bugfix：`harness-core/skills/sdd-bugfix/SKILL.md`
- 场景对齐：`harness-core/skills/alignment/SKILL.md`
- 代码审查：`harness-core/skills/sdd-code-review/SKILL.md`（Tester PASS 后、`user_gate` 前；只报不改，Blocker 未关闭不得放行）
- 经验治理：`harness-core/skills/sdd-experience-governance/SKILL.md`（经验文件超 32KB / 同类问题第 3 次 / 交付前 / 每 5 个任务；只维护不写入，禁止无依据删除）
- 重构专项：`harness-core/skills/sdd-refactor/SKILL.md`（行为不变的结构调整；无回归基线不开工，不得与功能变更混批）
- 发布交付：`harness-core/skills/sdd-release/SKILL.md`（交付前检查单、`startup.md` 与 `manual-checklist.md` 定稿、tag 与 release note、回滚方案；不擅自执行部署）
- 项目状态巡检：`scripts/check_project_state.py`（只读，报编码/BOM、任务状态机、Plan 与 tasks 一致性、残留文件、`.env*` 未忽略、`[Mock]` 残留、经验容量、审查缺失）

## 禁止

- 不要在本文件或任何平台适配器中维护 SDD 核心流程，只能写入口适配。
- 不要在平台命令目录增加新建、对齐、开始开发、修整或删除命令；这些入口由 Router 自然语言分发。
- 不要把某一个平台的适配规则复制到核心层，也不要把 `.cursor/`、`.claude/`、`.codex/`、`.workbuddy/` 的适配说明当作核心规则。
- 不要在 `Projects_Repo/<project-id>/` 内复制任何平台适配层，避免规则漂移。
- 不要把项目内依赖安装交给用户手动执行。

---

# SDD V7.1 入口路由

开始任何 SDD 项目工作前，必须先读取 `harness-core/router.md`，并判断用户的项目级意图：

1. 新建项目：进入现有新建项目 SDD 流程（`harness-core/skills/sdd-product-design/SKILL.md`）。
2. 已有项目修整：进入 `harness-core/skills/sdd-project-maintenance/SKILL.md`。Bug 修复不走此分支，转 `harness-core/skills/sdd-bugfix/SKILL.md`。
3. 导入已有项目：进入 `harness-core/skills/sdd-project-import/SKILL.md`。
4. 删除项目：进入 `harness-core/skills/sdd-project-delete/SKILL.md`。
5. 业务口径对齐：进入 `harness-core/skills/alignment/SKILL.md`。这是分支 1 / 2 的前置可选步，对齐完成后回到对应分支继续。

选择项目级分支之前，不要直接进入前端、后端、原型或测试。如果意图不清楚，只问：`你是要新建项目、修改已有的 SDD 项目、导入一个已有代码库，删除项目，还是先对齐一下业务口径？`

---
