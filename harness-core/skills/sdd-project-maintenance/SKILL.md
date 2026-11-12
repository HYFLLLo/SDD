---
name: sdd-project-maintenance
description: SDD 已有项目修整流程。用于已有 SDD 项目的加功能、改版、改接口、重构、修文档、继续中断的项目；读取现有状态与经验，产出聚焦 Delta Plan，只改受影响文件，必要时转多智能体开发循环，收尾回写经验。
---

# SDD 已有项目修整 Skill V7.1

## 目标

当用户要修改一个已有 SDD 项目时，使用本 Skill。

目标不是重新启动完整新建流程，而是读取现有项目状态，理解用户要改什么，产出聚焦的 Delta Plan，然后只修改受影响文件。

## 何时使用

以下情况进入已有项目修整分支：

- UI 改版或页面优化
- 增加功能
- 修改已有功能
- 接入或调整 API
- 重做原型或 Design Spec
- 重构实现
- 更新文档或验收标准
- 继续一个中断的 SDD 项目

以下情况**不进入**本分支，必须转对应 Skill：

- 修复 Bug（行为异常、报错、测试失败、页面不对）→ `harness-core/skills/sdd-bugfix/SKILL.md`
- 业务口径还没定清 → `harness-core/skills/alignment/SKILL.md`
- 视觉一致性走查 → `harness-core/skills/ui-design-standard/SKILL.md`
- **纯结构调整、要求行为不变**（重构 / 解耦 / 抽公共组件 / 还技术债）→ `harness-core/skills/sdd-refactor/SKILL.md`。判据只看一条：用户是否接受「改完功能表现一模一样」。接受是重构，不接受是修整。
- 项目已开发完、要交付给用户 → `harness-core/skills/sdd-release/SKILL.md`

进入本分支前，先跑一次只读巡检确认现状（见 `harness-core/router.md`「项目状态巡检」）。`ERROR` 级问题会直接改变修整方案——例如 `.env.production` 未被 gitignore 覆盖、`tasks.json` 带 BOM 解析失败，都属于先修环境再谈功能的情况。

## 必要输入

修改文件前，必须确认：

1. 目标项目名或路径
2. 用户希望修改什么
3. 当前项目阶段，如果能读取到
4. 用户期望改的是原型、前端、后端、测试还是文档

如果目标项目不明确，先询问项目名或路径。

## 状态检查

做决策前先读取现有项目：

1. `project-registry.json`
2. `Projects_Repo/<project>/.sdd/`
3. `Projects_Repo/<project>/docs/PRD.md`
4. `Projects_Repo/<project>/docs/Plan.md`
5. `Projects_Repo/<project>/docs/api-contracts.md`
6. `Projects_Repo/<project>/docs/prototypes/`
7. `Projects_Repo/<project>/frontend/`
8. `Projects_Repo/<project>/backend/` 或 `pycore/`
9. `Projects_Repo/<project>/.sdd/tasks.json`

只读取本次修改需要的文件，不做大范围重写。

## 经验回查（改动前必做）

动手改任何代码前，先查经验，避免重复踩坑（与 Bugfix「先查经验」一致）：

1. 读取项目级 `Projects_Repo/<project>/.sdd/experience.md`，检索与本次修整相关的历史坑与避坑规则。
2. 读取系统级 `<harness 根>/memory/harness-experience.md`，确认是否有跨项目通用教训适用于本次修整（如 Vite 代理、Mock 切真实、pycore 合规、固定高度容器缓冲等）。
3. 如果命中相关经验，必须在 Delta Plan 中明确「本次如何应用该经验/避免重犯」。

## 修整分支

### UI / 原型修改

用户要求改视觉风格、布局、页面结构、交互或原型时，进入此分支。

步骤：

1. 读取 `docs/prototypes/`，如存在则读取 `.sdd/tmp/visual-research.md`。
2. 只为相关功能读取 `docs/PRD.md` 和 `docs/Plan.md`。
3. 必要时更新 Design Spec 或原型。
4. 如果已有生产前端，必须保持原型和生产代码的边界。
5. 尽可能用浏览器或 Playwright 做视觉验证。

### 前端功能修改

用户要求改页面行为、状态、路由、组件或 mock 数据时，进入此分支。

步骤：

1. 读取前端技术栈和 scripts。
2. 读取受影响的页面、组件、store、service、types。
3. 生产前端默认保持 React + TypeScript + Vite。
4. 后端契约未就绪时，先用 mock 数据闭环。
5. 可用时运行 type-check、lint、build。

### API / 后端修改

用户要求新增或调整数据契约、接口、服务或后端逻辑时，进入此分支。

步骤：

1. 读取 `docs/api-contracts.md`。
2. 读取受影响的后端 routes、services、models。
3. PyCore 响应格式保持 `code`、`message`、`data`。
4. 如果契约变化，同步更新前端 service 和 types。
5. 可用时运行后端测试或 smoke check。

### Bugfix（受限子分支）

**默认不走本子分支。** 用户报告的是行为异常、测试失败、运行时报错、页面不对、功能不生效或 UI 错位时，即使项目是已有 SDD 项目，也必须走独立 Skill：

```text
harness-core/skills/sdd-bugfix/SKILL.md
```

原因：独立 Bugfix Skill 有强制链路（记录用户原话 → 产品口径门禁 → 读上下文 → 经验回查 → 重复犯错六问 → 根因分析 → 修复 → 验证 → 报告落盘 `.sdd/bug_fix/` → 回写 experience.md），本子分支只有 5 步简版，缺少经验回查与重复犯错分析，用它修 Bug 会让「同一个坑反复踩」失去拦截点。

