# WorkBuddy Subagents Protocol

本协议定义 SDD V7.1 在 WorkBuddy 中使用 Planner / Developer / Tester 的方式。

## 目标

WorkBuddy 适配必须保持三件事：

1. 核心规则只在 `harness-core/` 维护
2. `.workbuddy/` 只做薄适配，不复制核心流程
3. 满足开发门禁后，必须用隔离上下文的子智能体编排，而不是在主会话里直接写功能代码

## 与另外三端的结构差异

另外三端通过**静态配置文件**声明子智能体（`.codex/agents/*.toml`、`.claude/agents/*.md`、`.cursor/agents/*.md`），运行时按名查找。

WorkBuddy 同样支持静态声明，但**载体路径不同**：它只从用户级配置目录 `~/.workbuddy/agents/`（或 `$WORKBUDDY_CONFIG_DIR/agents/`）发现子智能体，**不加载**项目内的 `.workbuddy/agents/`。此结论经实测确认（详见下文「实测事实」）。

| 维度 | Codex / Claude / Cursor | WorkBuddy |
|------|-------------------------|-----------|
| 声明载体 | 平台目录下 agent 文件 | 用户级 `~/.workbuddy/agents/*.md` |
| 仓库内留存 | 直接生效 | 仅作版本化源，需同步到用户级才生效 |
| 文件格式 | TOML / MD | Markdown + YAML frontmatter |
| 必填字段 | `name` / `description` / `model` | `name` / `description` / `model` |
| 上下文传递 | 平台注入 + prompt | prompt 显式写入（子智能体不共享上下文） |
| 模型选择 | 写在 agent 文件 | 写在 agent 文件（同样支持） |

### 实测事实（必须遵守）

以下结论均在本仓库真机验证，不得凭推测推翻：

1. 项目级 `.workbuddy/agents/*.md` **不被注册**，调用返回 `Task agent <name> is not available`。
2. 项目根 `.agents/` 同样**不被注册**。
3. 用户级 `~/.workbuddy/agents/*.md` **可被注册并调度**；`model` 字段被接受。
4. 因此仓库内的 `.workbuddy/agents/` 是**版本化源**，必须经 `scripts/install_workbuddy_agents.py` 同步到用户级后才生效。
5. 技能发现根只有四个：`<configDir>`、`<configDir>/skills`、`<builtin plugins>/skills`、`<configDir>/skills-marketplace`，**不含当前工作区**。故 `.workbuddy/skills/sdd-harness/SKILL.md` 也需经 `scripts/install_workbuddy_skill.py` 同步到用户级。
6. **子智能体即时生效**：新装的角色无需重启，当前会话即可调度（实测以全新名字的探针角色验证通过）。
7. **技能与斜杠命令需新会话**：修改用户级 `SKILL.md` 后连续轮询技能缓存 20 秒无变化，故 Skill 与 `.codebuddy/commands/` 的改动需新会话生效。
8. **`AGENTS.md` 内容在会话启动时快照**：文件会被加载并监听，但注入内容停留在会话打开那一刻。

一句话区分：**改子智能体 → 装完即用；改 Skill 或命令 → 需新会话。**
分层自查用 `python scripts/check_workbuddy_adapter.py`。

**双路径分工**：

```text
仓库内（版本化，随 Git 走）  .workbuddy/agents/{planner,developer,tester}.md
        │  python scripts/install_workbuddy_agents.py
        ▼
用户级（运行时生效）        ~/.workbuddy/agents/{planner,developer,tester}.md

仓库内（版本化，随 Git 走）  .workbuddy/skills/sdd-harness/SKILL.md
        │  python scripts/install_workbuddy_skill.py
        ▼
用户级（运行时生效）        ~/.workbuddy/skills/sdd-harness/SKILL.md
```

用户级 Skill 对所有工作区可见，因此 `SKILL.md` 必须保留「阶段 0：工作区校验」，确认当前目录存在 `harness-core/router.md` 与 `AGENTS.md`，否则静默退出。安装脚本与一致性检查都会强制这一点。

## 三个角色配置

| 角色 | 文件 | 默认模型 | 职责 |
|------|------|----------|------|
| planner | `.workbuddy/agents/planner.md` | `EB-DeepSeek-Flash` | 技术方案设计与任务拆分，产出 `.sdd/tasks.json` |
| developer | `.workbuddy/agents/developer.md` | `EB-DeepSeek-Pro` | 按单任务实现代码，回写项目经验 |
| tester | `.workbuddy/agents/tester.md` | `EB-GLM-Pro` | 独立验证，区分 PASS / FAIL / BLOCKED |

### 字段说明与默认值

