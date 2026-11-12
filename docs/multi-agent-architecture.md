# SDD V7.1 多智能体协作架构

> 本文档描述 SDD Harness V7.1 的 Planner / Developer / Tester 多智能体协作机制，覆盖 Cursor、Codex、Claude Code、WorkBuddy 四个平台适配器。
> 单一权威源为 `harness-core/`，平台目录只做薄适配。

## 1. 架构定位

SDD V7.1 采用 **一份核心、四端适配** 的结构：

```text
harness-core/         跨平台核心规则（唯一权威源）
.cursor/              Cursor 入口与 subagent 适配
.codex/               Codex 入口与 subagent 适配
.claude/              Claude Code 入口与 subagent 适配
.workbuddy/           WorkBuddy 入口适配（无静态 subagent 文件）
Projects_Repo/<id>/   当前活动项目的业务文件
```

核心原则：

- 跨平台通用的路由、产品设计、开发循环、Agent、Skill、开发规范只维护在 `harness-core/`。
- `.cursor/`、`.codex/`、`.claude/`、`.workbuddy/` 只能维护入口适配和子智能体声明，不得复制完整核心流程。
- 业务文件只能写入 `Projects_Repo/<active_project_id>/`，不得写入 Harness 根目录。

## 2. 四端入口契约

四端最终都收敛到同一个 Router：

| 平台 | 入口文件 | 路由链 | 子智能体协议 |
|------|----------|--------|--------------|
| Cursor | `.cursor/rules/00-harness-router.mdc` | `.cursor/rules/00-harness-router.mdc -> harness-core/router.md` | `harness-core/protocols/cursor-subagents.md` |
| Codex | `AGENTS.md` | `AGENTS.md -> harness-core/router.md` | `harness-core/protocols/codex-subagents.md` |
| Claude Code | `.claude/CLAUDE.md` | `.claude/CLAUDE.md -> harness-core/router.md` | `harness-core/protocols/codex-subagents.md`（编排与降级语义通用） |
| WorkBuddy | `AGENTS.md` + `sdd-harness` SKILL（仓库内为源，需安装到用户级生效） | `AGENTS.md / sdd-harness SKILL -> harness-core/router.md` | `harness-core/protocols/workbuddy-subagents.md` |

## 3. 总体协作流程

```text
用户自然语言意图
        |
        v
harness-core/router.md
        |
        | 新建 / 修整 / 导入 / 删除
        v
对应 Skill -> 产出 PRD / api-contracts / Plan / prototypes / tasks.json
        |
        | 满足开发门禁
        v
主会话 Orchestrator
        |
        +-- Planner  -> .sdd/tasks.json
        |
        +-- Developer <---> Tester
        |       ^              |
        |       +--- FAIL 重试 --+
        |
        +-- Code Review（Tester PASS 后 / user_gate 前，只报不改）
        |       ^              |
        |       +-- Blocker 修复 -+
        |
        +-- 用户门禁 / 最终交付
```

进入开发后，主会话承担 **Orchestrator**，不直接写功能代码；子智能体按 `Planner -> Developer -> Tester -> Code Review` 编排，或由 Developer / Tester / Code Review 形成修复循环。

Code Review 不是第四个子智能体，而是 Orchestrator 在 Tester PASS 后按 `harness-core/skills/sdd-code-review/SKILL.md` 执行的审查环节；它只报不改，问题清单回到 Developer 修。详见 §8.1。

## 4. 角色与职责

### 4.1 核心角色

核心角色定义在 `harness-core/agents/`，不绑定任何平台和模型：

| 角色 | 核心文件 | 职责 | 主要输入 | 主要输出 |
|------|----------|------|----------|----------|
| Planner | `harness-core/agents/planner.md` | 技术方案设计和任务拆分 | `docs/PRD.md`、`docs/Plan.md`、`docs/api-contracts.md`、系统级经验 | `.sdd/tasks.json` |
| Developer | `harness-core/agents/developer.md` | 按单任务实现代码、积累经验 | 单个任务定义、`rules_files`、项目经验 | 修改/新增代码文件路径 |
| Tester | `harness-core/agents/tester.md` | 独立验证 Developer 成果 | `acceptanceCriteria`、代码文件、测试报告 | 测试报告 + BUG 日志 + `tasks.json` 状态更新 |
| Orchestrator | 由主会话承担 | 调度三角色、维护门禁与状态、回传系统经验 | `project-registry.json`、`.sdd/tasks.json`、子智能体返回 | 调度结果、用户门禁、经验回传 |

