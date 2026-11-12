---
description: SDD V7.1 开发阶段全局规则。由 router.md 在进入开发阶段时按需读取，非always-apply。
---

# 全栈开发助手 — 全局规则

核心技术栈：后端 Python 3.11+ / FastAPI / PyCore。前端默认使用 React + TypeScript + Vite；桌面 Web 使用 Ant Design，移动端 H5 使用 Ant Design Mobile。**不接受无确认替换。**

## 开发阶段全局规则

本文件只在 `harness-core/router.md`「开发循环启用判断」判定为大改 / 复杂需求、并满足「开发门禁」后进入读取；小改 / 中间改由 `harness-core/skills/sdd-project-maintenance/SKILL.md` 直接执行，不强制进入 Planner -> Developer -> Tester 循环。

- **Plan.md 是唯一的进度文件**：设计阶段 C 生成，开发阶段维护，前后端共用
- **自动化开发前必须确认外部服务与测试权限**：进入 Planner / Developer / Tester 循环之前，必须先确定项目会引用哪些外部服务，并向用户获取 Tester 完整联调所需的服务 Key、账号、Base URL、回调配置或测试环境权限
- **按 Planner 主线推进**：前端 Mock 先行 → 后端基础设施自动连续执行 → 逐功能闭环开发。前端 Mock 页面完成、每个功能闭环完成后触发用户门禁；后端基础设施任务不触发用户门禁，由 Agent/Tester 自动推进。
- **Mock 数据对齐 api-contracts.md**：前端 Mock 数据集中存放在 `frontend/src/mocks/`，格式必须与 api-contracts.md 一致
- **后端业务任务必须任务内真实联调**：凡是对应已有前端页面或 service 的后端功能，完成时必须同步让前端在 `VITE_USE_MOCK=false` 下调用真实后端；不能把首次联调推迟到最终 E2E
- **后端每个功能完成后必须提供测试指令**：前端真实联调测试（操作步骤+预期结果）+ 终端测试（curl 命令+预期返回）
- **交付**：全部功能自动验证通过后，输出 `docs/startup.md`（环境要求、启动命令、默认配置）；用户最终业务验收发现问题时进入 `sdd-bugfix`
- **Agent 自动执行项目内命令**：项目内脚手架、依赖安装、代码生成、lint、typecheck、build、单元测试、短时验证命令，默认由 Agent 自行执行，不要让用户手动复制命令
- **需要用户确认的命令**：全局安装、`sudo`、系统设置修改、删除/覆盖大量文件、数据库迁移、部署发布、长期运行服务、涉及密钥或付费资源的命令，必须先向用户确认
- **缺少外部服务配置不得假装完整验收**：如果用户暂不提供必要 Key / 测试账号 / 权限，只能进入明确标注的 Mock/fallback 降级开发；Tester 报告必须写明“真实外部服务未验收”，不得标记为完整联调通过
- **真实密钥只进配置文件**：见下文「密钥与敏感配置红线（单一权威源）」，本节不重述文件清单
- **测试策略**：Agent 能执行的自动化测试必须自行执行；前端完成后的页面检查由 Tester/Agent 先跑；每个功能开发并测试通过后，必须触发用户门禁，由用户确认后再推进下一个功能；需要业务判断或最终验收的部分，输出操作步骤交给用户验证
- **最终回归边界**：最终 E2E / 启动文档阶段只做全系统回归、跨模块链路和部署前检查；不得替代后端业务任务内的前端真实联调
- **人工门禁驱动**，按 `docs/Plan.md` 和 `.sdd/tasks.json` 逐功能开发。前端 Mock 页面和每个功能闭环完成后经 Tester 验证，必须触发用户门禁，由用户确认后才继续下一个需要门禁的任务；基础设施任务按 `user_gate=false` 自动连续推进。
- **Tester PASS 不等于可交付**：大改任务在 Tester 判 PASS 之后、`user_gate` 之前，必须先过代码审查（`harness-core/skills/sdd-code-review/SKILL.md`）；Blocker 未关闭不得提交用户验收。
- **以下情况必须暂停询问用户**：
  - PRD / API 契约 / 业务目标存在歧义
  - Planner 产出开发清单后，需用户确认
  - 每个功能 Developer + Tester 循环完成后，需用户决定是否继续下一个功能
  - 同一任务自动修复 3 次仍失败
  - 需要架构级决策
  - 需要全局安装、`sudo`、系统设置、真实密钥、付费资源、部署发布或长期服务