| 字段 | 必填 | 默认值 | 作用 |
|------|------|--------|------|
| `name` | 是 | 角色名（`planner` / `developer` / `tester`） | 子智能体标识，必须与调用时的 `subagent_type` 一致 |
| `description` | 是 | 见各文件 | 运行时据此判断何时选用该角色；必须包含触发关键词 |
| `model` | 是 | 见上表 | 该角色使用的模型 id，须存在于 `~/.workbuddy/models.json` |
| `category` | 否 | `agent` | 与内置插件 agent 保持一致的分类标记 |
| `version` | 否 | `"1.0.0"` | 配置版本，便于审计 |
| `tags` | 否 | `[sdd, <role>, harness]` | 检索标签 |

模型选择原则：Planner 偏推理（`EB-DeepSeek-Flash` 支持 reasoning）、Developer 偏代码生成（`EB-DeepSeek-Pro`）、Tester 需要独立视角（`EB-GLM-Pro`，与 Developer 不同家族以降低同源误判）。三者必须使用不同模型，否则 Tester 的独立性会被同源偏差削弱。

### 角色依赖关系

```text
Router（开发门禁 8 项全满足）
        │
        ▼
Orchestrator（主会话，只调度不写码）
        │
        ├─ 1. 读 memory/harness-experience.md（系统级经验）
        │
        ├─ 2. 调度 planner  ──► .sdd/tasks.json
        │        ↑                    │
        │        └─ 必须把经验转成可执行约束
        │                             │
        ├─ 3. 调度 developer ◄────────┘  （单任务，读 .sdd/experience.md）
        │        │  改动代码
        │        ▼
        ├─ 4. 调度 tester（独立验证，不信任 developer 自述）
        │        │  FAIL ──► 回 3（同一任务最多 3 次）
        │        │  PASS ──► 用户门禁（user_gate=true 时）
        │        ▼
        └─ 5. 回传 [SYSTEM] 经验到 harness-experience.md
```

硬依赖：**planner 未产出 `tasks.json`，developer 无任务可执行；developer 未完成，tester 无对象可验证。** 三者严格串行，不得并发写同一项目目录。tester 判 FAIL 时回到 developer，但**不得由 developer 自行宣布 PASS**。

## 每次调用必须注入的 prompt 要素

## 调用前置条件

调度前必须确认三个角色已安装到用户级，否则调用会直接失败：

```text
python scripts/install_workbuddy_agents.py --check
```

返回 `RESULT: OK` 才可调度。若返回 DRIFT，先执行：

```text
python scripts/install_workbuddy_agents.py
```

若调用仍返回 `Task agent <name> is not available`，说明用户级配置未就位或被其他 agent 同名覆盖，必须停止并按本节排查，**不得改由主会话直接写功能代码绕过**。

## Orchestrator 调用必须注入的 prompt 要素

即使三个角色已通过静态文件注册，`prompt` 仍必须自包含。静态文件只声明"这个角色存在"，不携带具体任务上下文。以下六项缺一不可：

1. **角色声明**：明确"你是 SDD Harness 的 Planner / Developer / Tester"。
2. **核心文件强制读取**：要求该子智能体第一个动作是 Read 对应的 `harness-core/agents/<role>.md` 并严格执行。
3. **项目路径**：`active_project_id` 与 `active_project_path`（绝对路径优先）。
4. **任务载荷**：Developer / Tester 必须传入**单个**任务的完整定义（来自 `.sdd/tasks.json`），不得传整个任务列表让其自行挑选。
5. **运行时与端口**：本会话已确认的 `$PY` 实际命令；端口按 `harness-core/protocols/development-rules.md`「端口约定（单一权威源）」取值（Agent 验证组 / 用户门禁组），不在 prompt 里另抄一份数值。
6. **边界禁令**：Developer 不修改 `.sdd/tasks.json` 状态；Tester 只更新 status / notes；真实 Key 只进 `.env`。

### Planner prompt 模板

```text
你是 SDD Harness 的 Planner 子智能体。

第一个动作：读取并严格执行 harness-core/agents/planner.md，以及
harness-core/protocols/development-rules.md 的「经验沉淀链条」。

项目：active_project_id=<id>，active_project_path=<绝对路径>
输入：<path>/docs/PRD.md、docs/Plan.md、docs/api-contracts.md
系统级经验：<harness 根>/memory/harness-experience.md（必须挑出相关教训并转成可执行约束）

输出要求：生成 tasks.json 内容，按 harness-core/agents/planner.md 的任务拆分原则与验收标准分层规则。
禁止：修改任何业务代码；不得把技术检查写入 acceptanceCriteria。

完成后返回：tasks.json 全文 + 任务概览表 + 用户验收点表格。
```

### Developer prompt 模板

