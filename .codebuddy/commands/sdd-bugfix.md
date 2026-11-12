---
description: SDD Bugfix — 修复开发过程中遇到的 BUG，产出修复报告并回写项目经验
argument-hint: <问题描述>
---

# /sdd-bugfix — WorkBuddy 适配器

本文件是**薄适配器**，不复制核心流程，只把控制权交给唯一入口。

## 工作区校验（最先执行）

本命令仅在 SDD Harness 仓库内有效。执行前先确认当前工作区根目录存在：

```bash
test -f harness-core/router.md && test -f AGENTS.md
```

- **两者都存在** → 继续执行下面的流程。
- **任一不存在** → 立即停止，告知用户此命令只在 SDD Harness 工作区可用，不要凭空创建 `.sdd/` 目录。

## 执行顺序

1. Read `harness-core/router.md`
2. Read `harness-core/commands/sdd-bugfix.md` 并严格执行
3. 按 `harness-core/skills/sdd-bugfix/SKILL.md` 执行修复流程

用户的原始问题描述（`$ARGUMENTS`）必须完整记录，不得改写或省略。

## 约束

- 修复报告写入 `Projects_Repo/<active_project_id>/.sdd/bug_fix/`
- 经验回写 `Projects_Repo/<active_project_id>/.sdd/experience.md`
- 若 Bug 涉及产品口径，先进入 `harness-core/skills/alignment/SKILL.md` 对齐
- 修复报告不得泄露真实 Key / Token / Secret
- 不得随意修改 `.sdd/tasks.json` 状态，除非用户明确要求

> 核心规则只允许维护在 `harness-core/commands/sdd-bugfix.md` 与 `harness-core/skills/sdd-bugfix/SKILL.md`。