### 4.2 平台模型映射

模型是**平台适配层**的配置，不属于核心规则。当前仓库中的实际声明如下：

| 角色 | Cursor | Claude Code | Codex | WorkBuddy |
|------|--------|-------------|-------|-----------|
| Planner | `composer-2.5[fast=false]` | `sonnet` | `EB-DeepSeek-Flash` | `EB-DeepSeek-Flash` |
| Developer | `claude-sonnet-4-5` | `opus` | `EB-DeepSeek-Flash` | `EB-DeepSeek-Pro` |
| Tester | `composer-2.5[fast=false]` | `haiku` | `EB-DeepSeek-Pro` | `EB-GLM-Pro` |

对应文件：

```text
Cursor       .cursor/agents/planner.md | developer.md | tester.md
Codex        .codex/agents/planner.toml | developer.toml | tester.toml
Claude Code  .claude/agents/planner.md | developer.md | tester.md
WorkBuddy    .workbuddy/agents/planner.md | developer.md | tester.md
             （格式同 Claude Code；但需同步到 ~/.workbuddy/agents/ 才生效）
```

平台适配器只允许声明 `name`、`description`、`model`（Cursor/Claude/Codex 按其格式）、`sandbox_mode`（Codex）和指向 `harness-core/agents/*.md` 的引用，不得复制核心规则。

WorkBuddy 适配器额外允许 `category`、`version`、`tags` 三个可选元数据字段。因运行时只加载用户级目录，仓库内配置须经 `scripts/install_workbuddy_agents.py` 同步；同时其角色约束仍需按 `harness-core/protocols/workbuddy-subagents.md` 的六项 prompt 要素注入。

## 5. 目录与关键文件

### 5.1 核心目录

| 路径 | 作用 |
|------|------|
| `harness-core/router.md` | 四端统一入口，项目级意图路由与开发门禁 |
| `harness-core/protocols/development-rules.md` | 开发阶段全局规则、端口约定、经验沉淀链条 |
| `harness-core/protocols/cursor-subagents.md` | Cursor 子智能体编排协议 |
| `harness-core/protocols/codex-subagents.md` | Codex 子智能体协议，Claude 编排/降级语义复用 |
| `harness-core/protocols/workbuddy-subagents.md` | WorkBuddy 子智能体协议（动态拉起 + prompt 六要素） |
| `harness-core/protocols/platform-adapters.md` | 四端适配层边界说明 |
| `harness-core/agents/*.md` | Planner / Developer / Tester 核心规则 |
| `harness-core/dev-standards/*.md` | 前端/后端开发规范 |
| `harness-core/skills/**` | 产品设计、修整、导入、删除、Bugfix、场景对齐等 Skill |
| `harness-core/commands/sdd-bugfix.md` | 唯一保留的手动命令核心流程 |

### 5.2 平台适配目录

| 平台 | Subagent / 规则 | 命令 |
|------|-----------------|------|
| Cursor | `.cursor/agents/*.md`、`.cursor/rules/00-harness-router.mdc` | `.cursor/commands/sdd-bugfix.md` |
| Codex | `.codex/agents/*.toml`、`.codex/config.toml` | `.codex/commands/sdd-bugfix.md` |
| Claude Code | `.claude/agents/*.md`、`.claude/CLAUDE.md` | `.claude/commands/sdd-bugfix.md` |
| WorkBuddy | `.workbuddy/agents/*.md`（需同步到用户级）、`.workbuddy/skills/sdd-harness/SKILL.md`（需同步到用户级）、`AGENTS.md` | `.codebuddy/commands/sdd-bugfix.md`（项目级命令目录名为 `.codebuddy`） |

### 5.3 项目状态文件

业务文件位于 `<active_project_path>/`，即 `Projects_Repo/<active_project_id>/`：

