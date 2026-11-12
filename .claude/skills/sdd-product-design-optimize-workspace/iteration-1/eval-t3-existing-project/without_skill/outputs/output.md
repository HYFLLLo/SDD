# T3 · 已有项目加功能 → 路由判断（文字模拟）

> 模拟对象请求：
> 「我之前已经用你们的流程做了一个售楼管理系统，项目还在 Projects_Repo 里，现在想在这个老项目上加一个预约看房的功能，我要新建项目吗？」
>
> 已知：`active_project_path = Projects_Repo/sales-system/`，目录下已有
> `docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`.sdd/tasks.json`、`frontend/`。
>
> 本文件是**文字模拟**，不真实创建任何目录或业务产物文件。

---

## 1. 应该走哪个流程分支？

**已有项目修整（sdd-project-maintenance）分支**，不是「新建产品设计」，也不是「导入已有项目」，也不是「删除项目」。

- 顶层意图：用户是在**已有 SDD 项目上加功能**（加一个「预约看房」功能），对应 `router.md`「顶层意图路由」的第 2 分支：已有项目修整。
- 对应 Skill：`harness-core/skills/sdd-project-maintenance/SKILL.md`。
- 依据是 SKILL.md 自身声明：frontmatter 明确写着「本 Skill 只处理项目新建需求；**已有项目修改必须进入 sdd-project-maintenance**」。

---

## 2. 判定依据（哪些信号）

| # | 信号 | 内容 | 指向 |
|---|------|------|------|
| A | 用户用词 | 「在（这个）老项目上**加一个**（预约看房）功能」 | `router.md`「已有项目修整」典型信号里就有「加功能」 |
| B | 项目来历 | 「我已经**用你们的流程**做了」→ 该项目已是 SDD 流程创建并管理的项目，非外部代码库 | 排除第 3 分支「导入已有项目」（那是给非 SDD 代码库用的） |
| C | 项目目录非空 | `sales-system/` 已存在 `docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`.sdd/tasks.json`、`frontend/` | 全部命中 SKILL.md「不得视为空项目」清单，且命中「开发门禁」前四要素中的多组 |
| D | 产品设计产物齐全 | PRD + api-contracts + Plan + prototypes 均已就位 | 该项目的产品设计流程早已完成并进入开发，不在「从零新建」语义内 |
| E | Skill 边界 | sdd-product-design 明确「只处理项目新建需求」 | 非空项目上不得启动新建产品设计流程 |

依据 `router.md`：「顶层入口不要直接判断前端、后端、原型、PRD、Bugfix…… 必须先把用户的**项目级意图**归入且只能归入一个分支」。本请求归入第 2 分支。

---

## 3. 会不会说「要新建项目」？

**不会。明确告知：不需要新建项目。**

- 新建项目分支仅在「从零空项目」时成立；SKILL.md「入口前置检查」第 3 节规定：项目一旦带有 `docs/PRD.md` / `docs/api-contracts.md` / `docs/Plan.md` / `.sdd/tasks.json` / `frontend/` 等业务产物，就**不得视为空项目**，不得继续新建产品设计流程。
- 给用户的标准答复应是：

    ```text
    不需要新建项目。你的 sales-system 已经是 SDD 项目且产品设计已闭环、进入开发阶段；
    加「预约看房」属于在已有项目上扩展功能，会走「已有项目修整」分支
    （harness-core/skills/sdd-project-maintenance），而不是新建项目。
    ```

- 同时要**纠正用户提问里的预设**：用户问「我要新建项目吗」不一定认同你的流程身份认知，需要用简洁一句确认意图：将「加功能」归入修整分支，并请求从 `router.md` 切入点继续而非直接复用新建 Skill。

---

## 4. 会不会创建任何新的产物文件（如 PRD.md、prototypes/ 等）？

**不会。** 本任务明确要求文字模拟，不真实创建任何目录或业务产物文件。

即便进入真实流程，第一步动作也不允许创建 `PRD.md` / `docs/prototypes/` / 新建 `.sdd/tasks.json` 之类的文件：

- 这些文件**已经存在**于 `projects_Repo/sales-system/`，重复创建即覆盖/污染既有产物。
- 维护分支的正确动作是：读取 `harness-core/skills/sdd-project-maintenance/SKILL.md` → 做「已有项目状态检查 + 修整类型判断」→ 针对「预约看房」功能产出 **Delta Plan**（增量变更计划），在既有 PRD/api-contracts/Plan/tasks.json 上做增量更新，而不是重造一套产品设计文件。

「该走的分支的第一步动作」应为：

1. 明确告知用户不需要新建项目，路由到 `harness-core/skills/sdd-project-maintenance/SKILL.md`；
2. 读取该 Skill，按其前置检查做项目状态/修整类型判断；
3. 进入修整流程（增量设计与 Delta Plan），不动已有 PRD/prototypes 等完整产物。

---

## 5. 如果已（错误地）创建了这些文件，会违反什么规则？

| 违反点 | 被违反的规则 |
|--------|--------------|
| 在非空项目上继续「新建项目产品设计流程」 | 违反 sd-product-design/SKILL.md「不得视为空项目 → 必须转入已有项目修整分支」的入口前置检查 |
| 把「已有项目修改」路由进新建分支 | 违反 `router.md`「顶层意图路由」——「加功能」必须归入且只能归入一个分支（第 2 分支），且 SKILL.md frontmatter 明确「已有项目修改必须进入 sdd-project-maintenance」 |
| 新建或覆盖 `PRD.md` / `docs/prototypes/` 等文件 | 违反 SKILL.md「不得在用户不知情的情况下覆盖已有项目记录」，覆盖已有业务产物 |
| 为过程产物单独建文件 | 违反「精简产出：非必要不新增文件」全局规则 |
| 真的去建一个新项目承接该功能 | 把本应内聚在一个项目里的功能拆到新项目，违反 `router.md` Active Project Path 强制规则与项目内聚原则；且 `sales-system` 已注册，直接跑 `sdd_project.py new` 会命中「project_id 已存在」冲突处理 |

---

## 结论（一句话）

> 本请求走**已有项目修整**分支（`harness-core/skills/sdd-project-maintenance/SKILL.md`）；
> 明确告知用户**不需要新建项目**；不新建/覆盖任何 PRD、原型等产物文件，
> 第一步是读取维护分支 Skill 做修整类型判断与 Delta Plan；本模拟未创建任何真实业务文件。