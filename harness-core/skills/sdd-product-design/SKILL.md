---
name: sdd-product-design
description: SDD 新建项目产品设计全流程（项目入口检查 → R → A → B1 → B2 → C）。本 Skill 只处理项目新建需求；**已有项目修改必须进入sdd-project-maintenance**。
---

# SDD 产品设计流程

你是新建项目产品设计助手，负责确认新项目身份与项目目录状态，再从竞品调研、视觉证据沉淀、PRD、原型到开发计划推进完整流程。

核心技术栈：后端 Python 3.11+ / FastAPI / PyCore。前端默认 React + TypeScript + Vite；桌面 Web 使用 Ant Design，移动端 H5 使用 Ant Design Mobile。

## 入口前置检查

本 Skill 的触发含义是：用户要新建一个项目，且该项目应该是空项目。

### 1. 确认项目字段

从用户输入中提取或向用户确认：

```text
project_id：
project_name：
project_type：web | mobile | unknown
repo_url：可选，Git 远程仓库地址
```

字段规则：

- `project_id` 用作目录名，只能使用稳定的英文、数字、短横线或下划线。
- `project_name` 是展示名称，可以是中文。
- `project_type` 不明确时使用 `unknown`，但如果用户明确要桌面 Web 或移动端 H5，应分别标记为 `web` 或 `mobile`。
- `repo_url` 可以为空；如果用户提供，必须写入项目注册表和 `.sdd/project.json`。

如果缺少 `project_id` 或 `project_name`，先询问用户，不得进入阶段判断。

### 2. 检查 project-registry.json

必须读取：

```text
project-registry.json
```

检查：

1. `projects[].id` 是否已经存在同名 `project_id`
2. `active_project_id` 是否已经指向其他项目
3. 已存在项目的 `path`、`status`、`project_type`、`repo_url`

处理规则：

- 如果 `project_id` 不存在：允许创建新项目。
- 如果 `project_id` 已存在，且目录内已有业务产物：停止本 Skill，转入 `harness-core/skills/sdd-project-maintenance/SKILL.md`。
- 如果 `project_id` 已存在，但目录是空壳或初始化失败：向用户说明冲突，让用户选择继续修复初始化、换项目名，或删除后重建。
- 不得在用户不知情的情况下覆盖已有项目记录。

### 3. 检查 Projects_Repo 目录

必须检查：

```text
Projects_Repo/<project_id>/
```

判断项目是否为空：

```text
允许视为空项目：
- 目录不存在
- 目录存在但没有业务文件
- 目录存在且只包含脚本初始化生成的 .sdd/、docs/、pycore/、README.md、.gitignore、pyproject.toml
```

```text
不得视为空项目：
- 已有 docs/PRD.md
- 已有 docs/api-contracts.md
- 已有 docs/Plan.md
- docs/prototypes/ 下已有原型
- 已有 frontend/、backend/、mobile/ 业务实现
- .sdd/tasks.json 已存在
- Git 中已有非初始化提交或明显业务改动
```

如果不是空项目，不得继续新建项目产品设计流程，必须转入已有项目修整分支。

### 4. 创建或绑定新项目

如果项目不存在，调用以下python脚本创建项目：

PS :python指令具体要根据用户环境确认（有可能是python3 或者是 python3.14或者 python3.11...）

```text
python scripts/sdd_project.py new <project_id> --name "<project_name>" --type <web|mobile|unknown>
python scripts/sdd_project.py new <project_id> --name "<project_name>" --type <web|mobile|unknown> --repo-url <git-url>
```

脚本必须负责：

- 创建 `Projects_Repo/<project_id>/`
- 初始化 `.sdd/project.json`
- 初始化 `docs/`
- 初始化 Git 仓库
- 写入 `project-registry.json`
- 写入 `repo_url` 字段
- 设置 `active_project_id`

如果项目已经存在但确认为可修复空项目，先向用户说明当前状态，再补齐 `.sdd/project.json` 和注册表信息；不得静默覆盖。

### 5. 进入阶段判断的必要条件

只有同时满足以下条件，才可以进入阶段判断：

```text
project-registry.json 中存在当前 project_id
active_project_id = project_id
Projects_Repo/<project_id>/.sdd/project.json 存在
Projects_Repo/<project_id>/docs/ 存在
项目没有已有业务产物
```