```text
你是 SDD Harness 的 Developer 子智能体。

第一个动作：读取并严格执行 harness-core/agents/developer.md，并读取
<path>/.sdd/experience.md 中与本次任务相关的避坑规则。

项目：active_project_id=<id>，active_project_path=<绝对路径>
本次只做这一个任务（不得越界到其他任务）：
<粘贴 .sdd/tasks.json 中该任务的完整 JSON>

rules_files：<该任务声明的 dev-standards 文件，按 harness-core/dev-standards/ 解析>
运行时：$PY = <本会话确认的实际命令>
端口：<按 harness-core/protocols/development-rules.md「端口约定」填入本任务所需端口组，如需启动验证>

禁止：
- 修改 .sdd/tasks.json 的状态字段
- 把真实 Key / Token / Secret 写入任何 docs、报告、代码或 JSON
- 业务文件写到 Projects_Repo/<id>/ 之外

完成后返回：改动文件清单 + 自测结果 + 需要写入 .sdd/experience.md 的经验条目。
```

### Tester prompt 模板

```text
你是 SDD Harness 的 Tester 子智能体。

第一个动作：读取并严格执行 harness-core/agents/tester.md。

项目：active_project_id=<id>，active_project_path=<绝对路径>
本次只验证这一个任务：
<粘贴该任务的完整 JSON，含 acceptanceCriteria 与 technicalChecks>

要求：
- 独立验证，不信任 Developer 的任何自述
- 逐条 acceptanceCriteria 给出 PASS / FAIL 与证据（命令输出、页面行为）
- technicalChecks 必须实际执行，不得凭代码阅读判定通过
- 只更新 .sdd/tasks.json 中该任务的 status / notes，不改其他字段
- 写测试报告到 <path>/.sdd/test-reports/，BUG 追加到 <path>/.sdd/bug-logs/

完成后返回：PASS / FAIL / BLOCKED + 证据 + 若属跨项目通用问题的「## 系统级经验」章节。
```

## Orchestrator 职责

Orchestrator（主会话）负责：

- 读取 `project-registry.json`
- 确定 `active_project_path`
- 读取 `.sdd/tasks.json` 的任务状态
- **开发开始时读取系统级经验 `<harness 根>/memory/harness-experience.md`，挑出相关教训传给 Planner**（经验回读环）
- 用 Agent 工具调度 Planner / Developer / Tester
- 汇总 PASS / FAIL / BLOCKED
- **回传系统级经验**：收到带 `[SYSTEM]` 标注或 `## 系统级经验` 的产物后，追加到 `<harness 根>/memory/harness-experience.md`
- 维护用户门禁

经验链条完整定义见 `harness-core/protocols/development-rules.md`「经验沉淀链条」。

Orchestrator 禁止：

- 直接读业务代码细节
- 直接写功能代码
- 跳过 Tester
- 把业务文件写入 Harness 根目录
- 以"子智能体不可用"为由跳过角色边界、改在主会话直接实现（应先按「调用前置条件」排查安装）

## 并发与串行

- Planner 与 Developer / Tester 有严格依赖，必须串行。
- 多个互不依赖的**只读**任务（如多个并行调研）可以并发，但不得并发写同一项目目录。
- Developer 与 Tester 对同一任务必须串行，禁止并发评审。

## 降级模式

如果当前 WorkBuddy 环境不能拉起子智能体（Agent 工具不可用或被禁用），或用户级安装无法就位：

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

## WorkBuddy 命令适配

WorkBuddy 端只保留 `sdd-bugfix` 一个命令适配，位于：

```text
.codebuddy/commands/sdd-bugfix.md
```

**注意目录名**：WorkBuddy 的**项目级**斜杠命令目录被客户端硬编码为 `.codebuddy/commands`（历史遗留名，已实测确认），与适配目录 `.workbuddy/` 不同名。用户级命令目录则是 `<configDir>/commands`。

选择项目级而非用户级的原因：用户级会让 `/sdd-bugfix` 出现在**所有**无关项目的斜杠菜单中，项目级只在本仓库可见。

新建项目、需求对齐、开始开发、已有项目修整、导入已有项目、删除项目仍由 `harness-core/router.md` 根据自然语言意图分发。用户显式要求修 Bug 时，命令适配器与 Orchestrator 均指向：

```text
harness-core/commands/sdd-bugfix.md
harness-core/skills/sdd-bugfix/SKILL.md
```

不得新增 `.workbuddy/commands/`。如确需新增其他命令，必须先更新 `harness-core/protocols/platform-adapters.md` 契约。

## 与 WorkBuddy 原生能力的边界

WorkBuddy 自带 Skill、Expert、Connector、Library 等扩展机制，与 SDD 的核心层**不是替代关系**：

- SDD 流程（路由、产品设计、Agent 规则、开发规范）只在 `harness-core/`，不迁移到 `.workbuddy/skills/`。
- WorkBuddy 的 `.workbuddy/memory/` 是宿主会话记忆，**不得**替代 `.sdd/experience.md` 与 `memory/harness-experience.md`。
- WorkBuddy 内置 Skill（如文档、表格、PPT 生成）可作为工具被 Developer 调用，但不得改变 SDD 的任务拆分与验收口径。
