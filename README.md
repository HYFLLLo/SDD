# SDD V7.1 — 项目管理型 AI Coding Harness

> Spec-Driven Development V7.1：从“项目内开发规范包”升级为“多项目管理 Harness”，并支持 Codex / Claude Code / Cursor / WorkBuddy 四端入口。

---

## V7.1 的定位

SDD V7.1 不再默认“当前文件夹就是项目”。它是一个 **项目管理系统**：

1. 先管理项目仓库 `Projects_Repo/`
2. 再选择新建项目 / 克隆项目 / 继续已有项目 / 功能升级 / Bugfix
3. 然后进入单个项目工作区
4. 最后执行产品设计、多 Agent 开发、测试、修复和经验沉淀

一句话：

> V5 是开发规范包，V7.1 是项目管理型、多平台 Agent Harness。

核心原则：

- `harness-core/` 是唯一真相源
- `.codex/`、`.claude/`、`.cursor/`、`.workbuddy/` 只做平台适配
- `Projects_Repo/<project-id>/` 只放业务项目状态和代码，不再复制整套平台规则

---

## 目录结构

```text
SDD_V7.1/
├── AGENTS.md                        # 平台中立入口（Codex / Claude Code / Cursor / WorkBuddy）
├── START.md                         # 非 Cursor 兜底 / 教学说明
├── HARNESS.md                       # Harness 使用规范
├── project-registry.json            # 项目注册表
│
├── harness-core/                    # 唯一真相源：agents / commands / skills / dev-standards / protocols
│   ├── router.md
│   ├── agents/
│   ├── commands/
│   ├── skills/
│   ├── dev-standards/
│   └── protocols/
│
├── .codex/                          # Codex 适配层：subagents TOML + commands + config
│   ├── config.toml
│   └── agents/
│
├── .claude/                         # Claude Code 适配层
│   ├── CLAUDE.md
│   ├── agents/
│   └── commands/
│
├── Projects_Repo/                   # 默认项目仓库，所有项目放这里
│   └── <project-id>/
│
├── .cursor/                         # Cursor 适配层，所有文件只引用 harness-core
│   ├── agents/
│   ├── commands/
│   ├── skills/
│   ├── dev-standards/
│   └── rules/
│
├── .workbuddy/                      # WorkBuddy 适配层：入口 Skill + 三角色 agent
│   ├── README.md
│   ├── agents/                      # planner / developer / tester（需同步到用户级生效）
│   ├── skills/
│   │   └── sdd-harness/SKILL.md
│   └── memory/                      # 宿主会话记忆，非 SDD 经验
│
├── .codebuddy/                      # WorkBuddy 项目级命令目录（客户端硬编码此名）
│   └── commands/
│       └── sdd-bugfix.md
│
├── templates/
│   ├── project/                     # 新项目初始化模板
│   ├── tasks.json
│   ├── experience.md
│   └── work-log.md
│
├── memory/
│   └── harness-experience.md        # 系统级经验
│
└── pycore/                          # Python 后端框架底座
```

---

## 项目工作区结构

每个项目都在 `Projects_Repo/<project-id>/` 下：

```text
Projects_Repo/<project-id>/
├── AGENTS.md                        # 项目级轻入口，提示返回 Harness 根目录
├── .sdd/                            # 项目状态脑子
│   ├── project.json                 # 项目元信息
│   ├── status.json                  # 当前阶段状态
│   ├── tasks.json                   # 任务状态机
│   ├── experience.md                # 项目级经验
│   ├── work-log.md                  # 工作日志
│   ├── bug_fix/                     # Bugfix 报告
│   └── test-reports/                # Tester 报告
│
├── docs/
│   ├── PRD.md
│   ├── api-contracts.md
│   ├── Plan.md
│   └── prototypes/
│
├── frontend/ / mobile/
├── backend/
└── ...
```

---

## 工作流总览

```text
平台入口自动注入 Harness Router
  │
  ├─ 读取 project-registry.json
  │
  ├─ 选择操作
  │   ├─ 新建项目
  │   ├─ 从 GitHub 克隆项目
  │   ├─ 继续已有项目
  │   ├─ 已有项目功能升级
  │   └─ Bugfix
  │
  ├─ 进入 Projects_Repo/<project-id>/
  │
  ├─ 判断项目形态
  │   ├─ Web：可走 alignment + sdd-product-design 全流程
  │   └─ 移动端：警告缺少移动端规范，用户确认后继续，可选业务场景对齐
  │
  ├─ 判断项目状态
  │   ├─ 缺 PRD / API / Plan → 产品设计或要求用户补齐
  │   └─ 文件齐全 → 多 Agent 开发
  │
  └─ Planner → Developer → Tester → Bugfix / Experience
```


## Codex 使用方式

在 Codex 中打开 Harness 根目录后，先读取：

```text
AGENTS.md
.codex/README.md
```

Codex 只保留一个手动命令适配：

```text
.codex/commands/sdd-bugfix.md
```

新建项目、需求对齐、开始开发、已有项目修整和删除项目都由 `harness-core/router.md` 根据自然语言意图分发，不要求用户手动触发命令。

Codex 子智能体配置：

```text
.codex/agents/planner.toml
.codex/agents/developer.toml
.codex/agents/tester.toml
```

