# SDD V7.1 Skill 全景梳理、覆盖盲区与新增建议

> 分析对象：`harness-core/`（唯一真相源）+ 四端适配层 + `Projects_Repo/` 三个在管真实项目
> 分析日期：2026-10-27

---

## 落地进度

| 批次 | 内容 | 状态 |
| ---- | ---- | ---- |
| 第 1 批 | `sdd-code-review` + F1 Bugfix 入口统一 + F2 alignment 路由 | 已完成（2026-10-27） |
| 第 2 批 | `sdd-experience-governance` + F3~F8 规则去重 | 已完成（2026-10-28） |
| 第 3 批 | `sdd-release`（含 F9）+ `sdd-refactor` + `check_project_state.py` | 已完成（2026-10-28） |
| 第 4 批 | `sdd-db-migration` / `sdd-quality-audit` / `sdd-mobile-standard` | 未开始（按需触发） |

第 2 批执行结果见 §10，第 3 批见 §11。

---

## 0. 结论摘要

1. **现有 8 个 Skill，全部集中在流程的上游（需求→设计→开发启动）与运维旁路（项目增删改），流程中段只有"验收验证"一道关口，缺失"代码审查"与"发布交付"两个标准阶段。**
2. **验证与审查被混为一谈**：Tester 的设计原则明确写了 `Test the contract, not preferences`，它按 `acceptanceCriteria` 验收，不评判架构、可维护性与一致性。Developer 的"输出前必查清单"是自审。三个项目累计 40 份 `test-reports`、4 份 `bug_fix`，**代码审查报告为 0 份**。
3. **经验系统的写入链完备、维护链缺失**：`draw-telephone/.sdd/experience.md` 已达 **60,944 字节**，`creator-topic-library` 为 12,997 字节。Developer 每次"开始工作前"全量读取，无去重、无失效标记、无晋升校验。经验沉淀是 V7.1 的核心差异点，却是唯一无治理机制的核心资产。
4. **8 处规则复制**（端口、密钥红线、Mock 验收禁区、小改/大改判定等），其中"端口约定"被复制到 5 个文件；已有 `development-rules.md` 声明为权威源，但正文仍各自重写，改一处必漏一处。
5. **1 处路由歧义**：用户说"修 bug"时，`router.md` 将其导向 `sdd-project-maintenance`，而 `/sdd-bugfix` 命令导向独立 Skill，`maintenance` 内部又含 Bugfix 子分支——同一意图三处入口。
6. **1 处可达性缺口**：`alignment` Skill 未被 `router.md` 任何分支引用，只能由 `phase-R`、`bugfix`、`AGENTS.md` 旁路触达。

**优先落地建议（P0）**：`sdd-code-review`、`sdd-experience-governance`。

---

## 1. 现有 Skill 全清单（按流程阶段归类）

### 1.1 阶段映射总表

| # | Skill | 流程阶段 | 规模 | 触发方式 |
|---|-------|----------|------|----------|
| 1 | `alignment` | 需求分析 | 117 行 | 旁路引用（**Router 未路由**） |
| 2 | `sdd-product-design` | 需求分析 → 方案设计 | 6 文件 / 977 行 | Router 分支 1 |
| 3 | `ui-design-standard` | 方案设计（原型底线） | 84 行 | `phase-B2` 强制加载 |
| 4 | `sdd-project-import` | 项目纳管（前置） | 67 行 | Router 分支 3 |
| 5 | `sdd-project-maintenance` | 变更管理（跨阶段） | 101 行 | Router 分支 2 |
| 6 | `git-workflow` | 编码实现 → 交付（仅到 push） | 239 行 | `developer.md` 第 7 步 |
| 7 | `sdd-bugfix` | 测试验证 → 修复 | 202 行 | `/sdd-bugfix` 命令 + 自然语言 |
| 8 | `sdd-project-delete` | 项目生命周期末端 | 78 行 | Router 分支 4 |

### 1.2 逐项说明

#### ① `alignment` — 业务口径对齐

- **核心用途**：把用户的大段需求、抱怨、bug 描述整理成**不含技术方案**的业务 PRD 对齐稿，快速锁定"用户真实想要什么"。
- **适用场景**：新 Web 项目进入产品设计前、已有项目功能升级前、产品口径型 Bugfix、用户明确说"整理需求/对齐场景"。
- **关键边界**：不写数据库/接口字段/组件拆分/开发任务；最多提 1-3 个带推荐答案的问题。
- **产出**：`docs/澄清文档/<feature>/01-alignment.md`
- **实测问题**：`router.md` 的四个顶层分支（新建/修整/导入/删除）均未引用本 Skill。它实际只通过 `phase-R.md` 的"若输入很长则转入 alignment"、`sdd-bugfix` Step 2、`AGENTS.md` 第 85 行三处旁路触达。**用户若在 Router 层直接说"帮我把需求理一下"，不会被路由到它。**

#### ② `sdd-product-design` — 新建项目产品设计全流程

- **核心用途**：驱动 `R（需求澄清+竞品调研+视觉证据）→ A（页面→功能→版本→PRD）→ B1（Design Spec）→ B2（原型）→ C（PRD 定稿+接口契约+Plan）` 五阶段，每阶段一道用户门禁。
- **适用场景**：从零空项目。
- **入口强校验**：先查 `project-registry.json` 与 `Projects_Repo/<id>/` 是否为空项目；已有业务产物则**强制转入 maintenance**。
- **产物权威表**：`SKILL.md` 内的「产出物映射表」是设计阶段产物的唯一权威（含临时产物清理时机：`ui-design-spec.md` 在 B2 后立即删，`visual-research.md` 保留到 C 完成后删）。
- **子阶段文件**：`phase-R.md`、`phase-A.md`、`phase-B1.md`、`phase-B2.md`、`phase-C.md`。
- **最重的 Skill**：977 行，占全部 Skill 代码量的 51%。

#### ③ `ui-design-standard` — 原型设计底线

- **核心用途**：定义 B2 阶段不可退让的设计底线：设计上下文优先、字阶、圆角密度、布局效率、全中文、色彩对比、**反 AI slop 清单**、交互五态、原型与生产前端边界、验证清单。
- **适用场景**：B2 原型阶段强制加载；也是唯一对"视觉质量"下硬约束的地方。
- **特点**：不固定审美风格，但给出 5 类默认规避元素（紫渐变、emoji 当图标、圆角卡片+左 border、SVG 手画人物、系统字体当 display）与"真图诚实性测试"。
- **实测问题**：`frontend.md` 第 11 节的「Design Context 提炼」与本 Skill 的「设计上下文优先」语义重叠，但两者**措辞不同、默认基底表述不同**（前者按项目类型给 Ant Design/Ant Design Mobile，后者按"桌面 Web / 移动 H5 / 课程页"三分）。

#### ④ `sdd-project-import` — 已有代码库纳管

- **核心用途**：把非 SDD 创建的代码库纳管——定位代码、`scripts/sdd_project.py import` 注册、**反向补齐** PRD/接口契约/Plan，使其达到"SDD 可接管"。
- **适用场景**：老项目、外部仓库、他人代码。
- **硬约束**：代码必须先就位到 `Projects_Repo/<id>/` 才能 import；只增不改业务逻辑；反向文档必须标注"由已有代码整理"并经用户确认。
- **实测**：`novel` 项目即 `source=import`，验证了该路径可用。

