# 模拟执行报告：老项目新增「预约看房」功能

- 模拟 Agent 依据：`sdd-product-design` SKILL.md + phase-R.md（入口前置检查/阶段判断）+ `router.md`（顶层意图路由）+ 维护分支 `sdd-project-maintenance/SKILL.md`
- 模拟假设：`active_project_path = Projects_Repo/sales-system/`，已存在 `docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`.sdd/tasks.json`、`frontend/`
- 模式：文字模拟，未创建任何目录或业务文件

## 1. 这个请求应该走哪个流程分支？

**已有项目修整分支（`harness-core/skills/sdd-project-maintenance/SKILL.md`），不是新建产品设计。**

## 2. 依据是什么？

判定信号（多规则层层印证）：

1. **前置检查直接命中停止条件**：`sdd-product-design/SKILL.md`「入口前置检查」第 2 节规定——`project_id` 已存在、且目录内已有业务产物时，"停止本 Skill，转入 `harness-core/skills/sdd-project-maintenance/SKILL.md`"。`sales-system` 在 `project-registry.json` 中必然已存在（用户说"项目还在 Projects_Repo 里"），且目录内满是业务产物。
2. **「不得视为空项目」清单全数命中**：SKILL.md 第 3 节列举了 7 项"不得视为空项目"信号——`docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`docs/prototypes/`、`frontend/ backend/ mobile/` 业务实现、`.sdd/tasks.json`、Git 非初始化提交。假设目录已具备 PRD / api-contracts / Plan / tasks.json / frontend 共 5 项，命中超过半数，绝不可能是空项目。
3. **SKILL 本身的性质限定**：SKILL.md 的 description 明确写"本 Skill 只处理项目新建需求；**已有项目修改必须进入 sdd-project-maintenance**"；同时"入口前置检查"第 5 节有一条硬条件"项目没有已有业务产物"，不满足则不得进入阶段判断。
4. **顶层意图路由的典型信号**：`router.md`「已有项目修整」分支把「加功能」列为典型信号，本请求就是给现有售楼系统"加一个功能"；而「新建项目」分支的典型信号（新建/创建/从零开始/初始化）没有任何一条命中。
5. **维护分支自身的目标**：`sdd-project-maintenance/SKILL.md` 的"目标"就是"修改一个已有 SDD 项目""产出聚焦的 Delta Plan，只修改受影响文件"；其「何时使用」明确列出"增加功能"；其「约束」写明"用户要求修改已有项目时，**不能创建新项目**"。

这一判断里完全没有歧义点：五个规则层全部一致指向维护分支。

## 3. 你说不说"要新建项目"？

**明确不说。** 会在回复中直接告知用户：这是已有 SDD 项目，**不需要新建项目**，应走"已有项目修整"分支。同时按维护分支的「必要输入」，先确认修改的三个关键信息：

- 目标项目：`sales-system`（用户已给出）
- 希望修改什么：新增「预约看房」功能（用户已给出方向，但需进一步澄清需求）
- 当前项目阶段 / 期望改的是原型、前端、后端、测试还是文档（需追问，或由维护 Skill 先读状态再判断）

## 4. 你会不会创建任何新的产物文件（PRD.md、prototypes/ 等）？

**不会。** 模拟流程里的动作是：

- 第一步：读取 `project-registry.json` 确认 `sales-system` 状态（只读）
- 第二步：读取 `Projects_Repo/sales-system/.sdd/`、`docs/PRD.md`、`docs/Plan.md`、`docs/api-contracts.md`、`docs/prototypes/`、`frontend/`（只读）
- 第三步：按维护 Skill「经验回查」读 `docs/experience.md` 与系统级 `memory/harness-experience.md`（只读）
- 第四步：产出**对话内**的聚焦 `Delta Plan`（修整目标 / 影响范围 / 要读的文件 / 要改的文件 / 验证方式），这是文本模拟、不落盘，或按维护 Skill 只在正式执行时才增量同步进现有 PRD/api-contracts/Plan——绝不新建 PRD.md、绝不新建原型目录。
- 修整过程中新增的原型、Design Spec 若确有需要，只会**增量进入现有文档**，而不是像新建流程那样从阶段 R/A/B/C 全新建一遍。

## 5. 如果已经创建了，会违反什么规则？

假设错误地走了新建分支并创建了产物，会同时违反：

1. **`sdd-product-design/SKILL.md` 的记录保护规则**："不得在用户不知情的情况下覆盖已有项目记录"——`sales-system` 已有注册与产物，再跑 `sdd_project.py new` 属于静默覆盖既有项目。
2. **同文件「禁止对已有项目重跑新建流程」**：项目不空仍继续新建，违反"如果不是空项目，不得继续新建项目产品设计流程，必须转入已有项目修整分支"。
3. **同文件「精简产出」与产出物映射**：为已有项目重写 `docs/PRD.md`、重建 `docs/prototypes/`、生成 `.sdd/tmp/visual-research.md` 等，就是把"已有项目的常驻核心产物"当新项目产物再生成一遍，属于重复/覆盖产物，违反"非必要不新增文件""禁止为过程产物单独建文件"，也违背"临时产物必须按清理时机删除"的收尾要求。
4. **维护分支 `sdd-project-maintenance/SKILL.md` 的「约束」**：明文规定"用户要求修改已有项目时，**不能创建新项目**"；同时维护分支"只读本次修改需要的文件，不做大范围重写"、目标"不是重新启动完整新建流程"，全新建一套文档与此直接冲突。
5. **router.md「开发门禁」与"给定空项目"的前提**：新建分支的前置是"从零空项目"，`sales-system` 实际已是开发中项目（PRD/契约/Plan/tasks/frontend 齐全），硬建会污染既有已确认文档与注册表，后续维护的 Delta Plan 无从锚定。
6. **范围纪律**：维护 Skill 要求"聚焦修整任务时，不改无关文件"，全新建产物必然改写无关文件；收尾本应"把本次经验写回 `.sdd/experience.md`"，但全程未走维护分支时这套回写闭环「经验沉淀链条」也会断裂。

## 结论：该走分支与第一步动作

- **分支**：已有项目修整（`harness-core/skills/sdd-project-maintenance/SKILL.md`）
- **第一步动作**：以维护分支的「状态检查 + 必要输入」为入口——读 `project-registry.json`、`.sdd/`、`docs/PRD.md`、`docs/Plan.md`、`docs/api-contracts.md`、`docs/prototypes/`、`frontend/`，确认 `sales-system` 当前阶段；随后按维护 Skill 进入「前端功能修改 / API 后端修改 / UI 原型修改」的具体修整判断（本请求最可能是前端 + 后端的小改/中改，视"预约看房"范围决定是否转多智能体开发循环，由 Planner 增量写 `.sdd/tasks.json`）。全程不新建项目、不重跑完整需求澄清、不新建 PRD/原型产物。