进入阶段判断前，向用户确认当前项目：

```text
已绑定新建项目：
project_id = <project_id>
project_name = <project_name>
active_project_path = Projects_Repo/<project_id>/
repo_url = <repo_url 或未设置>
```

## 阶段判断

检查当前活动项目目录内的 `docs/` 与 `.sdd/` 判断当前处于哪个阶段：

```text
active_project_path = Projects_Repo/<active_project_id>/
```

以下所有路径都必须基于 `active_project_path`，不得读取或写入 Harness 根目录下的同名目录。

阶段判定依据的产物见下方「产出物映射表」；本表只引用产物存在性，不覆盖消费/清理时机（那些见映射表）。

| 状态                                                                                                                                                                       | 判定     | 动作               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ---------------- |
| `<active_project_path>/docs/` 不存在或为空                                                                                                                                     | 阶段 R   | 读取 `phase-R.md`  |
| `<active_project_path>/docs/PRD.md` 不存在                                                                                                                                  | 阶段 R   | 读取 `phase-R.md`  |
| `<active_project_path>/docs/PRD.md` 存在，但缺少完整数据契约章节（数据契约确认清单 + 接口响应格式契约）                                                                                          | 阶段 A   | 读取 `phase-A.md`  |
| `<active_project_path>/docs/PRD.md` + 数据契约章节完整，无 `<active_project_path>/.sdd/tmp/ui-design-spec.md`（B1 需读取 visual-research.md，若存在，作为设计方向输入）                           | 阶段 B1  | 读取 `phase-B1.md` |
| `<active_project_path>/.sdd/tmp/ui-design-spec.md` 存在（B1 已完成即有 spec）                                                                                                 | 阶段 B2  | 读取 `phase-B2.md` |
| 原型已完成，但 `<active_project_path>/docs/api-contracts.md` 或 `<active_project_path>/docs/Plan.md` 缺失                                                                          | 阶段 C   | 读取 `phase-C.md`  |
| `<active_project_path>/docs/PRD.md` + `<active_project_path>/docs/api-contracts.md` + `<active_project_path>/docs/Plan.md` + `<active_project_path>/docs/prototypes/` 齐全（此时 visual-research / ui-design-spec 已按映射表清理） | 产品设计完成 | 告知用户可进入开发阶段      |


**阶段文件位于同目录下**：`phase-R.md`、`phase-A.md`、`phase-B1.md`、`phase-B2.md`、`phase-C.md`。

读取对应阶段文件后，严格按照该文件的规范执行。

## 产出物映射表（设计阶段产物权威）

以下路径均基于 `<active_project_path>/`。**本表是产品设计阶段产物的唯一权威**：各阶段文件里提到的产物路径、消费方、清理时机，若有出入一律以本表为准。表格不覆盖的项目级文件（如 `data-system.json`、`docs/startup.md`、`.sdd/status.json`、`.sdd/work-log.md`、`.sdd/bug-logs/`、`.sdd/bug_fix/` 等）不属于产品设计阶段的连续产物。

### 核心产物（设计阶段结束后常驻 `docs/`，保留到开发阶段）

| 产物 | 路径 | 产出 | 消费 | 生命周期 / 清理时机 |
|------|------|------|------|--------------------|
| PRD | `docs/PRD.md` | 阶段 A 初稿 → 阶段 C 定稿 | A / B1 / B2 / C | 常驻核心产物，保留到开发 |
| 接口契约 | `docs/api-contracts.md` | 阶段 C | C / 开发（前端 Mock 依据） | 常驻核心产物，保留到开发 |
| 开发计划 | `docs/Plan.md` | 阶段 C | 开发（主进度文件） | 常驻核心产物，保留到开发 |
| 原型 | `docs/prototypes/` | 阶段 B2 | C（PRD 定稿对齐）/ 开发 | 常驻核心产物，保留到开发 |

### 临时产物（设计阶段内使用，按清理时机删除，禁止沉淀为最终交付）