#### ⑤ `sdd-project-maintenance` — 已有项目修整

- **核心用途**：读取现有状态与两级经验 → 产出聚焦 **Delta Plan** → 只改受影响文件 → 必要时转多智能体开发循环 → 收尾回写经验。
- **适用场景**：UI 改版、加功能、改接口、重构、改文档、继续中断项目。
- **五个子分支**：UI/原型、前端功能、API/后端、Bugfix、文档/Plan。
- **关键机制**：「小改 vs 大改」四维判定表（范围/风险/需求确定性/验收可控性）决定是否转 Planner→Developer→Tester。
- **实测问题**：
  - 用户说"重构"会被路由到此 Skill，但**五个子分支中没有重构分支**，`sdd-bugfix` 又明令"禁止大范围重构"、`developer.md` 要求"手术刀式修改"。结构性技术债无正式出口。
  - Bugfix 子分支与独立 `sdd-bugfix` Skill 职责重叠，且前者只写 5 步、后者有 10 步（含产品口径门禁、重复犯错分析、报告落盘），**执行深度取决于用户碰巧走了哪条路径**。

#### ⑥ `git-workflow` — Git 仓库与提交推送

- **核心用途**：开发前 Git 仓库健康检查、功能验收后的功能级提交（`type` 规范 + 任务 ID 关联）、推送到 `project-registry.json` 中登记的 `repo_url`。
- **适用场景**：Developer 编码前、用户门禁确认"推送并继续"后、项目初始化（由脚本执行）。
- **禁止项**：不提交 `.sdd/` 状态文件、不提交含密钥产物、不强制推送、不提交未验证功能。
- **边界**：**止于 `git push`**。无 tag、无 release、无构建产物核对、无环境变量核对、无回滚方案。

#### ⑦ `sdd-bugfix` — Bug 修复工程闭环

- **核心用途**：把修 Bug 变成可沉淀的闭环：记录原话 → 产品口径门禁 → 读上下文 → **经验回查** → **重复犯错分析** → 根因分析 → 最小修复 → 验证 → 报告落盘 `.sdd/bug_fix/` → 更新 `experience.md`。
- **适用场景**：`/sdd-bugfix <描述>` 或明确要求修某个 Bug。
- **最独特设计**：Step 5「为什么已有经验仍然犯错」——六问定位是"经验太抽象""没写成禁止规则""Planner 没分配 rules_files""Developer 没读""Tester 没转成验收标准"还是"旧经验的新变体"。这是全框架唯一对"经验失效"做归因的机制。
- **实测**：`novel` 项目 4 份 bug_fix 报告，命名规范（`YYYYMMDD-HHMM-简述.md`）被真实遵循。

#### ⑧ `sdd-project-delete` — 安全删除

- **核心用途**：破坏性操作的可确认化：定位目标 → 展示删除范围 → 检查 Git 未提交改动 → 要求**明确确认句**（"确认删除 X"，不接受"可以/继续"）→ 脚本原子删除并清空 active 指针。
- **适用场景**：仅限明确删除整个项目的意图。
- **强约束**：不可从模糊意图触发；不可批量；不可删 `Projects_Repo/` 等父级目录；不可手改 registry。

---

## 2. 非 Skill 但承担 Skill 职责的规范（必须纳入覆盖分析）

这四类文件不是 Skill，但实际决定了开发质量，缺失会被误认为"Skill 已覆盖"。

| 载体 | 承担的职责 | 覆盖缺口 |
|------|-----------|----------|
| `agents/planner.md`（334 行） | 任务拆分、验收标准分层、Mock 阶段禁区、能力边界表 | 无 |
| `agents/developer.md`（160 行） | 编码、pycore 合规、密钥红线、输出前必查清单 | 自审，无独立复核 |
| `agents/tester.md`（277 行） | 验收验证、阶段错配判定、BLOCKED 分类、报告双轨制 | **明确不做代码审查** |
| `dev-standards/frontend.md`（442 行） | 前端技术栈、目录、命名、代理、Mock、易错点 | 无性能/可访问性预算 |
| `dev-standards/backend-dev.md`（334 行） | 后端硬性禁止、pycore、端口、测试隔离 | 无数据库迁移规范 |
| `dev-standards/backend-layers.md`（268 行） | 四层分层、依赖方向 | 无 schema 演进 |
| `protocols/development-rules.md`（60 行） | 全局规则、端口权威源、经验沉淀链条 | 权威源被 5 处复制 |

---

## 3. 覆盖盲区（按证据强度排序）

### 盲区 A：代码审查 —— 完全缺失（证据最强）

**证据链**：

1. `tester.md` 核心原则第 2 条：`Test the contract, not preferences` —— "按 acceptanceCriteria、api-contracts.md、原型文件和 rules 验证；个人偏好或范围外问题只能记为**超出范围发现**"。
2. `tester.md` 约束节：`禁止自己写代码来"修复"问题（只报告问题）`，因此它不产出改进方案。
3. `developer.md` 的可靠性来源是「输出前必查清单」——**自审**。
4. 真实产物统计：`draw-telephone` 25 份、`creator-topic-library` 8 份、`novel` 7 份 = **40 份 test-reports，0 份 review**。
5. `creator-topic-library` 的 `work-log.md` 明确记录 Tester 的「超出范围发现」至今未处理：`QuickCreateModal 复位竞态、排序口径不一致、frontend/T-004-pw-fix.patch 临时文件、AntD Card bordered 弃用警告 + favicon 404`。**这些正是代码审查该抓的问题，但它们被定义为"不影响当前任务判定"，于是永久搁置。**
6. `draw-telephone/.sdd/experience.md`（60KB）首条即"登录态一致性修复：401 拦截器 + store 同步"——属于架构一致性缺陷。这类问题验收测试抓不到（每个页面单独看都正常），只有跨模块通读代码才能发现。

**结论**：Tester 的"验收"与工程意义上的"审查"是两个正交维度。当前框架只有一个维度。

---

### 盲区 B：经验治理 —— 只有写入，没有维护（证据次强）

**证据链**：

1. `development-rules.md`「经验沉淀链条」只定义了**写回链**（Developer/Tester/Bugfix 写入 + Orchestrator 回传）与**回读链**（Orchestrator 读系统级 → Planner 转约束 → Developer 读项目级）。
2. 无任何环节负责：去重、合并、失效标记、容量控制、晋升校验。
3. 实测体量：`draw-telephone` **60,944 字节**、`creator-topic-library` **12,997 字节**、`memory/harness-experience.md` 已 10 条大条目。
4. `developer.md`「开始工作前（每次必做）」第 1 条：`读取 .sdd/experience.md` —— 要求**每次全量读取**。
5. 60KB 经验 + 任务描述 + api-contracts + rules_files 同处一个上下文，实际会挤压 Developer 的可用推理空间，且旧经验不失效会导致过度约束（例如已被后续架构变更推翻的避坑规则仍在生效）。
6. `[SYSTEM] 建议回传系统级经验` 是一个纯文本标记，无格式校验、无回传确认、无重复检测。同一教训可能被多项目重复回传成多条。
7. `development-rules.md` 自己写了一条正确但无人执行的规则：**"若某条系统级经验反复在不同项目重犯，说明它没被转成强制规则——必须升级为 `harness-core/` 里的硬性规范"**。这条"晋升"动作没有承载者。

