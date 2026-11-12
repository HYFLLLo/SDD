# SDD V7 Codex Adapter

本目录是 Codex 适配层，只做入口和 subagent 配置，不维护核心规则。

## 入口

- 根入口：`AGENTS.md`
- Codex 配置：`.codex/config.toml`
- 子智能体：`.codex/agents/*.toml`
- Codex 命令提示：仅 `.codex/commands/sdd-bugfix.md`

## 使用方式

在 Codex 中打开 Harness 根目录后：

1. 先读取 `AGENTS.md`
2. 新建项目、需求对齐、开始开发、已有项目修整、导入已有项目和删除项目由 `harness-core/router.md` 根据自然语言意图分发
3. 只有用户明确触发 Bugfix 命令时，才读取 `.codex/commands/sdd-bugfix.md`

## 子智能体

当前提供三个薄适配器：

- `planner` → `harness-core/agents/planner.md`
- `developer` → `harness-core/agents/developer.md`
- `tester` → `harness-core/agents/tester.md`

如果当前 Codex 环境不支持自定义 subagent TOML，按 `harness-core/protocols/codex-subagents.md` 在主会话中模拟三角色边界。