```text
.sdd/
  tasks.json                 # 任务状态机，调度唯一真相
  experience.md              # 项目级经验
  work-log.md                # 工作日志
  test-reports/              # 当前测试报告（覆写）
  bug-logs/                  # BUG 历史日志（追加）
  bug_fix/                   # Bugfix 报告
docs/
  PRD.md                     # 产品需求
  api-contracts.md           # API 契约
  Plan.md                    # 开发计划
  prototypes/                # 高保真原型
frontend/                    # 前端代码
backend/                     # 后端代码
pycore/                      # 框架依赖
```

## 6. 开发门禁

只有同时满足以下条件，才进入多智能体开发：

1. `docs/PRD.md` 存在。
2. `docs/api-contracts.md` 存在。
3. `docs/prototypes/` 存在，或用户明确放弃原型要求。
4. `docs/Plan.md` 存在。
5. `.sdd/tasks.json` 存在。
6. 已和用户对齐运行时命令与虚拟环境。
7. 外部依赖与配置草稿已确认：涉及 LLM、Embedding、Rerank、支付、短信、对象存储、三方登录等外部服务时，供应商、关键字段、Key/账号来源与存放位置已确认；或用户已明确选择 Mock/降级开发。
8. 用户明确表示开始或继续开发。

进入开发后，Orchestrator 必须先读取系统级经验 `<harness 根>/memory/harness-experience.md`，挑出与当前项目栈/形态相关的教训，随任务上下文传给 Planner。

## 7. 协作流程详解

### 7.1 Planner：任务拆分

Planner 读取 `Plan.md`、`PRD.md`、`api-contracts.md`、系统级经验和外部服务清单，拆成四类任务：

| 阶段 | 说明 | `user_gate` |
|------|------|-------------|
| 前端 Mock 页面 | 页面走 `frontend/src/mocks/`，先让用户验收 UI/UX | `true` |
| 后端基础设施 | 项目结构、配置、数据库、中间件、健康检查等 | `false`，自动连续执行 |
| 逐功能闭环 | 后端真实 API + 前端退出 Mock + 页面联调 | `true` |
| E2E 回归 | 全系统回归、跨模块链路、启动文档 | `true` |

关键约束：

- 每个业务功能必须是完整闭环，严禁把“后端实现”和“前端联调”拆成两个独立任务。
- Web 后端业务任务必须设置 `frontendIntegration.required = true`，把 Mock 退出标准写清楚。
- `acceptanceCriteria` 面向非技术用户，从前端页面可理解、可验证；`technicalChecks` 面向 Agent/Tester 自动执行。
- 若当前是移动端项目，客户端任务 `rules_files = []`，只有后端 API 任务读取 backend rules；移动端缺少默认规范时需先提示用户。

`tasks.json` 任务核心字段：

| 字段 | 含义 |
|------|------|
| `id` | 任务编号，如 `T-001` |
| `type` | `frontend` / `backend` / `integration` |
| `acceptanceCriteria` | 用户可见验收标准 |
| `technicalChecks` | 自动验证命令或技术验收项 |
| `frontendIntegration` | 真实前端联调要求 |
| `externalServices` | 本任务依赖的外部服务 |
| `dependencies` | 前置任务 |
| `priority` | 调度优先级，越小越先执行 |
| `rules_files` | 本任务必须遵守的开发规范 |
| `status` | 任务状态 |
| `retry_count` | 修复重试次数，由 Orchestrator 更新 |
| `blocked` | 是否阻塞自动调度 |
| `user_gate` | 完成后是否触发用户门禁 |

### 7.2 Orchestrator：任务选择

Orchestrator 从 `.sdd/tasks.json` 中选择下一个任务：

```text
status = "pending"
blocked = false
所有 dependencies 均已 passed
priority 最小
```

### 7.3 Developer：代码实现

每次调度只做**一个任务**。Developer 开始前读取：

1. `.sdd/experience.md`（项目经验，避免重复踩坑）。
2. `.sdd/tasks.json` 中该任务的 `description`。
3. `rules_files` 指定的规范文件，`dev-standards/...` 解析到 `harness-core/dev-standards/...`。
4. `docs/api-contracts.md`。
5. 如果 `externalServices` 非空，读取外部服务清单与降级策略。
6. 前端任务必须读取 `docs/prototypes/` 并严格对齐文案与样式。
7. 后端任务执行 Git 检查、pycore 框架检查、测试库隔离检查等基础设施前置检查。