**结论**：经验系统是 V7.1 相对其他 SDD 实现的差异化资产，但它是唯一没有治理机制的核心资产。

---

### 盲区 C：发布交付 —— 只有一句话约定，无流程

**证据链**：

1. `development-rules.md`：「交付：全部功能自动验证通过后，输出 `docs/startup.md`（环境要求、启动命令、默认配置）」——仅此一句。
2. `router.md` 开发门禁 8 条中**没有发布门禁**。
3. `git-workflow` 止于 `git push`，无 tag、无 release note、无构建产物与环境变量核对。
4. `development-rules.md` 把"部署发布"列入"必须用户确认"清单，但**未定义确认之后由谁执行、按什么步骤执行**。
5. 实测：三个项目**全部**产出 `docs/startup.md`，说明这一步是真实刚需，却每次靠即兴执行，无质量下限保障。
6. `creator-topic-library` 实际还额外产出了 `docs/manual-checklist.md`（最终用户验收走查清单）——**这属于交付物，但不在任何 Skill 的产物映射表中**，属自发行为。

---

### 盲区 D：重构 —— 有入口，无分支，且被两处明令禁止

**证据链**：

1. `router.md` 分支 2 典型信号含"重构"。
2. `sdd-project-maintenance`「何时使用」含"重构实现"，但五个子分支（UI/原型、前端功能、API/后端、Bugfix、文档/Plan）**均非重构语义**。
3. `sdd-bugfix` 禁止节：`禁止为了修 Bug 大范围重构`。
4. `developer.md` 编码四原则第 3 条：`Edit with surgical precision`，"每一行改动都必须能对应到明确规范或验收标准"。
5. 结果：结构性技术债只能伪装成"加功能"或"修 bug"来进场，行为等价性无验证，风险不可控。

**结论**：这不是"没有需求"，而是"需求被现有规则压制到看不见"。`creator-topic-library` 的竞态问题、`draw-telephone` 的 401/store 一致性问题都是候选。

---

### 盲区 E：数据库 Schema 演进 —— 被列为风险，无规范承接

**证据链**：

1. `development-rules.md`：「数据库迁移」属"必须先向用户确认"的命令。
2. `backend-dev.md`、`backend-layers.md` 只讲 models/db/repository 分层与测试隔离，**全文无 Alembic / 版本化 / 回滚 / 数据回填**。
3. `planner.md` 要求"真实 SQLite 文件、目标表、seed 数据落盘"，即把 schema 当**一次性快照**处理。
4. `maintenance` 的"大改"定义明确包含"改数据库结构或关联表"，但该场景落地时无规范可依。

---

### 盲区 F：移动端专项 —— 被显式记录为负空间

**证据链**：

1. `router.md`：「原生 App、React Native、Flutter、uni-app、小程序不属于当前 SDD 前端规范的默认支持范围」。
2. `planner.md` 移动端 `rules_files=[]`（空规则）。
3. `alignment` 明确「不提供移动端产品设计规范」。
4. `memory/harness-experience.md` 2026-05-11 已记录该约束。
5. `project-registry.json` 实测：3 个项目全部 `project_type: web`，**mobile 需求未激活**。

**结论**：这是已识别的已知缺口，但需求侧未验证。补齐成本高（等于再造一套产品设计+前端规范），应排在最后。

---

### 盲区 G：性能与可访问性 —— 验收清单未覆盖

**证据链**：

1. `ui-design-standard`「验证清单」9 项：设计上下文、文案、重叠裁切、1440×900、390×844、交互状态、flow demo、原型边界 —— **无性能、无 a11y、无对比度实测**。
2. `frontend.md` 无 bundle 体积预算、无 lazy loading、无图片优化约定。
3. 系统经验里有"固定高度容器 20% 缓冲"这类**渲染实测**教训，说明这类问题真实存在，但没有系统化的渲染/性能验证环节。
4. `frontend.md` §12「布局与样式易错点」只有 2 条（多栏等高、侧栏列表），且注明"无统一代码示例"。

---

### 盲区 H：项目状态与产物一致性 —— 无巡检机制

**证据链**：

1. `router.md` 文件写入守门第 3 条：`如果发现这些目录出现在 Harness 根目录，必须先停止并提示` —— **依赖"恰好发现"**，无主动巡检。
2. `creator-topic-library` 的 `work-log.md` 记录过一次真实事故：`tasks.json 被写成带 BOM 的 UTF-8，已用 Orchestrator 去掉 BOM，避免脚本 json.load 报错`。
3. 已有 `scripts/check_harness_consistency.py`、`scripts/check_workbuddy_adapter.py` 检查 **Harness 本体**，但**无任何脚本检查项目侧状态**（`.sdd/` 结构与状态机一致性）。
4. 本次分析中 `ConvertFrom-Json` 在读 `creator-topic-library/.sdd/tasks.json` 时失败——经字节校验确认文件本身为合法 UTF-8 无 BOM（首字节 `123,10,32`），是 PowerShell 5.1 默认编码问题，**非文件损坏**。但这恰好说明：状态文件编码/格式的合规性没有任何工具在守。

**结论**：这是"低成本、高确定性"的缺口，一个脚本即可闭合，不需要新 Skill。

---

## 4. 重复与冲突（8 处，按维护风险排序）

### R1. 端口约定被复制到 5 处 ⚠️ 最高风险

| 位置 | 内容 |
|------|------|
| `protocols/development-rules.md`「端口约定（单一权威源）」 | 5199/8099、5175/8003 权威表 |
| `dev-standards/frontend.md` §5 | 重复声明，标注"本节为前端侧操作细节" |
| `dev-standards/backend-dev.md` 硬性禁止第 25 条 | 重复声明 |
| `agents/developer.md` Vite 代理检查项 | 重复声明 |
| `agents/tester.md` 第二步补充 C 第 3 条 | 重复声明 |

**风险**：端口调整时需改 5 处，任一遗漏即产生"Agent 验收藏、用户门禁假失败"——这正是 `harness-experience.md` 2026-05-21 记录过的事故类型。

### R2. 密钥红线被复制到 6 处

`developer.md`、`tester.md`、`sdd-bugfix`、`git-workflow`、`development-rules.md`、`backend-dev.md` 各有一版措辞。内容一致但**文件清单不完全一致**（`developer.md` 列了 4 组，`git-workflow` 只列 1 段）。

### R3. Mock 阶段验收禁区被写两遍（两套表）

- `planner.md`：11 类禁区表（错误示例→正确示例）+ 11 行能力边界对照表；
- `tester.md`：7 项禁止测试动作表 + 5 项允许动作表 + 阶段错配判定。

两者语义高度重叠但**条目数不同、分类维度不同**（前者按"能力"，后者按"动作"）。新增一条禁区时极易只改一处，导致 Planner 生成了 Tester 不允许测的标准。