## 密钥与敏感配置红线（单一权威源）

本节是本框架「密钥与敏感值」的唯一权威定义。各 agent、dev-standards、skill、平台协议**只引用本节，不得另立一套文件清单**——此前 6 处各写一版且清单条目数不同（`developer.md` 列 4 组、`git-workflow` 只列 1 段），已导致"某些产物文件被漏检"。

### 允许写入的地方

真实敏感值**只能**写入配置文件：

- `backend/.env`、`frontend/.env.local`、项目根 `.env` / `.env.local`
- 用户明确指定的本地 secret 配置文件

### 禁止出现真实敏感值的文件范围（全量清单）

以下位置只能写**字段名 + 配置状态**，禁止写真实值、部分值、或可还原片段：

| 类别 | 具体路径 |
| ---- | -------- |
| 文档 | `docs/**`（含 `PRD.md`、`Plan.md`、`api-contracts.md`、`prototypes/**`、`澄清文档/**`、`startup.md`） |
| SDD 状态 | `.sdd/**`（含 `tasks.json`、`work-log.md`、`status.json`、`project.json`） |
| 经验 | `.sdd/experience.md`、`<harness 根>/memory/harness-experience.md` |
| 报告 | `.sdd/test-reports/**`、`.sdd/reviews/**`、`.sdd/bug-logs/**`、`.sdd/bug_fix/**`、`.sdd/experience-audit/**`、完成报告 |
| 框架文件 | `README.md`、`AGENTS.md`、`HARNESS.md`、任何 `*.md` / `*.json` / `*.yaml` 可读产物 |
| 代码与日志 | 源码中的硬编码、日志输出、错误信息、调试打印、前端可见文案 |

> 判断标准不是"这个文件重不重要"，而是**它是否会被提交进 Git、是否会被模型读取、是否会展示给用户**。三者任一为真，就不得出现真实值。

### 禁止的写法

- 完整真实值：`sk-xxxx`、`Bearer eyJ...`、真实密码串
- 部分值或前缀 + 省略：`sk-abc...`（前缀本身即泄露线索）
- 可还原片段：Base64 编码后的密钥、拆分拼接的密钥、截图中的密钥
- 结构化还原：把 `.env` 全量内容贴进报告并"看起来像示例"

### 允许的写法

```text
BAILIAN_API_KEY：已配置于 backend/.env
LLM_API_KEY：字段存在，未打印值
DATABASE_URL：已配置（指向本地 SQLite）
支付回调：未配置 / 用户选择 Mock 降级
```

### 例外与处理

- **发现泄露时的正确动作**：只写「发现密钥泄露（文件路径 + 字段名）」，**禁止复述泄露原文**；然后提示用户轮换该密钥——已提交进 Git 历史的值必须视为已泄露，改文件不足以修复。
- **`.env.example` / 模板文件**：只写字段名与空占位，不得填入真实值或看似真实的假值（假值会被误当成可用配置）。
- **测试报告与审查报告**：判断"是否泄露"是 Tester 与 Code Review 的必检项；两者都只报位置与字段名。

## 端口约定（单一权威源）

以下端口是全项目唯一权威声明。各 agent、dev-standards、平台协议与子智能体 prompt **只允许引用本节，不得各自另定或重抄数值**：

| 用途 | 前端端口 | 后端端口 |
| ---- | -------- | -------- |
| Agent / Tester 自动验证 | 5199 | 8099 |
| 用户门禁验收 | 5175 | 8003 |

