# SDD Harness V7.1 — Claude Code Entry

你是 SDD Harness V7.1 在 Claude Code 环境下的入口。

核心规则只允许维护在 `harness-core/`。`.claude/` 目录只做 Claude Code 适配。

## 启动顺序

处理任何项目管理、产品设计、已有项目修整、删除项目、Bugfix 或开发任务前，先读取唯一入口：

1. `harness-core/router.md`

`development-rules.md` 等其余规范由 `router.md` 在进入对应阶段时按需路由读取，不在启动时预读。

## Agents

Claude Code agent 适配器位于：

```text
.claude/agents/planner.md
.claude/agents/developer.md
.claude/agents/tester.md
```

这些文件只引用：

```text
harness-core/agents/*.md
```

不要在 `.claude/agents/` 里维护核心规则。

## 子智能体与开发

进入开发阶段（满足 `harness-core/router.md`「开发门禁」后）：

- Claude Code 用原生 `.claude/agents/*.md` 子智能体执行 Planner → Developer → Tester，主会话承担 Orchestrator，不在主会话直接写功能代码绕过角色边界。
- 子智能体编排与降级语义遵循 `harness-core/protocols/codex-subagents.md`（跨平台通用）。
- 开发与经验规则见 `harness-core/protocols/development-rules.md`，其中「经验沉淀链条」定义项目级 `.sdd/experience.md` 与系统级 `<harness 根>/memory/harness-experience.md` 的写回与回读闭环。

## Commands

Claude Code 只保留一个手动 command 适配器：

```text
.claude/commands/sdd-bugfix.md
```

新建项目、需求对齐、开始开发、已有项目修整、导入已有项目和删除项目都不通过手动命令触发，必须由 `harness-core/router.md` 根据用户自然语言意图进入对应 Skill。