### R4. 「小改 / 大改」判定被写两遍

`router.md`「开发循环启用判断」用三档（小改/中间改/大改 + 拿不准）；`maintenance` 用四维表。`router.md` 已加注"完整判断见 maintenance"，但**正文仍完整重写了一遍**，且 router 的三档描述与 maintenance 的四维表存在措辞差（router 说"小改可在项目修整分支直接执行"，maintenance 说"由本 Skill 直接读受影响文件并改"）。维护时容易改一处漏一处。

### R5. 经验回查/回写逻辑分散在 5 处

`developer.md`（读写）、`tester.md`（系统级经验回传）、`sdd-bugfix`（Step 4/5/10）、`maintenance`（经验回查 + 收尾回写）、`development-rules.md`（唯一权威定义）。虽已声明权威源，但每个 Agent 都重述了执行动作，**且措辞不同步**（例如 Bugfix 要求"必须分析为什么仍然犯错"，Developer 只要求"确认条目是否需要补充"）。

### R6. `alignment` 与 `phase-R` 的 R0 并存两套对齐产物

- `alignment` → `docs/澄清文档/<feature>/01-alignment.md`（业务 PRD 对齐稿格式）
- `phase-R` R0 → 对话内"需求对齐摘要"（另一套字段格式），且都做"最多 1-3 个带推荐答案的问题"。

`phase-R` 只说"若输入很长则转入 alignment"，**无明确分界条件**。实际可能出现：同一需求在 R0 已对齐一次，又被要求和 alignment 稿对齐第二次。

### R7. `frontend.md` §8 与 `phase-C` C3 的 Plan 模板重复

`frontend.md` 第 8 节给了一份 `docs/Plan.md` 前端部分模板；`phase-C.md` C3 给了完整 Plan.md 模板。前者未被声明为"片段引用"，而是独立完整模板，两部分章节编号（"一、前端开发" vs "一、功能清单总览"）**互相冲突**。

### R8. 适配层 Skill 覆盖不一致（非核心规则，但影响跨端一致性）

| 平台 | Skill 目录 | 缺失 |
|------|-----------|------|
| `harness-core/skills`（源） | 8 个 | — |
| `.cursor/skills` | 5 个 | `sdd-project-delete`、`sdd-project-import`、`sdd-project-maintenance` |
| `.workbuddy` | 仅 1 个入口薄适配 | 设计如此（走 Router 直读，符合契约） |

Cursor 端缺 3 个 Skill 的薄指针。按 `platform-adapters.md` 契约，Cursor 的 `skills/**` 应是"thin pointers"，缺指针不会导致功能不可用（可直读核心文件），但**破坏了"四端一致"的声明**，且会让 Cursor 端的 Skill 发现机制看不到这三个分支。

### R9. 路由歧义：修复 Bug 的入口有三处

| 入口 | 指向 | 执行深度 |
|------|------|---------|
| `router.md` 分支 2 信号（含"修 bug"） | `sdd-project-maintenance` | 5 步简版 Bugfix |
| `/sdd-bugfix` 命令 | `sdd-bugfix` Skill | 10 步完整闭环（含产品口径门禁、重复犯错分析、报告落盘） |
| `maintenance` 内部 Bugfix 子分支 | 同上 5 步 | 简版 |

**后果**：同一个 Bug，走 Router 自然语言进入的是简版（不落报告、不做重复犯错分析），走 `/sdd-bugfix` 进入的是完整版。**这是当前最影响经验沉淀质量的结构性问题。**

---

## 5. 新增 Skill 建议清单

### 建议 1 · `sdd-code-review`（代码审查）— **P0**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 A。Tester 按契约验收、明确不评判偏好与架构；Developer 自审；40 份 test-reports 中 0 份审查记录；「超出范围发现」被定义为不影响判定后永久搁置。 |
| **触发时机** | ① 任务 Tester PASS 后、`user_gate=true` 前；② 大改收尾（E2E 任务前）；③ 导入项目纳管完成后（基线体检）；④ Bugfix 根因属架构/规范类；⑤ 用户显式说"审查/复盘/技术债"。 |
| **输入** | 变更文件清单（Developer 输出）、`rules_files` 对应规范、`docs/api-contracts.md`、`.sdd/experience.md`、既有「超出范围发现」清单 |
| **输出** | `.sdd/reviews/review-<task-id>.md`，按 `Blocker / Major / Minor / Nit` 分级；每项含 `文件:行号 + 违反的规范条款 + 影响 + 建议`；末尾输出「可晋升为系统级经验的条目」 |
| **与现有 Skill 协作** | Orchestrator 在 Tester PASS 后调度，**审查通过才进用户门禁**；`Blocker` → 回 Developer（复用现有 retry 机制）；`Major×3 同类` → 触发 `sdd-refactor` 建议；跨项目问题 → 走既有系统级经验回传链。**只报不改**，与 Tester 契约一致。 |
| **关键设计约束** | 必须明确"审查 ≠ 验收"：不重跑 acceptanceCriteria、不替代 Tester；审查维度固定为 6 项——分层依赖方向、契约一致性、错误处理与边界、重复实现、命名与结构、死代码与残留（`[Mock]`/临时文件/TODO）。 |
| **优先级理由** | 唯一"阶段完全空白 + 证据链最完整 + 与现有角色无重叠"的缺口。补它不需要新增 Agent（可由 Tester 以"第二职责"承担，或以独立 reviewer 角色，与 Developer 模型不同源）。 |

---

### 建议 2 · `sdd-experience-governance`（经验治理）— **P0**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 B。写入链完备、维护链为零；`draw-telephone` 经验文件 60,944 字节且被要求每次全量读取；无去重/失效/晋升机制；`[SYSTEM]` 标记无校验。 |
| **触发时机** | ① 项目交付前（E2E 通过后）；② 经验文件超过阈值（建议 20KB）；③ 同一类问题第 3 次出现（`bug-logs` 可比对）；④ 用户说"整理经验/复盘"；⑤ 每 N 个任务（建议 N=5）。 |
| **输入** | `.sdd/experience.md`、`memory/harness-experience.md`、`.sdd/bug-logs/*`、`.sdd/bug_fix/*`、`.sdd/test-reports/*` |
| **输出** | ① 去重合并后的 `experience.md`（保留"现象→根因→规则"三段式，删除已失效条目并标注失效原因）；② `harness-experience.md` 的合并建议；③ **晋升清单**：哪些经验应升级为 `harness-core/` 硬规则（对应 `development-rules.md` 中那条无人执行的规则）；④ 上下文预算报告（当前经验字节数 vs 建议阈值）。 |
| **与现有 Skill 协作** | 只做"维护"，不替代任何"写入"职责——Developer/Tester/Bugfix 的写入链保持不变；产出直接落到 `maintenance` 的收尾环节；晋升清单由 Orchestrator 转为 `harness-core/` 的具体补丁（可视为"经验反哺 Harness 本体"的正式通道）。 |
| **关键设计约束** | **禁止无依据删除**：任何条目删除必须给出失效理由（如"该架构已在 T-00X 重构中被移除"），并保留 `git` 历史可追溯。 |
| **优先级理由** | 经验系统是 V7.1 的核心差异化能力，但其资产已实证失控（60KB）。继续增长会让"每次必读"从优势变成负担，且会让"经验回读环"名存实亡。 |