如果当前 Codex 环境不支持自定义 subagent TOML，按 `harness-core/protocols/codex-subagents.md` 在主会话中模拟 Planner / Developer / Tester 的角色边界。

---

## WorkBuddy 使用方式

在 WorkBuddy 中打开 Harness 根目录后，`AGENTS.md` 会作为项目级指令自动注入，指向唯一入口 `harness-core/router.md`。

WorkBuddy 原生 Skill 入口（仓库内为版本化源，**需安装到用户级才生效**）：

```text
.workbuddy/skills/sdd-harness/SKILL.md
```

WorkBuddy 的技能发现根只有 `<configDir>`、`<configDir>/skills`、内置插件目录和 `<configDir>/skills-marketplace`，**不含当前工作区**。因此该 Skill 与子智能体一样采用双路径，需执行：

```bash
python scripts/install_workbuddy_skill.py          # 安装 / 更新
python scripts/install_workbuddy_skill.py --check  # 只校验
```

用户级 Skill 对所有工作区可见，故 `SKILL.md` 内置「阶段 0：工作区校验」，仅当当前目录存在 `harness-core/router.md` 与 `AGENTS.md` 时才接管，否则静默退出。

> **生效时机按链路区分**：子智能体安装后**即时生效**（实测新装角色当前会话即可调度）；入口 Skill 与斜杠命令需**新会话**；`AGENTS.md` 内容在会话启动时快照。跑 `python scripts/check_workbuddy_adapter.py` 可逐层确认实际状态。

WorkBuddy 与其余三端一致，**只保留一个手动命令** `sdd-bugfix`，位置为 `.codebuddy/commands/sdd-bugfix.md`：

```bash
/sdd-bugfix <问题描述>
```

> 目录名是 `.codebuddy` 而不是 `.workbuddy` —— WorkBuddy 的项目级斜杠命令目录在客户端被硬编码为 `.codebuddy/commands`（历史遗留名，已实测确认）。一致性检查会拦截误建的 `.workbuddy/commands/`。

新建项目、需求对齐、开始开发、已有项目修整、导入已有项目、删除项目，全部由 `harness-core/router.md` 根据自然语言意图分发。

WorkBuddy 子智能体以 Markdown + YAML frontmatter 声明，格式与 Claude Code 适配器一致。**关键差异**：运行时只从用户级 `~/.workbuddy/agents/` 发现子智能体，不加载项目内 `.workbuddy/agents/`。仓库内配置是版本化源，需同步后才生效：

```bash
python scripts/install_workbuddy_agents.py          # 安装 / 更新
python scripts/install_workbuddy_agents.py --check  # 只校验
```

三个角色配置：

```text
.workbuddy/agents/planner.md      -> harness-core/agents/planner.md    (EB-DeepSeek-Flash)
.workbuddy/agents/developer.md    -> harness-core/agents/developer.md  (EB-DeepSeek-Pro)
.workbuddy/agents/tester.md       -> harness-core/agents/tester.md     (EB-GLM-Pro)
```

编排规则见：

```text
harness-core/protocols/workbuddy-subagents.md
```

若子智能体仍无法拉起，先按该协议「调用前置条件」排查用户级安装，再考虑降级模式；不得改由主会话直接写功能代码。

> **注意**：`.workbuddy/memory/` 是 WorkBuddy 的宿主会话记忆，与 SDD 的两级经验体系（`.sdd/experience.md` + `memory/harness-experience.md`）是两套独立机制，不可互相替代。

---

## 核心变化

### 1. 所有项目统一放进 `Projects_Repo/`

无论是新建项目，还是从 GitHub 拉下来的项目，都放在：

```text
Projects_Repo/<project-id>/
```

V7.1 不管理任意外部路径，降低教学和使用复杂度。

### 2. `.sdd/` 替代 `.output/` 成为长期项目状态目录

V5 的 `.output/` 更像临时产物目录。V7.1 里：

- `docs/` 存设计文档
- `.sdd/` 存任务、状态、经验、日志、报告

### 3. 三级经验系统

```text
任务经验 → 项目经验 → 系统经验
```

- 任务经验：具体任务/bug 的局部经验
- 项目经验：当前项目长期有效的经验，写入 `.sdd/experience.md`
- 系统经验：跨项目可复用的 Harness 规则，写入 `memory/harness-experience.md`

经验可以上升，但必须带证据和用户确认。

### 4. 场景对齐层

`alignment` 是 V7.1 的业务口径对齐层，位于 PRD、技术合同、Planner 和 Bugfix 之前。

它负责把用户的大段想法、功能升级描述或产品口径型 Bug 整理成：

```text
docs/澄清文档/<feature-name>/01-alignment.md
```

它只写业务目标、范围、场景、验收口径和关键问题，不写技术方案、接口字段、组件拆分或开发任务。

### 5. Web / 移动端分流

- Web 项目：可以走产品设计 Skill，自动产出 PRD / 原型 / API 契约 / Plan
- 移动端项目：当前缺少移动端产品设计和开发 rules，必须警告并等待用户确认；用户需自行提供 PRD / 原型 / API 契约 / Plan

---

## 一句话架构

```text
SDD V7.1 Harness
  → Project Registry
    → Projects_Repo/<project-id>
      → Alignment
        → docs + .sdd
          → Product Design / Multi-Agent Development / Bugfix
            → Experience Promotion
              → Harness Evolution
```
