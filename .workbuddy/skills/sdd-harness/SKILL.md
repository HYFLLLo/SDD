---
name: sdd-harness
description: SDD Harness V7.1 在 WorkBuddy 环境下的入口适配器。仅在当前工作区根目录存在 harness-core/router.md（即 SDD Harness 仓库根）时生效，其他工作区必须完全忽略本 Skill。在 SDD Harness 工作区内，当用户提出新建项目、从零做一个应用、修改/继续已有 SDD 项目、导入已有代码库、删除项目、修 Bug、业务口径对齐、代码审查、整理经验与复盘、重构或还技术债、发布上线交付、项目状态巡检、进入开发阶段或继续多智能体开发时，加载本 Skill，由它把控制权交给 harness-core/router.md。关键词：SDD Harness、SDD 项目、新建项目、导入项目、删除项目、开始开发、多智能体开发、Planner、Developer、Tester、Bugfix、代码审查、code review、场景对齐、经验治理、整理经验、复盘、重构、技术债、解耦、发布、上线、部署、交付、回滚、项目状态检查。
---

# SDD V7.1 — WorkBuddy Adapter

本文件是**薄适配器**，只做一件事：把控制权交给唯一入口。

## 阶段 0：工作区校验（最先执行，不可跳过）

本 Skill 安装在用户级技能目录（`~/.workbuddy/skills/`），对所有 WorkBuddy 工作区**全局可见**。因此加载后的第一件事，是确认当前工作区确实是 SDD Harness 根目录：

```bash
test -f harness-core/router.md && test -f AGENTS.md
```

- **两者都存在** → 确认是 SDD Harness 根目录，继续执行下面的「强制启动顺序」。
- **任一不存在** → **立即停止**。不要提及 SDD、不要读取任何 `harness-core/` 路径、不要改变用户的原始任务，按用户原话正常作答。这是一个普通项目，本 Skill 不适用。

> 校验失败时静默退出，是本 Skill 的硬约束。它对所有工作区可见，只有工作区形态满足条件时才允许接管路由。

## 强制启动顺序

被本 Skill 触发后，你的下一步动作必须是：

1. Read `harness-core/router.md`
2. 严格按该文件执行项目级意图路由

不得跳过这一步直接开始写代码、写文档或创建目录。`harness-core/router.md` 是 SDD V7.1 的唯一真相源，本文件不复制其中任何流程。

## WorkBuddy 平台约束

- **子智能体**：进入开发阶段后，按 `harness-core/protocols/workbuddy-subagents.md` 用 Agent 工具拉起隔离上下文的 Planner / Developer / Tester，主会话承担 Orchestrator，**不得在主会话内直接写功能代码绕过角色边界**。
- **技能路由**：`harness-core/skills/` 下的 SKILL.md 是核心流程，需要时直接 Read 并按其中步骤执行；不要因为 WorkBuddy 自身也有 Skill 机制就改用 `.workbuddy/skills/` 下的副本来承载 SDD 流程。
- **记忆边界**：WorkBuddy 会在 `.workbuddy/memory/` 写工作日志，这与 SDD 的两级经验体系**不是同一套**。SDD 经验仍按 `harness-core/protocols/development-rules.md`「经验沉淀链条」写入 `Projects_Repo/<id>/.sdd/experience.md` 与 `<harness 根>/memory/harness-experience.md`，二者不得互相替代。
- **路径约束**：所有业务文件只写入 `Projects_Repo/<active_project_id>/`；发现 `docs/`、`.sdd/`、`frontend/`、`backend/` 出现在 Harness 根目录时，先停止并按 Router「路径解析规则」提示迁移。

## 禁止

- 不在 `.workbuddy/` 内维护 SDD 核心流程、Agent 规则或开发规范。
- 不把 `.workbuddy/memory/` 当作 SDD 项目经验或系统经验的存放位置。
- 不在 `Projects_Repo/<project-id>/` 内复制 `.workbuddy/` 适配层。