---

### 建议 3 · `sdd-release`（发布交付）— **P1**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 C。`startup.md` 只有一句话约定；无发布门禁；`git-workflow` 止于 push；"部署发布需用户确认"但确认后无流程。 |
| **触发时机** | 用户说"发布/上线/部署/打包/交付/给客户"；或全部 `tasks.json` 为 `passed` 且用户确认要交付。 |
| **输入** | `tasks.json`（全 passed 校验）、`docs/startup.md`、`.env.example`、`docs/Plan.md`「外部服务与测试权限清单」、`repo_url` |
| **输出** | ① 发布前检查单（质量门禁全绿 / 密钥未入库 / `.gitignore` 覆盖 / 构建产物可复现 / 外部服务状态与降级说明）；② `startup.md` 定稿（环境要求、启动命令、默认配置、端口、已知限制）；③ Git `tag` + release note（按 `tasks.json` 生成变更摘要）；④ 回滚方案（版本回退步骤 + 数据回滚边界）。 |
| **与现有 Skill 协作** | 串联 `git-workflow`（复用其提交规范与 `repo_url` 读取逻辑，扩展 tag/release 段）；消费 `sdd-product-design` 的「外部服务与测试权限清单」；交付后若用户验收发现问题 → `sdd-bugfix`。 |
| **优先级理由** | 三个在管项目**全部**自发产出 `startup.md`，说明是刚性需求；当前靠即兴执行，质量下限无保障。但因触发频次低于审查（仅项目末期），故列 P1。 |

---

### 建议 4 · `sdd-refactor`（重构专项）— **P1**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 D。有路由入口、无执行分支，且被 `bugfix`（禁止大范围重构）与 `developer`（手术刀式修改）双重压制，技术债无正式出口。 |
| **触发时机** | 用户说"重构/技术债/拆分模块/统一口径/清理"；`sdd-code-review` 累计 3+ 同类 `Major`；「超出范围发现」清单累计 ≥3 条同类。 |
| **输入** | 代码地图、`.sdd/experience.md`、`docs/api-contracts.md`（**重构不得改契约**）、现有测试与 Playwright 用例 |
| **输出** | ① 重构方案（目标/非目标/行为等价性契约）；② **回归基线先行**（重构前必须把现有行为固化为可执行用例）；③ 分批执行计划（每批可独立验证、可独立回滚）；④ 每批的等价性验证证据。 |
| **与现有 Skill 协作** | 由 `maintenance` 的 Delta Plan 升级而来（重构属"大改"）；每批执行走 Planner→Developer→Tester；收尾调 `sdd-code-review` 复核；经验回写走既有链条。 |
| **关键设计约束** | **行为等价性优先于代码美观**：无回归基线不得开工；每批不得超过"N 个文件 / 一个模块"；禁止与功能变更混在同一批。 |
| **优先级理由** | 需求已在真实项目出现（竞态、登录态一致性、临时文件残留），但目前被规则压制。P1 而非 P0，因为它是"清理型"能力，不阻塞新项目交付。 |

---

### 建议 5 · `scripts/check_project_state.py` + 薄 Skill 入口（项目状态巡检）— **P1**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 H。项目侧 `.sdd/` 状态无任何校验工具；曾发生 `tasks.json` BOM 污染事故；Router 的"发现误写入"依赖恰好发现；四端适配层已有 `check_harness_consistency.py`，项目侧空白。 |
| **触发时机** | 每次会话接手项目时；`maintenance` 状态检查步骤；交付前；出现"脚本 json.load 报错""任务状态与 Plan 不一致"等症状时。 |
| **输入** | `Projects_Repo/<id>/` 全目录 |
| **输出** | 结构化巡检报告：① 编码合规（UTF-8 无 BOM、可 `json.load`）；② 状态机一致性（`tasks.json` 的 status 与 `Plan.md` 勾选、`status.json` 的 stage 三者互校）；③ 产物完整性（PRD / api-contracts / Plan / prototypes 四件套）；④ 残留检测（`.sdd/tmp/` 未清理、`*.patch`、`[Mock]` 文本、`.env` 是否被误提交）；⑤ 误写入检测（Harness 根出现 `docs/`、`.sdd/` 等）。 |
| **与现有 Skill 协作** | **不新增 Skill 正文，只加一个脚本 + 在 `router.md`「Active Project Path 强制规则」处加一行调用说明**。`maintenance` 状态检查、`import` 纳管、`release` 交付前均可复用。 |
| **优先级理由** | 成本极低（单文件脚本）、收益确定（有历史事故记录）、且不增加流程负担（可自动跑）。列 P1 而非 P0 是因为它不改变能力边界，只提升可靠性。 |

---

### 建议 6 · `sdd-db-migration`（数据库演进）— **P2**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 E。"数据库迁移"被列为需确认项，但无规范；`planner` 把 schema 当一次性快照；`maintenance` 的"改数据库结构"大改场景无承接。 |
| **触发时机** | 任务涉及新增/修改表或字段、数据回填、索引调整；`maintenance` 判定为"改数据库结构"的大改。 |
| **输入** | 现有 schema、PRD「数据契约确认清单」、`api-contracts.md`、现有 seed 脚本 |
| **输出** | 迁移脚本（版本化、可回滚）+ 数据回填方案 + 兼容窗口说明（旧数据/旧接口在新 schema 下如何工作）+ 迁移前后验证命令。 |
| **与现有 Skill 协作** | 由 Planner 在生成 schema 变更任务时引用；`developer` 按迁移规范实现；`tester` 增加"迁移后 seed 数据与新表共存"验证项（现有 tester 只验"表存在 + seed 落盘"）。 |
| **优先级理由** | 三个在管项目均为 SQLite 单机形态，迁移需求尚未真实发生。**建议先以 `backend-layers.md` 增补一节的方式低成本试水，验证确有需要再独立成 Skill。** |

---

### 建议 7 · `sdd-quality-audit`（性能与可访问性专项）— **P3**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 G。`ui-design-standard` 验证清单无性能/a11y；`frontend.md` 无 bundle 预算与懒加载约定。 |
| **触发时机** | 前端 E2E 任务；用户说"优化性能/加载慢/适配";交付前抽查。 |
| **输入** | 构建产物、关键页面路由、Playwright 用例 |
| **输出** | 性能预算报告（bundle 体积、首屏时间、关键路径请求数）+ a11y 检查（对比度、焦点顺序、语义标签、键盘可达）+ 修复建议分级。 |
| **优先级理由** | 需求未验证（三个项目均未提出性能问题）。**建议先以 `ui-design-standard` 验证清单增补 3 条（bundle 体积上限、首屏请求数、键盘可达）的方式低成本覆盖，暂不独立成 Skill。** |

---

### 建议 8 · `sdd-mobile-standard`（移动端专项）— **P3**

| 项 | 内容 |
|----|------|
| **解决的问题** | 盲区 F。全流程移动端空白（产品设计、rules_files、前端规范）。 |
| **触发时机** | `project_type = mobile` 或用户明确要求原生/跨端应用。 |
| **优先级理由** | 注册表实测 0 个 mobile 项目，需求未激活；补齐成本接近再造一套产品设计与前端规范（预估 800+ 行）。**在出现第 1 个真实移动端需求前不应启动**——否则是为假想需求维护规范。 |