Developer 硬约束：

- 禁止修改 `.sdd/tasks.json`。
- 禁止启动服务器或后台进程。
- 允许且应当自动安装项目内依赖，不得要求用户手动安装。
- 真实密钥只写入 `.env` 等配置文件，不得出现在报告、经验、日志、文档中。
- 完成后只返回修改/新增文件路径，不回传大段代码。
- 完成后追加项目级 `.sdd/experience.md`；跨项目通用教训标注 `[SYSTEM] 建议回传系统级经验`。

### 7.4 Tester：独立验证

Tester 不信任 Developer 的声明，只按当前任务的 `acceptanceCriteria` 验证，**不扩散验证范围**。

验证重点：

- 代码存在性、语法、导入、密钥泄露、`TODO/FIXME/HACK` 标记。
- `acceptanceCriteria` 逐条给出 PASS / FAIL。
- 前端任务严格对齐高保真原型：文案、布局、配色、间距、圆角、字号。
- Mock 阶段不检查真实后端；真实闭环任务必须验证 `VITE_USE_MOCK=false` 下命中真实 API，且页面无 `[Mock]` 残留。
- 后端任务验证真实运行路径、真实数据库落盘、测试库与业务库隔离。
- 外部服务无法真实调用时明确标记 `Mock/fallback only`，不得假装完整联调通过。

结果分类：

| 结果 | 含义 | Tester 更新 |
|------|------|--------------|
| `PASS` | 全部验收标准通过 | `status = "passed"` |
| `FAIL` | 代码缺陷 | `status = "fixing"`，写测试报告与 BUG 日志 |
| `BLOCKED` | 环境/权限/端口/外部服务不可用 | `status = "blocked"`，不更新 `retry_count`、不写 BUG 日志 |

Tester 写入双轨产物：

- `.sdd/test-reports/test-<task-id>.md`：当前状态，覆写。
- `.sdd/bug-logs/<task-id>.md`：历史累积，只追加不覆写。

## 8. 状态机与重试

```text
pending
  -> Developer 实现
  -> Tester 验证
       |
       +-- PASS    -> Code Review 审查
       |               +-- 无 Blocker -> passed（若 user_gate=true 则触发用户门禁）
       |               +-- 有 Blocker -> fixing（Orchestrator retry_count++），转回 Developer
       +-- FAIL    -> fixing（Orchestrator retry_count++）
       |               -> retry_count < 3  ?  重新调度 Developer
       |               -> retry_count >= 3 ?  标记 blocked，请求人工介入
       +-- BLOCKED -> blocked（环境阻塞，retry_count 不增加）
```

规则：

- `retry_count` 由 Orchestrator 更新，Developer/Tester 不直接改。
- 同一任务自动修复最多 3 次；超过则暂停并要求用户介入。
- `BLOCKED` 不是开发者代码问题，不计入重试次数，也不写入 BUG 日志。
- `user_gate = true` 的任务通过 Tester 后，必须**先过 Code Review 且 Blocker 清零**，才触发用户门禁，由用户确认后再推进下一个需要门禁的任务；`user_gate = false` 的基础设施任务自动连续推进。
- Code Review 的 Blocker 修复与 Tester 的 FAIL 修复共用同一个 `retry_count`，避免「审查-修复」循环无限往复。

### 8.1 Code Review 环节

Tester PASS 只说明行为符合验收标准，不说明写法守规范。因此大改任务在 Tester PASS 后增补一道代码审查：

```text
harness-core/skills/sdd-code-review/SKILL.md
```

- 触发：大改任务 Tester PASS 后、`user_gate` 前；大改收口；导入纳管基线；架构类 Bugfix 复审；用户显式要求。小改与中间改不强制。
- 产物：`.sdd/reviews/review-<task-id>.md` / `review-sprint-YYYYMMDD.md`，按 `Blocker / Major / Minor / Nit` 分级，每条含 `文件:行号 + 违反条款`。
- 只报不改：Orchestrator 把问题清单转给 Developer 修，Tester 复验行为，Code Review 复审关闭。
- Blocker 未关闭不得进入 `user_gate`，也不得把任务标为可交付。
- 报告末尾固定输出「可晋升为系统级经验的条目」，接入经验沉淀链条。