- Vite 代理默认指向后端 `8099`，通过 `VITE_BACKEND_PROXY_TARGET=http://localhost:8003` 切到用户门禁端口。
- 后端 CORS 必须同时允许 `localhost` / `127.0.0.1` 的 `5199` 与 `5175`，即四个来源都要在允许列表内。
- `frontend/.env` 的 `VITE_API_BASE_URL` 使用相对路径 `/api`，禁止写完整后端 URL。
- WebSocket 路径 `/ws` 单独配置 `ws: true` 代理，前端代码禁止硬编码 `ws://localhost:<port>`。
- 启动命令模板：后端 `cd backend && PYTHONPATH=.. $PY -m uvicorn src.main:app --host 127.0.0.1 --port <后端端口>`；前端 `cd frontend && npm run dev -- --host 127.0.0.1 --port <前端端口>`；用户门禁时前端额外带 `VITE_BACKEND_PROXY_TARGET=http://localhost:<门禁后端端口>`。
- 端口被占用时，Agent 验证可临时改用冷门端口，但必须在测试报告中写明实际端口；不得静默 fallback。

> 维护规则：端口数值有任何调整，只需改本表。其他文件出现具体数值时，一律视为"示例示意"而非规则来源；新增文件不得再复制本表数值，只引用本节。

## 阶段规范引用

- 产品设计阶段（R/A/B1/B2/C）：由 `sdd-product-design` Skill 驱动（`harness-core/skills/sdd-product-design/`）
- 前端开发：`dev-standards/frontend.md`
- 后端开发：`dev-standards/backend-dev.md`（总控）+ `dev-standards/backend-layers.md`（分层）+ `dev-standards/backend-plugin.md`（仅 AI Agent 项目）

## 经验沉淀链条（单一权威源）

经验分两级，**既要写回、也要回读**，形成闭环。本节是经验链条的唯一权威定义，各 agent / skill 引用本节，不另立口径。

### 两级经验文件

| 级别 | 文件 | 内容 | 谁写 | 谁读 |
| ---- | ---- | ---- | ---- | ---- |
| 项目级 | `Projects_Repo/<id>/.sdd/experience.md` | 本项目踩过的坑、修复要点、避坑规则 | Developer / Tester / Bugfix / 修整 / Code Review | Developer / Bugfix / 修整 / Code Review（动手前） |
| 系统级 | `<harness 根>/memory/harness-experience.md` | 跨项目可复用、能反哺 Harness 本体的教训 | Orchestrator（回传） | Orchestrator + Planner（开发开始时） |

> 路径口径统一：系统级经验固定为 `<harness 根>/memory/harness-experience.md`（不在 `harness-core/` 下，不写相对歧义路径）。

### 写回链（沉淀）

- Developer 完成任务后，把经验追加到项目 `.sdd/experience.md`；同类问题重复出现时标注 `[SYSTEM] 建议更新规则`。
- Tester 判 FAIL 且属跨项目通用问题时，在测试报告追加 `## 系统级经验` 章节。
- Code Review 在审查报告末尾固定输出「可晋升为系统级经验的条目」；判定为跨项目时标注 `[SYSTEM] 建议回传系统级经验`。
- Bugfix / 修整 完成后必须回写项目经验；跨项目教训标注 `[SYSTEM] 建议回传系统级经验`。
- **Orchestrator 负责回传**：收到带 `[SYSTEM]` / `## 系统级经验` 的产物后，把规则提炼并追加到 `<harness 根>/memory/harness-experience.md`（带日期、来源、Why、How to apply）。

### 回读链（应用，过去缺失的一环）

- **开发开始时，Orchestrator 必须先读 `<harness 根>/memory/harness-experience.md`**，挑出与当前项目栈/形态相关的系统级教训，随任务上下文传给 Planner。
- **Planner 必须把命中的系统级教训转成可执行约束**：写入相关任务的 `acceptanceCriteria` / `technicalChecks`，或在 `rules_files` / `notes` 中点名，避免"经验只写不用"。
- **Developer 动手前读项目 `.sdd/experience.md`**；修整 / Bugfix 同样先回查两级经验。
- 若某条系统级经验反复在不同项目重犯，说明它没被转成强制规则——必须升级为 `harness-core/` 里的硬性规范（rules / 自查清单 / 验收项），而不是停留在经验文件。

## 沟通风格

- 简洁专业，主动推进
- 修改代码前先阅读现有代码
- 每完成一个模块主动告知进展
- 遇到 PRD 不明确的地方及时询问

## 注意事项

- 使用 httpx/openai 这类网络客户端时，永远不要继承环境变量；`httpx.Client` / `httpx.AsyncClient` 必须显式 `trust_env=False`，禁止裸 `httpx.get/post` 快捷调用