---

## 6. 不建议新增（应通过合并解决）

| 候选 | 判断 | 理由 |
|------|------|------|
| `sdd-doc-sync`（文档一致性） | **合并进 `sdd-code-review`** | "api-contracts 与 TS 类型/后端 model 是否一致"本质是契约一致性检查，属审查的 6 个维度之一。独立成 Skill 会导致审查被拆成两遍、用户要过两道门禁。 |
| `sdd-design-review`（设计审查） | **扩展 `ui-design-standard`** | 现有验证清单已是审查清单，只需增补条目（性能/a11y/对比度实测），无需新 Skill。 |
| `sdd-alignment`（独立化 alignment） | **修正 Router 路由即可** | alignment 能力已在，问题是 `router.md` 未路由到它。**这是修路由，不是造 Skill。**（见下方"存量修复"） |

---

## 7. 优先级排序与理由

| 序 | 建议 | 优先级 | 核心判据 |
|----|------|--------|----------|
| 1 | `sdd-code-review` | **P0** | 阶段完全空白 + 证据链最完整（0/40 审查报告）+ 与现有角色零重叠 + 有真实积压问题（4 项超出范围发现） |
| 2 | `sdd-experience-governance` | **P0** | 核心资产已实证失控（60KB）+ 写入链完备而维护链为零 + 直接决定"经验回读环"是否还成立 |
| 3 | `sdd-release` | **P1** | 三项目全部自发产出 startup.md（刚需已验证）+ 但仅项目末期触发 |
| 4 | `sdd-refactor` | **P1** | 需求真实存在但被规则压制 + 属清理型能力，不阻塞交付 |
| 5 | `check_project_state.py` | **P1** | 单文件脚本、有历史事故、不增流程负担 |
| 6 | `sdd-db-migration` | **P2** | 需求未真实发生，先以规范增补试水 |
| 7 | `sdd-quality-audit` | **P3** | 需求未提出，先以验证清单增补覆盖 |
| 8 | `sdd-mobile-standard` | **P3** | 0 个 mobile 项目，启动即为假想需求维护 |

**为什么不是 8 项都做**：Skill 数量增长本身是成本。每新增一个 Skill，就多一处需要与 `router.md`、四端适配层、`AGENTS.md` 核心规则位置清单同步的地方——而本报告第 4 节已列出 8 处现有同步失败。**先补两个真空缺，先修 9 处存量问题，再谈扩展。**

---

## 8. 存量修复（不需新增 Skill，但优先级等同 P0）

| # | 问题 | 修复动作 |
|---|------|----------|
| F1 | Bugfix 三处入口深度不一（R9） | 统一为：`router.md` 分支 2 的"修 bug"信号**改为指向 `sdd-bugfix`**；`maintenance` 的 Bugfix 子分支改为"仅限与本次修整同批的连带修复，且必须落 `bug_fix` 报告"。 |
| F2 | `alignment` 未被路由 | `router.md` 顶层意图中增补"业务口径对齐"为第 5 分支（或明确为分支 1/2 的**前置可选步**），并在 `AGENTS.md` 核心规则位置清单中对齐。 |
| F3 | 端口约定 5 处复制（R1） | 保留 `development-rules.md` 权威表，其余 4 处**只保留一行指针**（如"端口见 `development-rules.md`「端口约定」"），删除具体数值。 |
| F4 | Mock 禁区两套表（R3） | 以 `planner.md` 的能力边界表为唯一权威，`tester.md` 改为"按能力边界表的 Mock 列执行"，删除重复的 7 项表。 |
| F5 | 小改/大改两处判定（R4） | `router.md` 只保留判定结论与指向，删除三档正文。 |
| F6 | 密钥红线 6 处（R2） | 统一到 `development-rules.md` 一节 + 一份"禁止出现真实敏感值的文件清单"，各 Agent 只引用。 |
| F7 | Plan 模板两套（R7） | `frontend.md` §8 改为"前端部分片段，插入 `phase-C` C3 模板的第一节"，删除独立编号。 |
| F8 | Cursor 缺 3 个 Skill 指针（R8） | 补齐 `sdd-project-delete`、`sdd-project-import`、`sdd-project-maintenance` 的薄指针，或从 `platform-adapters.md` 显式声明"Cursor 端不镜像这三个分支，由 Router 直读"。**二选一，不要留模糊态。** |
| F9 | `manual-checklist.md` 无归属 | 将其纳入 `sdd-release`（建议 3）的产物，或在 `development-rules.md`「交付」一节显式声明为可选交付物。**已处理：随 `sdd-release` Step 3 交付（§11.1）。** |

---

## 9. 落地路线（建议顺序）

```
第 1 批（补真空 + 修歧义，互不阻塞）
├─ sdd-code-review            ← 新 Skill
├─ F1 Bugfix 入口统一          ← 改 router.md + maintenance SHELL
└─ F2 alignment 路由          ← 改 router.md

第 2 批（经验系统闭环）
├─ sdd-experience-governance   ← 新 Skill
└─ F3~F8 规则去重             ← 纯重构，无行为变化，可一次性提交

第 3 批（交付与治理）
├─ sdd-release                ← 新 Skill（含 manual-checklist 归属，F9）
├─ sdd-refactor               ← 新 Skill
└─ check_project_state.py     ← 脚本 + router 一行调用

第 4 批（按需触发，不主动做）
├─ sdd-db-migration  → 先以 backend-layers.md 增补试水
├─ sdd-quality-audit → 先以 ui-design-standard 验证清单增补
└─ sdd-mobile-standard → 等待第 1 个真实移动端项目
```

**验收标准（对新增 Skill 的统一要求）**：
1. 必须有明确的**触发条件**（可被 Router 或用户自然语言命中）；
2. 必须有**产物落盘路径**，并纳入对应 Skill 的产出物映射表；
3. 必须声明**与现有 Skill 的边界**（尤其与 Tester 与 Developer 的职责分界）；
4. 必须在 `AGENTS.md` 核心规则位置清单、`router.md`（若需路由）、`platform-adapters.md`（若需适配）三处同步登记；
5. 必须能被 `scripts/check_harness_consistency.py` 校验（路径可解析、无核心规则副本）。

---

## 10. 第 2 批执行记录（2026-10-28）

### 10.1 新增 `sdd-experience-governance`

`harness-core/skills/sdd-experience-governance/SKILL.md`。补的是经验链条的**第三环**：

| 环节 | 谁负责 | 动作 |
| ---- | ------ | ---- |
| 写回链 | Developer / Tester / Bugfix / 修整 / Code Review | 追加新教训 |
| 回读链 | Orchestrator / Planner / Developer | 读取并转约束 |
| **维护链（新增）** | 经验治理 Skill | 去重 / 合并 / 标失效 / 控容量 / 评估晋升 |

核心设计：