本子分支**只允许一种情形**：本次修整任务执行过程中**连带发现的、与本次改动直接相关**的小问题（不修就会让本次改动不成立）。

此时步骤：

1. 复现或检查失败现象。
2. 定位最小影响范围。
3. 修原因，不只修表象。
4. 查 `.sdd/experience.md` 是否有同类历史经验；若命中，必须说明本次为何仍会发生。
5. 运行最窄但有效的验证。
6. **必须落 `.sdd/bug_fix/YYYYMMDD-HHMM-问题简述.md` 报告**，结构参照 `sdd-bugfix` Skill 的 Step 9。
7. 汇报修了什么、验证了什么。

判据：如果这个问题在本次修整之前就已存在、用户也单独提过，它就不属于「连带发现」，必须转 `sdd-bugfix`。

### 文档 / Plan 修改

用户要求调整 PRD、Plan、tasks、验收标准或课程框架表述时，进入此分支。

步骤：

1. 读取当前文档。
2. 只更新用户要求的章节。
3. 版本命名统一为 V7.1。
4. technical checks 和 acceptance criteria 必须分开。

## Delta Plan

较大修改前，先产出短 Delta Plan：

```text
修整目标：
影响范围：
要读的文件：
要改的文件：
验证方式：
```

非常小的修复可以用一句话说明 Delta Plan。

## 小改 vs 大改：是否转开发循环

> **本节是本框架「小改 / 中间改 / 大改」判定的唯一权威源。**
> `harness-core/router.md`「开发循环启用判断」只给三档结论与指针，不重述判定正文。新增或调整判定维度时**只改本节**。

根据 Delta Plan 的影响范围、风险和验收可控程度选择执行方式。**不以用户是否说出「开始开发 / 进入开发阶段」等授权词作为唯一判断条件。**

判定时看四个维度，不做纯文件数 / 字数死扣：

| 维度 | 小改倾向 | 中间改倾向 | 大改倾向 |
| ---- | -------- | ----------- | -------- |
| 范围 | 单侧、单点、单页 / 单接口 | 跨前后端，或少量接口 / 页面 | 新增完整功能，跨多页面 / 多接口 / 多模块 |
| 风险 | 无数据、权限、事务、缓存、外部依赖风险 | 无高风险，只读已有数据或加简单字段 | 改数据库结构 / 关联表、改权限、涉及事务 / 缓存一致性、引入新外部服务 |
| 需求确定性 | 边界清晰，一次说清 | 边界清晰，可一次性闭环 | 边界不清、存在多方案或需架构决策 |
| 验收可控性 | 一条最窄命令即可验证 | 一组接口 / 构建 / 单页路径可闭环 | 需要跨模块联调、真实外部服务或人工业务验收 |

- **小改（直接执行）**：单点 UI/文案/样式、单个 Bug、单个接口字段、文档调整等。由本 Skill 直接读受影响文件并改，跑最窄验证即可，不进多智能体循环。
- **中间改（可先说明再直接执行）**：跨前后端或涉及少量接口，但没有数据结构变更、权限变更、事务风险、缓存风险、外部依赖等高风险项，且能用一组接口/构建验证闭环。主会话应先给出一句话判断和验证方式，然后直接执行；完成后按本 Skill 收尾回写经验。
- **大改（转开发循环）**：新增完整功能、跨多页面/多接口改版、改数据库结构或关联表、涉及权限/缓存/事务、引入新外部服务、需求边界不清晰，或用户明确要求走多智能体。必须先把改动落成增量任务，再走多智能体开发：
  1. 把 Delta Plan 增量同步进 `docs/PRD.md` / `docs/api-contracts.md` / `docs/Plan.md`（只增量，不重跑完整新建流程）。
  2. 如涉及新外部依赖，更新 PRD「A5-3 外部依赖与配置草稿」并与用户确认（接 router 开发门禁第 7 条）。
  3. 由 Planner 把增量写成 `.sdd/tasks.json` 新任务，按 `harness-core/protocols/development-rules.md` 与平台子智能体协议跑 Planner → Developer → Tester。
  4. 大改 Tester PASS 之后、`user_gate=true` 之前，必须按 `harness-core/skills/sdd-code-review/SKILL.md` 做代码审查；Blocker 未关闭不得交给用户验收。
  5. 满足 router「开发门禁」后才进入开发循环；不得在主会话直接堆功能代码绕过角色边界。

- **拿不准**：先向用户说明「建议直接执行」或「建议走 Planner → Developer → Tester」及理由，让用户一句话确认；不默认跳过角色边界，也不默认把简单需求复杂化。

## 收尾：回写经验（必做）

修整完成后：

1. 把本次踩到的坑、修复要点、后续避坑写入项目 `.sdd/experience.md`。
2. 如果是**跨项目通用**的新教训（不只本项目），在 `.sdd/experience.md` 标注 `[SYSTEM] 建议回传系统级经验`，由 Orchestrator 回传 `<harness 根>/memory/harness-experience.md`（与 Developer/Tester 的系统级经验回传链一致）。

## 约束

- 用户要求修改已有项目时，不能创建新项目。
- 除非产品目标变化，否则不要重新跑完整需求澄清。
- 不覆盖用户已有改动。
- 未进入删除项目分支并获得确认前，不能删除项目文件。
- 聚焦修整任务时，不改无关文件。