## 9. 通信机制与共享状态

### 9.1 无直接子智能体通信

子智能体之间不直接通信，通过共享文件系统异步协作：

- 父 -> 子：通过平台调用工具的 `prompt` 传入任务指令、路径、任务 ID、运行时命令。
- 子 -> 父：只返回文本摘要，通常包含文件路径列表和 PASS / FAIL / BLOCKED 结论。
- 子 -> 子：不直接通信，通过 `.sdd/tasks.json`、测试报告、经验文件中转。

每次子智能体调用都是**全新上下文**，没有跨会话记忆；Orchestrator 必须在每次 `prompt` 中显式传入恢复上下文所需的路径和参数。

### 9.2 核心共享文件

| 文件 | 谁写 | 谁读 | 作用 |
|------|------|------|------|
| `.sdd/tasks.json` | Planner 初始化，Tester 更新状态，Orchestrator 调度 | Orchestrator / 三角色 | 任务状态唯一真相 |
| `.sdd/experience.md` | Developer / Tester / Bugfix / 修整 / Code Review | Developer / Bugfix / 修整 / Code Review | 项目级经验 |
| `.sdd/test-reports/test-<id>.md` | Tester | Developer（修复时）、Orchestrator | 当前验收结论 |
| `.sdd/reviews/review-<id>.md` | Code Review | Developer（修复时）、Orchestrator | 规范与契约审查结论 |
| `.sdd/bug-logs/<id>.md` | Tester | 后续 Tester / 修复 | 历史返工记录 |
| `<harness 根>/memory/harness-experience.md` | Orchestrator 回传 | Orchestrator / Planner | 系统级经验 |

## 10. 经验沉淀闭环

权威定义在 `harness-core/protocols/development-rules.md`「经验沉淀链条」。当前采用**两级经验**：

| 级别 | 文件 | 内容 | 写 | 读 |
|------|------|------|----|----|
| 项目级 | `Projects_Repo/<id>/.sdd/experience.md` | 本项目踩坑、修复要点、避坑规则 | Developer / Tester / Bugfix / 修整 | Developer / Bugfix / 修整 |
| 系统级 | `<harness 根>/memory/harness-experience.md` | 跨项目可复用、能反哺 Harness 的教训 | Orchestrator 回传 | Orchestrator + Planner |

写回链：

- Developer 完成后追加项目经验；重复问题标注 `[SYSTEM]`。
- Tester 判 FAIL 且属跨项目通用问题时，在报告追加 `## 系统级经验`。
- Orchestrator 收到带 `[SYSTEM]` 或 `## 系统级经验` 的产物后，提炼并追加到系统级经验文件。

回读链：

- 开发开始时，Orchestrator 先读系统级经验，把相关教训传给 Planner。
- Planner 把教训转成可执行约束，写入相关任务的 `acceptanceCriteria`、`technicalChecks`、`rules_files` 或 `notes`。
- Developer 动手前读项目级经验；Bugfix / 修整同样先回查两级经验。
- 反复重犯的系统级经验应升级为 `harness-core/` 硬性规则，而不是只停留在经验文件。

## 11. 四端调用方式

### 11.1 Cursor

Cursor 通过 `Task` 工具拉起子智能体，`subagent_type` 与 `.cursor/agents/*.md` 的 `name` 字段一致：

```typescript
Task({
  description: "实现任务 T-001",
  prompt: [
    "active_project_id = ...",
    "active_project_path = Projects_Repo/<id>/",
    "任务 ID = T-001",
    "本会话运行时 = $PY",
    "请先读取并严格执行 harness-core/agents/developer.md",
  ].join("\n"),
  subagent_type: "developer",
  run_in_background: false,
})
```

### 11.2 Codex

Codex 使用 `.codex/agents/*.toml` 声明子智能体：

```toml
name = "developer"
description = "代码实现专家。根据任务描述编写代码，自动安装项目内依赖，完成后积累 experience.md。"
model = "EB-DeepSeek-Pro"
sandbox_mode = "workspace-write"

developer_instructions = """
读取并严格执行：
harness-core/agents/developer.md
"""
```