- **五步治理**：体检（先量化）→ 分类（KEEP / MERGE / STALE / VAGUE / DUP-SYSTEM / PROMOTE）→ 合并与失效标记 → 晋升评估 → 报告落盘 `.sdd/experience-audit/YYYYMMDD.md`。
- **硬阈值 32KB / 预警线 20KB**，直接对应 `draw-telephone` 60,944 字节的实测问题。
- **禁止无依据删除**：标失效必须给可核验理由（任务 ID / 架构变更），文件内保留标题 + 原规则摘要，不整段抹掉。
- **晋升优先级**：能机械检测的一律做成 `check_harness_consistency.py` 检查项，不做成经验文字——经验靠人记，脚本不会忘。这补上了 `development-rules.md` 里那条"反复重犯须升级为硬规则"的无人执行规则。
- **只维护不写入**：明确不新增条目，避免与写回链职责重叠。

### 10.2 F3~F8 去重结果

| # | 原问题 | 处理结果 |
| - | ------ | -------- |
| F3 | 端口约定 5 处复制 | 实测 6 处（含 `workbuddy-subagents.md` 的 2 处）。区分两类：**规则陈述**改为指针删数值；**示例命令/代码块**保留数值并注明"以权威表为准"。权威节补全 `VITE_BACKEND_PROXY_TARGET`、CORS 四来源、`/ws`、启动命令模板、端口占用处理，避免"指针指向的权威源反而比副本更简"的倒挂。 |
| F4 | Mock 禁区两套表 | 以 `planner.md`「阶段验收禁区 + 能力边界对照表」为唯一权威；`tester.md` 删除 7 项禁止表与 5 项允许表，改为按能力边界表「Mock 阶段」列执行，并保留 Tester 侧**验证手段**约束（多标签页、E2E 工具、刷新持久化、真实后端探测）——这些是手段限制而非禁区定义。另补一条原先缺失的判定：阶段错配责任在 Planner，不判任务 FAIL。 |
| F5 | 小改/大改两处判定 | `router.md` 删三档正文，只留三档结论表 + 指针；`maintenance` 四维表声明为唯一权威源。补一条 `router` 原有的空白：新建项目默认按大改处理。 |
| F6 | 密钥红线 6 处 | `development-rules.md` 新建权威节，含**全量禁止文件清单**（6 类，覆盖 `reviews` 与 `experience-audit` 两个新增产物目录）、禁止写法（含"前缀+省略"这类隐性泄露）、允许写法、泄露处理（已进 Git 历史须轮换）。5 个文件改为引用，独立清单条文清零。 |
| F7 | Plan 模板两套 | `frontend.md` §8 改为 phase-C C3 的**片段引用**，删除「# 开发计划」「一、前端开发」「二、后端开发」等与权威模板冲突的顶层编号，只保留「三、前端开发清单」一节内的页面清单片段 + 前端侧补充要求。 |
| F8 | Cursor 缺 3 个 Skill 指针 | 补齐 maintenance / import / delete，另补第 2 批新增的 experience-governance，共 4 个。顺带修掉 2 个既有缺陷：`git-workflow` 与 `ui-design-standard` 指针缺 YAML frontmatter（Cursor 靠 frontmatter 发现 skill，缺了等于不可见）。 |

### 10.3 新增防复发机制

`check_harness_consistency.py` 增加 `scan_cursor_skill_coverage()`，机械校验：

1. `harness-core/skills/<name>` 有目录 → `.cursor/skills/<name>/SKILL.md` 必须存在，否则报缺指针；
2. 反向：Cursor 有目录但核心无对应 Skill → 报 stale pointer；
3. 指针文件必须有 YAML frontmatter、`name` 与目录一致、含 `description`、指向 `harness-core/skills/<name>/SKILL.md`。

已用"临时重命名目录"方式实测该扫描能捕获三种故障（缺指针 / stale pointer / 缺必需路径），验证后恢复。

这条扫描的意义：F8 属于"文档声明四端一致、实际少三个指针"的漂移，靠人工检查必然复发，只有机械化才能终结。

### 10.4 校验结果

- `check_harness_consistency.py` → PASS（含新增 Cursor 覆盖扫描）
- `check_workbuddy_adapter.py` → 五项全 OK
- 15 个改动文件编码校验：无 U+FFFD、无 BOM

---

## 11. 第 3 批执行记录（2026-10-28）

### 11.1 新增 `sdd-release`（解决盲区 C，含 F9）

`harness-core/skills/sdd-release/SKILL.md`。核心原则 `Reproducible or it did not happen.`——交付的判断标准不是"我这儿能跑"，而是"换一个人、换一台机器、按文档照做能跑起来"。

为什么此前是真空：`development-rules.md` 关于交付只有一句「全部功能自动验证通过后，输出 `docs/startup.md`」。而三个真实项目的产物分布是：`startup.md` 3/3 有、`manual-checklist.md` 1/3 有（`creator-topic-library`，41 行完整走查清单，**产出但没有归属**）、release note 0/3、回滚方案 0/3。

交付五步：

| 步骤 | 内容 | 产物 |
| ---- | ---- | ---- |
| 1 | 发布前检查单（9 项门禁，任一不通过不得发布） | `.sdd/release/release-checklist-YYYYMMDD.md` |
| 2 | `startup.md` 六节定稿（环境/安装/启动/配置/端口/已知限制） | `docs/startup.md` |
| 3 | 最终用户验收走查清单（**F9 归属落地**） | `docs/manual-checklist.md` |
| 4 | Git tag + release note | `.sdd/release/release-note-v<version>.md` |
| 5 | 回滚方案（含数据回滚边界） | 写入 release note |

三条边界写死在文件里：**不擅自执行部署**（只出方案，执行前须用户确认）、**不复制 `git-workflow` 的提交规范**（只引用）、**不重跑 Tester 验收**。

第 9 项门禁「已知限制已记录」与第 4 项「密钥未入库」直接引用第 2 批建立的权威源，不再另立清单。

### 11.2 新增 `sdd-refactor`（解决盲区 D）

`harness-core/skills/sdd-refactor/SKILL.md`。补的是一个**结构性矛盾**，不是简单缺个 Skill：

1. `router.md` 分支 2 的典型信号含「重构」；
2. `maintenance` 的「何时使用」含「重构实现」，但五个子分支**没有一个是重构语义**；
3. `sdd-bugfix` 明令「禁止为了修 Bug 大范围重构」；
4. `developer.md` 原则要求 `Edit with surgical precision`。

结果是结构性技术债**只能伪装成"加功能"或"修 bug"进场**——行为等价性无验证、改动范围无边界。本 Skill 不放松前两条禁令，而是给出一个满足它们的入场方式。

定位判据只有一条，写在三行表格里：

| 对象 | 改完的行为 |
| ---- | ---------- |
| `sdd-bugfix` | 变了（变对了） |
| 功能开发 | 变多了 |
| **`sdd-refactor`** | **一模一样** |

三条硬红线：**不得与功能变更混批**、**不得改 `api-contracts.md`**（契约是保护壳不是对象）、**无回归基线不得开工**。

基线要求三条：可执行（是一条命令，不是"手动点一遍"）、可对比（前后跑同一条）、覆盖行为契约。覆盖不足时**先补测试再重构**（补测试算重构的一部分）。若完全无法建立基线，终止重构——"在没有护栏的路上换轮胎"。

