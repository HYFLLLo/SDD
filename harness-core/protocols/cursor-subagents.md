# Cursor Subagents Protocol

本协议定义 SDD V7.1 在 Cursor 中使用 Planner / Developer / Tester 的方式。

## 目标

Cursor 适配必须保持三件事：

1. 核心规则只在 `harness-core/` 维护
2. Cursor 目录只做薄适配
3. 满足开发门禁后，必须用 Cursor 子智能体编排，而不是在主会话里直接写功能代码

## 子智能体配置

Cursor 子智能体适配器位于：

```text
.cursor/agents/planner.md
.cursor/agents/developer.md
.cursor/agents/tester.md
```

这些文件只允许声明：

- `name`
- `model`
- `description`
- 指向 `harness-core/agents/*.md` 的引用

不得在适配器中复制 Planner / Developer / Tester 核心规则。

## 调用方式

Cursor 通过 Task 工具拉起子智能体，`subagent_type` 与适配器一一对应：

```text
planner   -> .cursor/agents/planner.md   -> harness-core/agents/planner.md
developer -> .cursor/agents/developer.md -> harness-core/agents/developer.md
tester    -> .cursor/agents/tester.md    -> harness-core/agents/tester.md
```

进入开发阶段后，主会话默认承担 Orchestrator 角色，必须用 Task 子智能体执行 Planner / Developer / Tester，不得在主会话内直接写功能代码绕过角色边界。

每次拉起子智能体时，必须在 `prompt` 中明确传入：

- `active_project_id` 与 `active_project_path`
- 当前要处理的单个任务（来自 `.sdd/tasks.json`）
- 本会话已确认的运行时命令（`$PY` 解析结果）与端口约定
- 要求该子智能体先读取并严格执行对应的 `harness-core/agents/*.md`

子智能体之间不共享上下文，编排器必须把必要上下文显式写进每次 `prompt`。

## 编排器职责

Orchestrator（主会话）负责：

- 读取 `project-registry.json`
- 确定 `active_project_path`
- 读取 `.sdd/tasks.json` 的任务状态
- **开发开始时读取系统级经验 `<harness 根>/memory/harness-experience.md`，挑出相关教训传给 Planner**（经验回读环）
- 用 Task 调度 Planner / Developer / Tester
- 汇总 PASS / FAIL / BLOCKED
- **回传系统级经验**：收到带 `[SYSTEM]` 标注或 `## 系统级经验` 的产物后，追加到 `<harness 根>/memory/harness-experience.md`
- 维护用户门禁

经验链条完整定义见 `harness-core/protocols/development-rules.md`「经验沉淀链条」。

Orchestrator 禁止：

- 直接读业务代码细节
- 直接写功能代码
- 跳过 Tester
- 把业务文件写入 Harness 根目录

## 降级模式

如果当前 Cursor 环境不能用 Task 拉起自定义子智能体：

1. 主会话先声明当前模拟角色
2. 每个角色开始前读取对应 `harness-core/agents/*.md`
3. 每个角色只做自身职责
4. 角色切换时清楚说明输入和输出文件

降级模式仍必须遵守：

- Developer 一次只做一个任务
- Developer 不修改 `.sdd/tasks.json` 状态
- Tester 独立验证，不信任 Developer 声明
- Tester 只更新 status / notes，并写测试报告与 BUG 日志
- 真实 Key / Token / Secret 只能进入 `.env` 等配置文件

## Cursor 命令适配

Cursor 只保留一个手动命令适配：

```text
.cursor/commands/sdd-bugfix.md
```

Bugfix 命令只做路由提示，必须指向：

```text
harness-core/commands/sdd-bugfix.md
harness-core/skills/
harness-core/protocols/
```

不得在 `.cursor/commands/` 增加新建项目、需求对齐、开始开发、已有项目修整或删除项目命令。上述入口由 `harness-core/router.md` 根据自然语言意图分发。