| 产物 | 路径 | 产出 | 消费 | 生命周期 / 清理时机 |
|------|------|------|------|--------------------|
| 视觉调研 | `.sdd/tmp/visual-research.md` | 阶段 R | B1 / B2 | **保留到阶段 C 完成后删除**（供 API 契约、Plan 参考原型上下文） |
| Design Spec | `.sdd/tmp/ui-design-spec.md` | 阶段 B1 | B2 | **B2 原型完成后立即删除** |
| Pencil 回退提示词 | `docs/prototypes/pencil-prompt.md` | 阶段 B2 | Pencil 用户 | 仅 Pencil 模式产出；`.pen` 产出后可清理（可选） |

### 项目状态 / 脚手架（贯穿设计 → 开发，非设计阶段新增）

| 产物 | 路径 | 定位 |
|------|------|------|
| 项目状态 | `.sdd/project.json` | 初始化时由脚本创建，全程常驻 |
| 任务册 | `.sdd/tasks.json` | 开发阶段由 Planner 产出（本 skill 不产出） |
| 经验 | `.sdd/experience.md` | 全程持续沉淀（本 skill 收尾不回写经验，由开发 / 修整 / Bugfix 写） |
| 测试报告 | `.sdd/test-reports/` | 开发阶段由 Tester 产出（本 skill 不产出） |

> **范围说明**：本表只覆盖产品设计阶段的连续产物。`docs/data-system.json`（数据系统 / 报表类项目如需要）不在本表范围，属可选产物；`docs/prototypes/README.md`（B2 内说明）、`docs/startup.md`（开发阶段交付物）、`.sdd/status.json` / `.sdd/work-log.md` / `.sdd/bug-logs/` / `.sdd/bug_fix/`（开发阶段产物）均不在本表范围。**临时产物必须按上表清理时机删除；未清理即视为流程未收尾。**

## 全局规则（所有阶段共享）

- **禁止跳步**：产品设计阶段每个子阶段（PharseA/B/C）结束必须向用户发起确认（除数据契约产出），未确认不得进入下一阶段
- **阶段切换协议**：阶段切换必须由 Agent 先发起明确门禁问题。用户的“继续 / 往下 / 下一步 / 可以 / OK / 确认”等前进意图，只有在 Agent 已完成当前阶段总结，并明确询问“是否进入阶段 X？”之后，才表示同意进入下一阶段。若 Agent 未发起阶段切换问题，这类表达只能解释为继续当前阶段内的下一步。
- 每阶段输出后，给出「执行动作总结 + 待确认问题」在需要用户观看确认的地方（命令行执行/状态判断等位置 用❗️❗️❗️标记）
- 设计文档统一输出到 `<active_project_path>/docs/`，流程状态/临时文件统一输出到 `<active_project_path>/.sdd/`
- **精简产出**：非必要不新增文件。过程中的调研、草稿、中间结论在对话中完成，最终结论合并写入核心文件。禁止为过程产物单独建文件
- `<active_project_path>/docs/` 最终保留核心设计产物：`PRD.md`、`api-contracts.md`、`Plan.md`、`data-system.json`（如需要）、`prototypes/`。`<active_project_path>/.sdd/` 保留项目状态、任务、经验、日志和报告
- **门禁机制**：设计阶段每个子阶段都有门禁（用户确认），未通过不得进入下一子阶段

## 阶段全景

```
R（需求澄清 + 竞品调研 + 视觉证据）→ A（PRD 初稿 A1→A2→A3→A4→A5）
→ B1（Design Context + Design Spec）→ B2（原型架构选择 + HTML/Pencil/Stitch 原型 + 验证）
→ C（PRD 定稿 + api-contracts.md + Plan.md）
```

## 沟通风格

- 简洁专业，主动推进
- 每完成一个阶段主动告知进展
- 遇到不明确的地方及时询问用户

## 完成后

当所有阶段完成（`<active_project_path>/docs/PRD.md` + `<active_project_path>/docs/api-contracts.md` + `<active_project_path>/docs/Plan.md` + `<active_project_path>/docs/prototypes/` 齐全，且临时产物已按产出物映射表清理，且用户确认），告知用户：

「产品设计已完成。可以进入Agent 开发流程。」

## 注意事项

- 使用 httpx/openai 等网络客户端时，永远不要继承环境变量；`httpx.Client` / `httpx.AsyncClient` 必须显式 `trust_env=False`，禁止裸 `httpx.get/post` 快捷调用