冲突处理表逐条对上既有禁令：Bugfix 禁大范围重构 → 分两次做，先修行为再重构结构；`surgical precision` → 每批改动都对应 Step 1 目标条目与 Step 2 基线用例。优先级明确为 **行为正确性 > 行为等价性 > 结构美观**。

Step 4 特意加了一条反直觉提醒：**"测试全绿"不等于行为等价**，必须额外做契约逐项核对（对着 `api-contracts.md` 一条条确认测试未覆盖的边界）。

### 11.3 新增 `scripts/check_project_state.py`（解决盲区 H）

按报告 §5 的约束执行：**不新增 Skill 正文，只加脚本 + router 一行调用说明**。

它补的是「Harness 有 `check_harness_consistency.py`，项目侧什么都没有」的不对称。9 类检查：

| 检查 | 级别 | 真实案例 |
| ---- | ---- | -------- |
| 编码合规（BOM / CRLF / 非 UTF-8 / U+FFFD） | ERROR / WARN | `tasks.json` 带 BOM 导致 `json.load` 全链失败 |
| 任务状态机（非法 status / passed+blocked 并存 / retry 超限） | ERROR / WARN | — |
| acceptanceCriteria 污染（写入 typecheck/lint） | ERROR | — |
| Plan 与 tasks 进度一致性 | ERROR / INFO | 见 11.4 |
| 必备产物缺失 | WARN | — |
| `.sdd/tmp/` 与 `*.patch/*.bak/*.orig/*.rej` 残留 | WARN / ERROR | `novel/frontend/yarn.lock.bak`、`creator-topic-library/frontend/T-004-pw-fix.patch` |
| `.env*` 是否被 gitignore 覆盖 | ERROR / INFO | `novel/frontend/.env.production` 未被覆盖 |
| `[Mock]` 残留（仅交付态检查） | WARN | `draw-telephone` 2 个源文件 |
| 经验文件容量（32KB 硬 / 20KB 预警） | ERROR / WARN | `draw-telephone` 60,944 字节 |

退出码语义：存在 ERROR 才返回 1，WARN 不失败。`--json` 供 CI 与程序消费。

router 接入位置在「Active Project Path 强制规则」之后新增「项目状态巡检」小节，明确四个触发点：maintenance 修整判断前、import 纳管收尾、release 交付前检查、用户问「项目什么状态」。

### 11.4 两个误报的修正过程（值得记录）

**误报一：`pycore/` 被判为误写入目录。** 首版把 `pycore` 放进 `MISPLACED_DIRS`，跑 Harness 根目录立刻报 ERROR。读 `scripts/sdd_project.py::copy_harness` 才发现 `pycore` 是**框架源**——从 `ROOT / "pycore"` 复制进每个项目。所以它出现在 Harness 根目录是正确布局，出现在项目内也是正确布局。已在代码里写明为何故意排除，防止后人"顺手补上"。

**误报二：`.env` 忽略检测只看根目录。** 首版只读 `project/.gitignore`。`novel` 报 `.env.production` 未覆盖，但该项目根目录**根本没有** `.gitignore`——判定依据本身就不成立。重写为 `_gitignore_covers()`，按 git 自身语义实现：**就近 `.gitignore` 优先**，逐级向上直到项目根。逐条匹配 `*`、`*.suffix`、`prefix*suffix`，并保留一个易错点：裸 `.env` 行**不**覆盖 `.env.production`。

改完重跑 `novel` 仍报该 ERROR，但这次结论**有依据**：`frontend/.gitignore` 只列 `.env.local` 与 `.env.*.local`（与 Vite 模板一致），确实不含 `.env.production`。该文件 152 字节，仅含 `VUE_APP_BASE_API_URL` / `VUE_APP_BASE_IMG_URL` 字段名与 URL，无真实密钥，但风险判断成立。

**误报三：Plan 与 tasks 数量不一致。** `draw-telephone` 报「8 个勾选项 vs 25 个任务」「0 项完成 vs 25 passed」。实际是 Plan 用**功能级**勾选、tasks 用**任务级**条目，口径本就不同——25/25 全 passed 的健康项目被判成异常。

改为按方向分级：

- `total != task_total` → **INFO**（口径差异，非缺陷）；
- `done < passed` → **INFO**（Plan 未同步，收口补勾）；
- `done > passed` → **ERROR**（Plan **虚报**进度，验收前须核实）。

方向比总量更有信息量：Plan 说完成得比 tasks 证明的更多才是危险信号，反过来只是文档滞后。

### 11.5 三项目实测结论

| 项目 | 结果 | 真实问题 |
| ---- | ---- | -------- |
| `draw-telephone` | FAIL（1 ERROR / 4 WARN / 6 INFO） | 经验文件 60,944 字节超硬阈值；交付态仍有 2 个 `[Mock]` 源文件；无审查报告 |
| `novel` | FAIL（2 ERROR / 4 WARN / 2 INFO） | `yarn.lock.bak` 残留；`.env.production` 未被任何 `.gitignore` 覆盖；`.sdd/tmp/` 27 个未清文件；经验 23,456 字节超预警 |
| `creator-topic-library` | FAIL（1 ERROR / 1 WARN / 4 INFO） | `T-004-pw-fix.patch` 残留 |

三个项目**全部 FAIL**，且没有一条是误报——这说明项目侧确实长期缺机械检查。

### 11.6 配套改动

| 文件 | 改动 |
| ---- | ---- |
| `harness-core/router.md` | 新增「项目状态巡检」「重构环节」「发布交付环节」三节；路径表补 `.sdd/release/`、`.sdd/refactor/` |
| `harness-core/skills/sdd-project-maintenance/SKILL.md` | 转出指引新增 refactor / release 两条，附判据（用户是否接受"行为一模一样"）；进分支前先跑巡检 |
| `harness-core/skills/sdd-code-review/SKILL.md` | 协作表新增 refactor（双向，D4 是重构证据源）、release（Blocker 是发布门禁第 2 项） |
| `AGENTS.md` | 核心规则位置清单新增重构专项、发布交付、项目状态巡检三条 |
| `.cursor/skills/sdd-release/`、`.cursor/skills/sdd-refactor/` | 新建薄指针（否则 §10.3 的 `scan_cursor_skill_coverage()` 会 FAIL） |
| `scripts/check_harness_consistency.py` | `REQUIRED_PATHS` 加 3 条：两个 Skill + 巡检脚本 |
| `scripts/sdd_project.py` | `ensure_project_dirs` 加 `.sdd/release`、`.sdd/refactor` |
| `.workbuddy/skills/sdd-harness/SKILL.md` | 关键词补「重构/技术债/解耦」「发布/上线/部署/交付/回滚」「项目状态检查」，并重新 `install_workbuddy_skill.py` 同步 |

### 11.7 校验结果

- `check_harness_consistency.py` → PASS
- `check_workbuddy_adapter.py` → 五项全 OK（入口 Skill 同步后由 FAIL 转 OK）
- `check_project_state.py --all` → 三项目均检出真实问题，误报已降级为 INFO
- `--json` 输出结构正常，`EXIT=1` 与 ERROR 存在性一致