主会话承担 Orchestrator。如果当前 Codex 环境不支持自定义 subagent TOML，则按 `harness-core/protocols/codex-subagents.md` 在主会话中模拟 Planner / Developer / Tester，但必须保持角色边界。

### 11.3 Claude Code

Claude Code 使用原生 `.claude/agents/*.md` 子智能体，主会话承担 Orchestrator。编排与降级语义遵循 `harness-core/protocols/codex-subagents.md`。如果原生子智能体不可用，同样在主会话中模拟三角色。

### 11.4 WorkBuddy

WorkBuddy 用 Markdown + YAML frontmatter 声明子智能体（格式同 Claude Code），但运行时只从用户级 `~/.workbuddy/agents/` 发现，需先同步：

```bash
python scripts/install_workbuddy_agents.py
```

声明后即可按角色名调度：

```typescript
Agent({
  description: "实现任务 T-001",
  prompt: [
    "你是 SDD Harness 的 Developer 子智能体。",
    "第一个动作：读取并严格执行 harness-core/agents/developer.md，",
    "并读取 <path>/.sdd/experience.md 中的相关避坑规则。",
    "active_project_id = ...",
    "active_project_path = ...（绝对路径）",
    "本次只做这一个任务：" + JSON.stringify(task),
    "rules_files = [...]",
    "运行时 $PY = ...；前端 5199 / 后端 8099",
    "禁止：修改 .sdd/tasks.json 状态；真实 Key 写入 docs/JSON；越界到其他任务。",
  ].join("\n"),
  subagent_type: "developer",
  run_in_background: false,
})
```

关键点：静态文件只声明"角色存在"，**不携带任务上下文**。因此六项 prompt 要素（角色声明、核心文件读取、项目路径、单任务载荷、运行时与端口、边界禁令）每次都必须完整注入。详见 `harness-core/protocols/workbuddy-subagents.md`。

## 12. 命令入口与 Bugfix

四端各保留一个手动命令适配：

```text
.cursor/commands/sdd-bugfix.md
.codex/commands/sdd-bugfix.md
.claude/commands/sdd-bugfix.md
.codebuddy/commands/sdd-bugfix.md    # WorkBuddy 的项目级命令目录名
```

WorkBuddy 的项目级斜杠命令目录被客户端硬编码为 `.codebuddy/commands`（历史遗留名），与适配目录 `.workbuddy/` 不同名。选项目级而非用户级 `<configDir>/commands`，是为了避免 `/sdd-bugfix` 出现在所有无关项目的斜杠菜单里。

所有手动命令都指向核心流程：

```text
harness-core/commands/sdd-bugfix.md
harness-core/skills/sdd-bugfix/SKILL.md
```

新建项目、需求对齐、开始开发、已有项目修整、导入项目和删除项目不得通过新增平台命令实现，必须由 `harness-core/router.md` 根据自然语言意图进入对应 Skill。

## 13. 关键设计原则

- **单一职责**：Planner 只拆任务、Developer 只写代码、Tester 只验证、Orchestrator 只调度。
- **文件系统中转**：子智能体间异步协作，不依赖共享内存。
- **状态驱动**：`.sdd/tasks.json` 是调度唯一真相。
- **独立验证**：Tester 不信任 Developer 声明。
- **有限重试**：同一任务自动修复最多 3 次。
- **用户门禁驱动**：`user_gate = true` 的任务通过后必须用户确认。
- **经验闭环**：经验既要写回、也要回读，最终可升级为核心规则。
- **核心规则单源**：四端只做适配，不在平台目录复制核心流程。
- **敏感值隔离**：真实 Key / Token / Secret 只进 `.env` 等配置文件。

## 14. 当前限制

- **串行执行**：当前默认串行开发以避免文件冲突；`tasks.json` 已含 `priority` 与 `dependencies`，但并行开发需额外 git worktree / 写集合隔离机制。
- **无子智能体跨会话记忆**：每次调用都是新上下文，只能靠文件系统恢复。
- **移动端默认规范缺失**：移动端客户端任务 `rules_files = []`，需要用户自备 PRD / 原型 / 契约 / Plan 或补充专项规范。
- **Tester 不长期运行服务**：只做短时验证，完成后关闭进程。
- **平台能力差异**：原生 subagent 不可用时会降级为主会话模拟，角色边界仍需维持。
