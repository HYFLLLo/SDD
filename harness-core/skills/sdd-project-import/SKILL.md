---
name: sdd-project-import
description: SDD 导入已有项目流程。把一个非 SDD 创建的已有代码库纳入 SDD 管理：定位代码、注册项目、补齐 .sdd 脚手架、反向梳理 PRD/接口契约/Plan 到可继续开发的状态，然后转入修整或开发循环。
---

# SDD 导入已有项目 Skill V7.1

## 目标

当用户已经有一个**不是 SDD 创建**的代码库（自己写的 / 别处迁来的 / 旧项目），希望纳入 SDD 管理继续开发时，使用本 Skill。

目标不是从零新建，也不是直接改代码，而是：先把已有代码**纳管 + 反向补齐设计文档**，让它达到「SDD 可接管」的状态，再转入修整或多智能体开发。

## 何时使用

进入导入分支的典型信号：

- 把已有项目接入 SDD / 用 SDD 管理这个老项目
- 这是我之前写的代码，想用这套流程继续做
- 导入 / onboard 一个现成代码库

不要把以下情况路由到导入：

- 全新空项目（→ 新建项目 `sdd-product-design`）
- 已经是 SDD 项目、只是要改（→ 已有项目修整 `sdd-project-maintenance`）
- 删除项目（→ `sdd-project-delete`）

## 必要步骤

### 1. 确认项目身份与代码位置

向用户确认：

```text
project_id：用作目录名，英文/数字/短横线/下划线
project_name：展示名，可中文
project_type：web | mobile | unknown
repo_url：可选，远程仓库地址
代码当前在哪里：路径或仓库地址
```

代码必须先就位到 `Projects_Repo/<project_id>/`：

- 如果用户代码在别处，先让用户复制或 `git clone` 到 `Projects_Repo/<project_id>/`（Agent 可代为执行 clone/cp，需用户确认）。
- 不得把业务代码留在 Harness 根目录或其它位置后再硬连接。

### 2. 注册并补齐脚手架（不覆盖已有代码）

代码就位后，调用脚本导入（脚本只补缺失的 `.sdd/` 脚手架，绝不覆盖已有业务文件，也不会复制 pycore 覆盖用户后端）：

```text
python scripts/sdd_project.py import <project_id> --name "<project_name>" --type <web|mobile|unknown>
python scripts/sdd_project.py import <project_id> --name "<project_name>" --type <web|mobile|unknown> --repo-url <git-url> --configure-git
```

> Python 指令按 Router「运行时检测」确认实际命令，不写死。

脚本会：注册到 `project-registry.json`、补齐 `.sdd/project.json`（`source=import`）、`status.json`、`experience.md`、`work-log.md`，并设为 active。已存在的 `docs/`、`frontend/`、`backend/` 等保持原样。

### 3. 摸清现状（反向理解）

只读必要文件，建立代码地图：

1. 技术栈与目录结构（前端框架、后端框架、数据库）
2. 入口、路由、主要页面 / 接口
3. 已有的 README / 文档 / 配置（`.env.example` 等）
4. 与 SDD 默认栈（React+TS+Vite / FastAPI+PyCore）的差异

向用户汇报现状摘要与差异，不擅自重构去贴合默认栈。

### 4. 反向补齐设计文档（按需，最小充分）

根据用户接下来要做的事，反向补齐 SDD 接管所需文档，缺什么补什么，不强制全量重写：

- `docs/PRD.md`：从代码与用户描述反推核心功能、页面、关键链路；标注「由已有代码反向整理」。
- `docs/api-contracts.md`：整理已有接口的请求/响应；统一响应格式如与现状不符，记录差异而非强行改造。
- `docs/Plan.md`：列出当前已实现 / 待开发清单。
- PRD「A5-3 外部依赖与配置草稿」：扫描代码中的外部依赖（LLM、第三方 API、支付、存储、OAuth 等）与 `.env` 字段，整理成草稿交用户确认。

每补一份都向用户确认口径，避免反推失真。

### 5. 转交后续流程

纳管与文档补齐到位后，按用户意图转交：

- 要继续小步修改 → `harness-core/skills/sdd-project-maintenance/SKILL.md`
- 要成体系新增功能并自动开发 → 满足 router「开发门禁」后进入 Planner → Developer → Tester
- 要先修 Bug → `harness-core/skills/sdd-bugfix/SKILL.md`
- 要评估这套代码离规范有多远 → `harness-core/skills/sdd-code-review/SKILL.md`

**建议默认动作**：纳管完成后先做一次基线代码审查（`review-sprint-YYYYMMDD.md`），把存量问题按 `Blocker / Major / Minor / Nit` 分级登记。这条基线清单是后续修整排期的依据，也避免后续每次改动都重新发现同一批老问题。

基线审查属建议而非强制；若用户明确只要纳管、不做审查，需把「未做基线审查」记入 `.sdd/work-log.md`。

## 约束

- 不覆盖、不擅自重构用户已有代码；纳管阶段只增不改业务逻辑。
- 不把已有项目当空项目跑完整新建流程。
- 反向补齐的文档必须标注来源（由已有代码整理），并经用户确认。
- 真实 Key / Secret 只进 `.env`；反推 contracts/PRD 时只写字段名与状态。
- 代码未就位到 `Projects_Repo/<project_id>/` 前，不得执行 import。
