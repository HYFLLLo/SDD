# SDD V7.1 Claude Code Adapter

本目录是 Claude Code 适配层，只做入口和 subagent 配置，不维护核心规则。

## 入口

- 根入口：`.claude/CLAUDE.md`
- 子智能体：`.claude/agents/*.md`（薄适配，指向 `harness-core/agents/*.md`）
- Claude 命令提示：仅 `.claude/commands/sdd-bugfix.md`

## 使用方式

在 Claude Code 中打开 Harness 根目录后：

1. 先读取 `.claude/CLAUDE.md`，它指向唯一入口 `harness-core/router.md`
2. 新建项目、需求对齐、开始开发、已有项目修整、导入已有项目和删除项目由 `harness-core/router.md` 根据自然语言意图分发
3. 只有用户明确触发 Bugfix 命令时，才读取 `.claude/commands/sdd-bugfix.md`

## 子智能体

提供三个薄适配器：

- `planner` → `harness-core/agents/planner.md`
- `developer` → `harness-core/agents/developer.md`
- `tester` → `harness-core/agents/tester.md`

满足 `harness-core/router.md`「开发门禁」后，用原生子智能体跑 Planner → Developer → Tester；编排与降级语义见 `harness-core/protocols/codex-subagents.md`。核心规则只维护在 `harness-core/`，不在本目录复制。
