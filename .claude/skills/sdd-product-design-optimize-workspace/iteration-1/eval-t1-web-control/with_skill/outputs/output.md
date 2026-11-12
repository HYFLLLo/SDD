# SDD 产品设计流程（文字模拟）—— project-ops-desk 运维工单管理后台

> **本文件说明**：本任务为**纯文字模拟**，未真实创建任何目录或文件。以下内容完整走一遍 SDD 产品设计流程（入口检查 → 阶段 R → A → B1 → B2 → C），给出各阶段应产出的产物清单、写入路径、临时产物清理时机、阶段判定方法与决策理由，并在末尾直接回答 6 个指定问题。
>
> **模拟假设**（由任务方给定）：
> - `project_id` = `project-ops-desk`
> - `project_name` = 内部运维工单管理后台
> - `project_type` = `web`（桌面 Web 后台）
> - `repo_url` = 未提供（空）
> - `active_project_id` = `project-ops-desk`
> - `active_project_path` = `Projects_Repo/project-ops-desk/`
> - Harness 根目录记为 `H` = `E:\SDD_V7_1_2\SDD_V7_1_2\`；项目绝对目录 `P` = `E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\`

---

## 0. 入口前置检查（进入阶段判断之前的步骤）

依据 `SKILL.md`「入口前置检查」，新建项目需依次完成：

1. **确认项目字段**：用户请求已基本覆盖所需信息，缺 `project_id`/`repo_url`，由 Agent 补齐为 `project-ops-desk`、repo_url 留空。（模拟假设已给定这三项。）
2. **检查 project-registry.json**：`H:\project-registry.json`。结论：`projects[]` 中无 `project-ops-desk`，且 `active_project_id` 为空或指向其他项目 → 允许创建新项目。
3. **检查 Projects_Repo**：`P` 目录不存在 → 按「允许视为空项目」处理，可继续新建流程。
4. **创建/绑定项目**（模拟执行）：
   ```text
   python scripts/sdd_project.py new project-ops-desk --name "内部运维工单管理后台" --type web
   ```
   脚本负责：创建 `P\`、初始化 `.sdd/project.json`、初始化 `docs/`、初始化 Git 仓库、写 `H:\project-registry.json`（新增项目记录 + 设 `active_project_id=project-ops-desk`）。
5. **进入阶段判断的必要条件**全部满足：注册表存在、active 指向本项目、`.sdd/project.json` 存在、`docs/` 存在、无业务产物。

**初始化脚手架产物**（脚本生成，设计流程不新增）：

| 路径 | 定位 |
|------|------|
| `P\.sdd\project.json` | 项目状态（脚本创建，全程常驻） |
| `P\docs\` | 空目录（脚本创建） |
| `P\pycore\` | 后端脚手架模板（脚本生成） |
| `P\README.md`、`P\.gitignore`、`P\pyproject.toml` | 脚手架 |
| `H:\project-registry.json` | 注册表（含新项目记录 + active 指向） |

> ❗️❗️❗️ **用户确认点 0**：执行初始化前向用户展示「已绑定新建项目：project_id / project_name / active_project_path / repo_url=未设置」，确认后进入阶段判断。

---

## 1. 阶段判定协议（如何根据已有产物判断当前阶段）——对应问题 4

判定依据 `<active_project_path>/docs/` 与 `.sdd/` 的产物存在性，权威表来自 `SKILL.md`「阶段判断」+「产出物映射表」：

| 现状（按序检测） | 判定 | 动作 |
|---|---|---|
| `docs/` 不存在/为空，或 `docs/PRD.md` 不存在 | 阶段 R | 读 `phase-R.md` |
| `docs/PRD.md` 存在，但**缺少完整数据契约章节**（= 数据契约确认清单 + 接口响应格式契约） | 阶段 A | 读 `phase-A.md` |
| `docs/PRD.md` 数据契约章节完整，且**无 `.sdd/tmp/ui-design-spec.md`**（若有 `.sdd/tmp/visual-research.md`，作为 B1 设计方向输入） | 阶段 B1 | 读 `phase-B1.md` |
| `.sdd/tmp/ui-design-spec.md` 存在 | 阶段 B2 | 读 `phase-B2.md` |
| 原型已完成，但 `docs/api-contracts.md` 或 `docs/Plan.md` 缺失 | 阶段 C | 读 `phase-C.md` |
| PRD + api-contracts + Plan + prototypes/ 四件套齐全，且 visual-research / ui-design-spec 已按映射表清理 | 产品设计完成 | 告知可进入开发 |

**本模拟的判定链**：

```text
初始化后：docs/ 空                     → 阶段 R
R 结束：docs/PRD.md 初稿（无契约章节）  → 阶段 A
A 结束：PRD 含完整数据契约、无 ui-design-spec → 阶段 B1
B1 结束：.sdd/tmp/ui-design-spec.md 存在  → 阶段 B2
B2 结束：docs/prototypes/ 已产出、缺 api-contracts/Plan → 阶段 C
C 结束：四件套齐全 + 临时产物已清理     → 产品设计完成
```

**断点恢复说明**：若流程中途被打断，下次进入时直接按上表检测产物即可定位阶段——例如 PRD 已含数据契约但无 ui-design-spec，则回到 B1；ui-design-spec 存在但无 prototypes 则回到 B2；原型在但缺两件套则回到 C。此判定不需要任何额外状态文件。

---

## 2. 阶段 R：需求澄清 + 竞品调研 + 视觉证据

**判定**：`docs/` 为空 → 阶段 R。

### R0 需求澄清与用户对齐

用户已给出较完整的四问信息，Agent 采用「总结已知 + 追问缺口」方式（不重复提问）。

**需求对齐摘要**（对话中呈现，用户确认后为 R0 唯一门禁）：

- 项目目标：企业内部运维工单的录入、分派、跟踪与状态统计，统一在一个干净专业的后台完成。
- 目标用户：运维人员 + 客服人员。
- 使用场景：每日高频录入/分派/跟踪工单；运维负责人定期查看状态统计报表。
- 核心问题：工单分散无统一台账、状态不可跟踪、报表靠人工统计。
- 核心功能：登录、工单列表、工单详情与流转、创建工单表单、统计仪表盘。

**功能 Pipeline 拆解**（一次整体呈现，关键节点带推荐默认，仅歧义处追问；全部附着于需求对齐摘要一次性确认，不逐条设门禁）：

| 核心功能 | Pipeline 节点链 | 关键节点口径（带默认） |
|---|---|---|
| 登录 | 打开登录页 → 输入账号密码 → 服务端校验 → 签发 token → 进入工单列表 | 认证方式=账号密码（默认）；SSO/第三方登录 → V2 |
| 创建工单 | 填表 → 校验 → 提交 → 创建成功 → 跳转工单详情 | 分类体系=6 类（网络/服务器/数据库/应用系统/账号权限/办公终端，默认可改）；优先级=紧急/高/中/低（默认）；MVP 不支持附件（V2 引入，涉及存储选型，默认）；是否指定处理人=可空（默认空，进入待分派） |
| 工单列表 | 读取列表 → 筛选/搜索/排序 → 分页查看 | 筛选维度=状态/分类/优先级/分派对象/时间范围；关键词搜索匹配标题与描述；分页 20/页（默认） |
| 工单详情与流转 | 看详情 → 流转操作 → 追加备注 → 更新状态 | 状态机=新建→待分派→处理中→已解决→已关闭，含拒绝/退回与重新打开分支；分派=手动指定（默认；自动分派按技能匹配 → V2）；每步留痕（events 时间线） |
| 统计仪表盘 | 选时间范围 → 指标卡/趋势/分布/排行 → （V2 下钻） | 指标=总工单/待处理/处理中/今日新增/今日解决/SLA 达标率/平均处理时长；趋势=近7/30天新增与解决；分布=按状态/分类/优先级；排行=分派对象负载 Top | 

**AI 功能识别结论**：以上均为普通 CRUD / 业务流程 / 数据查询，**无 AI 参与** → 不写 AI 章节、不产出 AI 默认配置、不追问 AI 材料。（V2 智能分类/智能分派预留为 AI 评估项，本期不写。）

- 用户输入清晰、口径稳定 → **不创建澄清文档**（`docs/澄清文档/**` 不出现），R0 结论直接合入后续 PRD 背景章节。

### R1 竞品调研执行

调研 3 家同类产品（≥2 家、≥1 家国内），同时覆盖「产品结论」与「视觉证据」：

| 竞品 | 目标用户/场景 | 可借鉴点 | 不采用点 | 视觉证据 |
|---|---|---|---|---|
| ServiceNow ITSM（海外） | 企业 IT 服务管理 | 工单/事件分级、SLA、服务目录、高密度工单列表 | 流程过重、学习成本高 | Playwright 截图 → `.sdd/tmp/screenshots/servicenow.png` |
| Zendesk（海外） | 客服支撑 | 筛选面板化、指标卡片、标签、报表清晰 | 邮件会话范式不适配内部工单 | 截图 → `.sdd/tmp/screenshots/zendesk.png` |
| 腾讯蓝鲸智云 ITSM（国内） | 国内 IT 流程平台 | 侧边菜单 + 工单流转步骤条、中高信息密度 | 规约冗长、暗色默认 | 截图 → `.sdd/tmp/screenshots/bluewhale.png` |

（无法截图时必须说明原因并请求用户提供截图；本模拟假设可截图。）

### R2 调研产出与视觉证据落盘

对话中呈现参考方向 A/B/C + 融合方案，用户在 R 门禁选择：**融合方案**（ServiceNow 的列表密度 + Zendesk 的指标卡片与筛选 + 蓝鲸 ITSM 的状态流转呈现；蓝灰主色，专业干净）。

存在可复用视觉证据 → 写入临时产物：

```text
P\.sdd\tmp\visual-research.md
```

内容含：竞品视觉证据表 / 用户选定方向 / 可复用视觉规则（页面结构=左导航+顶部工具条；组件形态=Table+Tag+统计卡片+步骤条+时间线；色彩=蓝灰主色+中性灰背景；信息密度=中高密度）/ 原型必须参考 / 禁止照搬（不复制竞品品牌、Logo、真实文案、商业数据，只借鉴结构交互视觉规律）。

**阶段 R 产物路径汇总**：`P\.sdd\tmp\visual-research.md`（临时，保留到阶段 C 完成后删除）+ `P\.sdd\tmp\screenshots\*.png`（辅助临时文件，随 visual-research 一并清理）；竞品产品结论随后合入 PRD 背景章节。

> ❗️❗️❗️ **R 门禁（用户确认点 1）**：请确认阶段 R 结果——竞品参考方向采用**融合方案**？是否存在 AI 功能需确认默认配置？（本项目无 AI，第 2 项应用）。确认后进入阶段 A。**未确认不得进入 A。**

---

## 3. 阶段 A：页面 → 功能 → 版本规划 → PRD 初稿

**判定**：PRD 初稿存在但无数据契约章节 → 阶段 A。

### A1 页面梳理

**页面清单**：

| 序号 | 页面名称 | 页面类型 | 可见角色 | 入口来源 | 跳转去向 |
|------|---------|---------|---------|---------|---------|
| P01 | 登录页 | 表单页 | 未登录用户 | 直接访问 | 工单列表 |
| P02 | 工单列表 | 列表页 | 运维/客服 | 登录后默认页 / 侧边栏 | 工单详情、创建工单 |
| P03 | 工单详情 | 详情页 | 运维/客服 | 列表行点击 | 流转操作、返回列表 |
| P04 | 创建工单表单 | 表单页 | 运维/客服 | 列表页「新建工单」按钮 | 工单详情（提交成功） |
| P05 | 统计仪表盘 | 仪表盘 | 运维/客服（默认全员可见） | 侧边栏 | V2：下钻列表（携带筛选参数） |

**页面跳转图**：

```text
登录页 → 工单列表 → 工单详情
  ↓          ↓
仪表盘     创建工单 → 工单详情（提交成功）
```

**全局布局**：统一左侧导航（列表/仪表盘）+ 顶部工具条（登录用户、通知占位）。

> ❗️❗️❗️ **A1 门禁（确认点 2）**：确认「页面清单和跳转逻辑」后进入 A2。

### A2 主要功能定义与分析

按页面逐页定义功能清单 + 边界 + 关联（节选示例，完整内容写入 PRD）：

- **P01 登录页**：F-01-01 账号密码登录（完成标准：正确凭据登录进入列表，错误有提示）。不包含第三方登录/SSO（V2）。
- **P02 工单列表**：F-02-01 列表展示；F-02-02 筛选与搜索（状态/分类/优先级/分派对象/时间 + 关键词）；F-02-03 分页排序。V2：批量分派/批量关闭、导出。
- **P03 工单详情**：F-03-01 全量信息展示（含时间线）；F-03-02 工单流转操作（分派/转派、接单、处理中、已解决、关闭、重新打开）；F-03-03 备注与操作记录。V2：SLA 超时预警、工单合并/关联。
- **P04 创建工单表单**：F-04-01 创建工单（标题、描述、分类、优先级、可选指定处理人；MVP 无附件），提交成功跳详情。
- **P05 统计仪表盘**：F-05-01 核心指标卡；F-05-02 新增/解决趋势折线；F-05-03 状态分布环形图；F-05-04 分类/分派对象排行；F-05-05 时间范围切换（7/30 天）。V2：下钻明细、自定义报表、报表导出。

> ❗️❗️❗️ **A2 门禁（确认点 3）**：确认所有页面功能清单与边界后进入 A3。

### A3 版本规划（Roadmap）

- **Mission**：让运维与客服在一个统一、干净、专业的后台完成工单录入、分派、跟踪与统计，缩短响应时间、全貌清晰。
- **Persona**：运维工程师（处理人，处理/更新工单）；客服/一线支持（受理录入）；运维负责人（看统计、监督 SLA 与负载）；管理员（V2 配置类）。
- **V1/MVP**：P01~P05 全部页面入 MVP。
- **V2+**：SSO/第三方登录（依赖 IDP 申请）；工单批量操作、导出；SLA 规则配置与超时预警（依赖规则/定时任务）；附件与对象存储（存储选型）；仪表盘下钻/自定义报表/导出；消息通知（短信/邮件/IM webhook，依赖外部服务）；AI 智能分类/智能分派（无材料，合规待评估）。
- **理由**：MVP 功能均为单表 CRUD + 简单聚合，成本低、依赖内建；被排除项均依赖外部账号/服务/规则引擎，MVP 不必要。

> ❗️❗️❗️ **A3 门禁（确认点 4）**：确认版本规划与取舍后进入 A4。

### A4 关键功能实现思路（穿插式对齐，无独立门禁）

复杂链路/关键技术选型才做 A4；普通 CRUD 不写。本项目两条：

1. **工单状态机流转**（复杂业务链路）：采用**状态枚举 + 服务端合法性校验表**（新建→待分派→处理中→已解决→已关闭；分支：待分派可转派、已解决/已关闭可重新打开）。不使用工作流引擎（依赖轻），V2 多级审批时再评估。
2. **仪表盘聚合选型**（关键技术选型）：MVP 数据量为单一业务表，**直接对 tickets 表实时 COUNT/GROUP BY 聚合**，不引入 OLAP/数仓、不引入物化表；V2 数据量大时评估预聚合表或 ClickHouse。图表库前端约定 ECharts。

结论并入 PRD「复杂功能业务链路 + 关键实现思路」。

### A5 数据契约确认（A5-1/A5-2 不设用户门禁；A5-3 需用户确认）

**A5-1 业务数据契约（checklist，完整设计、不随 V1/V2 变化 — 只开发部分功能也要完整设计）**：

- 工单实体 `ticket`：id、ticket_no、title、description、category（枚举：网络连通/服务器/数据库/应用系统/账号权限/办公终端/其他）、priority（枚举：紧急/高/中/低）、status（枚举：新建/待分派/处理中/已解决/已关闭）、assignee_id、creator_id、created_at、updated_at、resolved_at、closed_at。
- 状态流转表（见 A4，含非法流转拒绝）。
- 用户/角色 `user`：id、name、username、role（枚举：运维/客服/管理员）、is_active。
- 流转记录 `ticket_event`：id、ticket_id、actor_id、action_type（枚举：create/assign/accept/resolve/close/reopen/comment）、content、created_at。
- 权限角色：MVP 期运维与客服权限基本一致；管理员配置能力 V2。
- 仪表盘口径：见 `docs/data-system.json`（指标/维度/聚合规则）。

**A5-2 接口响应格式契约（必须在此锁定）**：

- 成功：`{"code": 200, "message": "success", "data": {...}}`；错误：`{"code": <错误码>, "message": "<描述>", "data": null}`；分页：`{"code": 200, "data": {"items":[...], "total": n, "page": 1, "page_size": 20}}`。
- HTTP 状态码：200 成功 / 400 参数错误 / 401 未认证 / 403 无权限 / 404 不存在 / 500 服务器错误。

**A5-3 外部依赖与配置草稿（需用户确认，涉及账号/密钥/付费/合规）**：

| 依赖 | 用途 | 关键配置字段 | Key/账号来源 | 存放位置 | 缺失时策略 | 状态 |
|---|---|---|---|---|---|---|
| LLM / Embedding / Rerank | 无（MVP 无 AI；V2 智能分派时再评估） | — | — | — | Mock | 不适用（V2 预留） |
| 第三方 API / 数据源 | 无 | — | — | — | — | 不适用 |
| 支付 / 结算 | 无 | — | — | — | — | 不适用 |
| 短信 / 邮件 / 推送 | MVP 无（V2 消息通知引入） | `SMTP_*` / webhook URL | 用户（V2 再提供） | `backend/.env` | Mock | 不适用（V2 预留） |
| 对象存储 / 文件服务 | MVP 无附件（V2 引入 OSS/本地盘） | `OSS_*` | 用户（V2 再提供） | `backend/.env` | Mock | 不适用（V2 预留） |
| 第三方登录 / SSO | MVP 无（本地账号密码） | — | — | — | — | 不适用（V2 预留） |
| 地图 / 定位 / 实名 / 风控 | 无 | — | — | — | — | 不适用 |
| 认证 | 本地账号密码（backend 内建，无外部） | — | — | — | — | 不适用 |

> 自检通过：功能链路里用到的任何外部依赖（尤其 AI/OSS/通知/SSO）都已有明确行；**MVP 级零外部依赖**，草稿结论为「全部 V2 预留」，用户确认成本极低。
> ❗️❗️❗️ **A5-3 确认点 5**：外部依赖草稿逐项与用户过一遍（本单确认 MVP 无外部依赖）。

### PRD 初稿落盘

写入 `P\docs\PRD.md`，结构：背景与调研结论 / 页面清单与跳转 / 按页面功能定义与边界 / Mission/Persona/版本规划 / 复杂链路与关键实现思路 / 数据契约确认清单（A5-1+5-2）/ 外部依赖与配置草稿（A5-3）。

> ❗️❗️❗️ **阶段 A 总确认（确认点 6）**：确认页面清单、功能边界、版本规划、外部依赖草稿、PRD.md 一致无遗漏。询问「是否进入原型设计阶段？」→ 用户确认 → 进入阶段 B1。

**阶段 A 产出路径汇总**：`P\docs\PRD.md`（初稿态，阶段 C 定稿）。

---

## 4. 阶段 B1：Design Spec

**判定**：PRD 含完整数据契约章节、无 `.sdd/tmp/ui-design-spec.md` → 阶段 B1。

1. 从 PRD 列出 MVP 界面清单：P01~P05（共 5 个）。
2. **读取视觉调研上下文**：`.sdd/tmp/visual-research.md` 存在 → 提取用户选定融合方向、竞品截图/URL、可借鉴页面结构与组件形态、配色字体间距信息密度、不采用点。
3. **收集 Design Context**：检查 design system/UI kit、品牌规范/Logo/色彩/字体、已有产品截图、已有 codebase → **均无** → 标注 `visual_research_status: ready`，默认设计基底 = **Ant Design（桌面 Web）**。无 codebase 可读，不凭记忆重画（无现成代码，天然满足）。
4. **设计方向**：R 阶段已确认融合方向 → **沿用，不另起炉灶**（不触发「设计方向顾问 fallback」）。
5. **撰写 Design Spec** 到 `P\.sdd\tmp\ui-design-spec.md`：

   - `visual_research_status: ready`；方向来源=阶段 R 选定方向
   - 界面清单（P01 登录页 1440×900 / P02 工单列表 / P03 工单详情 / P04 创建工单 / P05 统计仪表盘）
   - 设计方向：蓝灰企业运维后台，信息密度中高
   - 核心资产：Logo=无；已有产品图=无；codebase tokens=无
   - 视觉规格：Primary=蓝（AntD 蓝灰系 `#1677ff` 派生）；Background=`#F5F5F5`；Text=`#1F1F1F`；Border=`#D9D9D9`；Accent=状态 Tag 色（绿=已解决 / 橙=处理中 / 红=紧急）；字型=系统 sans-serif；间距/圆角/阴影=AntD 默认（8px 圆角）；信息密度=中高
   - 组件与页面结构：Layout（Sider+Header+Content）、Table、Tag（状态/优先级）、Statistic 卡、Timeline（流转记录）、步骤条（创建/流转）、ECharts 图表
   - 签名细节（120% 质感锚点）：状态 Tag 色板 + 仪表盘指标卡
   - 设计禁区（反 AI slop）：不使用无依据紫渐变、emoji 当图标、圆角卡片+左 border accent、SVG 手画人物、系统字体当 display；不照搬竞品品牌/Logo/文案/数据
   - 气质关键词：专业 / 干净 / 可信 / 高效 / 克制

> ❗️❗️❗️ **B1 门禁（确认点 7）**：「Design Spec 已完成，请审阅。确认后进入阶段 B2 原型设计。」**未确认不得进入 B2。**

**阶段 B1 产出路径汇总**：`P\.sdd\tmp\ui-design-spec.md`（临时；B2 原型完成后立即删除）。

---

## 5. 阶段 B2：原型设计

**判定**：`.sdd/tmp/ui-design-spec.md` 存在 → 阶段 B2。

1. **加载底座**：先读 `harness-core/skills/ui-design-standard/SKILL.md`（原型阶段底线：可读性、中文显示、组件状态、视口验证、竞品参考边界、原型与生产代码边界）。
2. **原型架构选择**：桌面 Web 后台 → **桌面 Web 原型（Browser frame / 1440×900）**。不适用 Overview 平铺（页数少、有明确流程）。
3. **工具选择**：用户未指定 → **默认 HTML 原型（模式 A）**，不用 Pencil/Stitch。
4. **Junior Pass 判断**：必做场景逐项检查——Design Spec 缺截图/URL/context？（否，ready）；用户要求高质量/多方案？（否）；原型超过 5 个界面？（否，恰好 5 个）；单机流程复杂？（否，路径简单）；Agent 对信息层级不确定？（否）。→ **可跳过 Junior Pass**，标注：`已走快速路径：Design Spec 明确，直接生成高保真原型。`
5. **Full Pass（模式 A）执行**：按 spec 用 HTML/CSS/JS 绘制可点击 flow demo（最小状态机：登录→列表→详情；列表→新建→详情→列表；列表→仪表盘），全中文真实示例数据，验证 ≥3 个关键点击与 1440×900 视口。

**输出路径**（`P\docs\prototypes\`）：

```text
docs/prototypes/
├── README.md                 ← 生产前端交接说明（页面清单/关键组件/交互状态/Mock 数据结构/需真实 API 的位置/须生产实现 vs 仅原型效果）
├── index.html                ← 流程入口/导航
├── 01-login.html
├── 02-ticket-list.html
├── 03-ticket-detail.html
├── 04-create-ticket.html
├── 05-dashboard.html
└── assets/                   ← 共用的 css/js/示例数据
```

6. **原型验证清单**：浏览器可打开、控制台无 JS 错误、无重叠裁切溢出、组件清单与 spec 一致、视口 1440×900、中文无英文占位、关键按钮可点击路径可走通。

> ❗️❗️❗️ **B2 门禁（确认点 8）**：「阶段 B2 原型已完成，请确认是否进入阶段 C。」

**B2 收尾（临时产物清理 #1）**：
- **立即删除** `.sdd/tmp/ui-design-spec.md`（B2 原型完成后随即清理，权威口径：SKILL.md 产出物映射表）。
- **保留** `.sdd/tmp/visual-research.md`（供阶段 C 写 api-contracts / Plan 参考原型上下文，权威口径：映射表「保留到阶段 C 完成后删除」）。
- 本项目为 HTML 模式 → **不产出** `docs/prototypes/pencil-prompt.md`（仅 Pencil 模式产物）。

**阶段 B2 产出路径汇总**：`P\docs\prototypes\*`（常驻）+ 删除 `P\.sdd\tmp\ui-design-spec.md`。

---

## 6. 阶段 C：PRD 定稿 + 接口契约 + 开发计划

**判定**：原型已完成，但 `docs/api-contracts.md` 或 `docs/Plan.md` 缺失 → 阶段 C。

### C1 定稿 PRD.md

在阶段 A 初稿上补充章节（**不生成 roadmap-final.md / architecture-blueprint.md 等独立文件**，全部合入）：

- 路线图（版本规划终版：V1·MVP 五页面 / V2 清单）
- 技术架构蓝图：前端 React SPA（Vite）+ 后端 Python3.11+/FastAPI/PyCore；分层=API 层/服务层/数据层；部署=单机进程（V2 容器化）
- 原型说明：`docs/prototypes/` 各文件与 P01~P05 对应关系
- 核心流程图（Mermaid sequenceDiagram / flowchart）：创建→分派→接单→处理→解决→关闭，及异常分支（退回待分派、重新打开）
- 组件交互说明：影响模块（新增 ticket/ticket_event/dashboard 模块）、调用关系
- 技术选型与风险：前端栈（React/TS/Vite/react-router/Zustand/Axios/AntD/ECharts/ESLint+Prettier）；风险=仪表盘高频实时聚合性能（V2 预聚合/物化）、状态机一致性（服务端校验）、MVP 零外部依赖（无 Key 风险）

### C2 输出接口契约 docs/api-contracts.md

> 前端 Mock 与后端实现的唯一对齐依据。所有响应遵循 A5-2 锁定格式，字段类型/嵌套完整，禁止 `...`/TBD。

接口清单（每个均含请求方法/路径/请求体/成功响应/至少一种错误响应；下文给 2 个完整示例 + 其余列表）：

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/auth/login` | POST | 账号密码登录 |
| `/api/meta/dictionaries` | GET | 分类/优先级/状态/流转动作字典 |
| `/api/users?is_assignable=true` | GET | 分派对象下拉 |
| `/api/tickets` | GET | 列表（筛选/搜索/分页/排序） |
| `/api/tickets` | POST | 创建工单 |
| `/api/tickets/{id}` | GET | 详情（含 events 时间线） |
| `/api/tickets/{id}/assign` | POST | 分派/转派 |
| `/api/tickets/{id}/status` | POST | 状态流转（accept/resolve/close/reopen，服务端校验非法流转） |
| `/api/tickets/{id}/comments` | POST | 追加备注（写入 event） |
| `/api/dashboard/summary` | GET | 指标卡 |
| `/api/dashboard/trend` | GET | 趋势（metric + range 7/30 天） |
| `/api/dashboard/distribution` | GET | 状态/分类/优先级分布 |
| `/api/dashboard/rankings` | GET | 分派对象负载排行 |

契约示例：

```markdown
### POST /api/auth/login
请求体：{"username":"string","password":"string"}
成功 200：{"code":200,"message":"success","data":{"access_token":"string","user":{"id":1,"name":"string","role":"运维|客服"}}}
失败 401：{"code":401,"message":"用户名或密码错误","data":null}

### GET /api/tickets
Query：status=待分派&category=服务器&priority=高&assignee_id=3&keyword=xxx&page=1&page_size=20&sort_by=created_at&sort_order=desc
成功 200：{"code":200,"data":{"items":[{"id":1,"ticket_no":"T-2026-0001","title":"...","category":"服务器","priority":"高","status":"待分派","assignee_id":null,"creator_id":1,"created_at":"2026-08-27T10:00:00","updated_at":"2026-08-27T10:00:00"}],"total":128,"page":1,"page_size":20}}
错误 401：{"code":401,"message":"未认证","data":null}
```

### C3 输出开发计划 docs/Plan.md

- 一、功能清单总览（F-01-01…F-05-05，MVP 优先级，状态=待开发）
- 二、数据契约摘要（完整契约以 PRD「数据契约确认清单」与 api-contracts.md 为唯一权威，不重复展开）
- 二点五、外部服务与测试权限清单：**本项目 MVP 零外部服务依赖**（承接 A5-3 落定版，状态无一停留「待确认」，无 Key/账号悬空项）
- 三、前端开发清单：技术选型表（框架 React / 语言 TypeScript / 构建 Vite / 路由 react-router / 状态 Zustand / 请求 Axios / 组件库 Ant Design / 图表 ECharts / 工程化 ESLint+Prettier+type-check+build）+ 页面×功能×Mock 来源（api-contracts.md）+ 前端自动验收标准（UI 与原型一致、Mock 可交互、格式与契约一致、Agent/Tester 自动验收通过；用户验收 UI/UX 后进入后端，`VITE_USE_MOCK=false` 切真实联调）
- 四、后端开发清单：B00 基础设施（pycore：ConfigManager/APIServer/db 模板，`GET /health`）→ B01 认证 → B02 工单 CRUD → B03 工单流转（依赖 B02）→ B04 元数据字典 → B05 仪表盘聚合（依赖 B02/B03）；基础设施自动连续执行不触发用户门禁，业务功能每闭环真实联调验收
- 五、功能详情（开发阶段由 Developer/Tester 逐个展开）
- 六、开发顺序建议：阶段1 前端 MVP（Mock，用户验收 UI）→ 阶段2 后端基础设施（自动）→ 阶段3 逐功能闭环（前后端切真实，每功能用户门禁）→ 阶段4 E2E 回归

### （可选）docs/data-system.json —— 决策见问题 6

本单为**含报表/仪表盘需求**的项目，全局规则明确 `docs/` 最终保留 `data-system.json`（如需要）。Agent 判定**需要**并在阶段 C 一并产出（结构为维度/指标/聚合规则/视图定义，供前端图表渲染与后端聚合查询对齐）。

**阶段 C 产物路径汇总**：`P\docs\PRD.md`（定稿）+ `P\docs\api-contracts.md` + `P\docs\Plan.md` + `P\docs\data-system.json`（可选报表类）。

### C 终态自检与收尾（临时产物清理 #2）

- 自检清单：无「待定/TBD」占位、功能均有优先级、核心流程图含主流程+异常分支、技术选型确定、PRD 与原型一致、含路线图/架构蓝图/原型说明章节、api-contracts 覆盖所有接口、Plan 含清单/契约/前后端清单、外部服务清单无待确认项、docs/ 仅保留核心产物且 .sdd/ 无残留草稿。
- **收尾**：删除 `.sdd/tmp/visual-research.md`（+ 关联截图 `.sdd/tmp/screenshots/*`）→ `P\.sdd\tmp\` 清空。
- 最终门禁：四件套齐全 + 临时产物已清理 + 用户确认 →「产品设计已完成。可以进入 Agent 开发流程。」

> ❗️❗️❗️ **C 完成确认点 9**：C 自检通过、临时产物已清理后，告知用户「产品设计已完成。可以进入Agent 开发流程。」用户确认后才算收尾，并通告可进入 Router 多 Agent 开发。

---

## 7. 最终文件清单（含完整路径）——对应问题 1

**设计阶段核心产物（常驻 docs/，保留到开发阶段）**：

```text
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\PRD.md
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\api-contracts.md
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\Plan.md
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\data-system.json        （可选·报表类产物，本单存在）
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\README.md
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\index.html
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\01-login.html
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\02-ticket-list.html
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\03-ticket-detail.html
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\04-create-ticket.html
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\05-dashboard.html
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\prototypes\assets\（css/js/示例数据）
```

**项目状态 / 脚手架（初始化脚本生成，设计流程只存在不新增）**：

```text
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\.sdd\project.json
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\docs\（初始空目录）
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\pycore\
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\README.md
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\.gitignore
E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\project-ops-desk\pyproject.toml
E:\SDD_V7_1_2\SDD_V7_1_2\project-registry.json                      （H 根·注册表，active=project-ops-desk）
```

**仅在设计过程中存在、阶段末已删除**：

```text
Existed during:  E:\...\project-ops-desk\.sdd\tmp\ui-design-spec.md      （B1 产出 → B2 完成后删）
Existed during:  E:\...\project-ops-desk\.sdd\tmp\visual-research.md     （R2 产出 → C 完成后删）
Existed during:  E:\...\project-ops-desk\.sdd\tmp\screenshots\*.png      （R1 证据，随 visual-research 删）
```

**设计结束时不存在的文件（开发阶段才产）**：`.sdd/tasks.json`（Planner）、`.sdd/test-reports/`（Tester）、`.sdd/experience.md`（本 Skill 收尾不回写经验）、`.sdd/status.json`、`.sdd/work-log.md`、`.sdd/bug-logs/`、`.sdd/bug_fix/`、`frontend/`、`backend/mobile 业务实现`、`docs/startup.md`、`docs/澄清文档/**`。

---

## 8. 临时产物与清理时机汇总——对应问题 2

| 临时产物 | 路径 | 产出阶段 | 消费 | 清理时机 | 权威依据 |
|---|---|---|---|---|---|
| 视觉调研 | `.sdd/tmp/visual-research.md` | 阶段 R | B1 / B2 | **阶段 C 全部完成、进入「产品设计完成」态时删除**（此前保留，供 api-contracts/Plan 参考原型上下文） | SKILL.md 映射表 + phase-R + phase-B2 收尾 |
| 视觉证据截图（辅助） | `.sdd/tmp/screenshots/*` | 阶段 R | B1 / B2 | 随 visual-research.md 在阶段 C 完成后一并清理 | 同上（属调研证据） |
| Design Spec | `.sdd/tmp/ui-design-spec.md` | 阶段 B1 | B2 | **B2 原型完成后立即删除**（唯一输入已被消费） | phase-B2 收尾 + 映射表 |
| Pencil 回退提示词 | `docs/prototypes/pencil-prompt.md` | 阶段 B2 | Pencil 用户 | 仅 Pencil 模式；`.pen` 落盘后可清理（可选）。**本单 HTML 模式不产出** | 映射表 |

另：R0 需求对齐摘要与竞品调研草稿只在对话中完成、不建文件，最终结论合入 PRD（精简产出原则）。

---

## 9. 六个问题直接回答

**Q1. 走完流程后最终存在哪些文件（含完整路径）？**
见第 7 节完整清单。核心 = 四件套 + `docs/prototypes/README.md` + `docs/data-system.json`（本项目含） + 脚手架/注册表；`.sdd/tmp/` 已清空。

**Q2. 哪些是临时产物？分别在哪个阶段、什么时机删除？**
三组：
1. `.sdd/tmp/ui-design-spec.md`（B1 产出）→ **B2 原型完成后立即删除**。
2. `.sdd/tmp/visual-research.md` + `.sdd/tmp/screenshots/*`（R 产出）→ **阶段 C 全部完成后删除**（B2 结束时仍保留）。
3. `docs/prototypes/pencil-prompt.md`：仅 Pencil 模式存在，本单 HTML 模式不产出。
判定成败的要害是：**visual-research 不是 B2 完就删，要留到 C 完成**；未按映射表清理即视为流程未收尾。

**Q3. 阶段 R/A/B1/B2/C 各自的产出文件写到哪里？**
- 阶段 R → 对话输出（对齐摘要/调研方案），视觉证据落 `.sdd/tmp/visual-research.md`（+截图）；竞品结论并入后续 PRD。
- 阶段 A → `docs/PRD.md`（唯一文件，初稿）。
- 阶段 B1 → `.sdd/tmp/ui-design-spec.md`（唯一输出）。
- 阶段 B2 → `docs/prototypes/`（HTML 页面 + README + assets；Pencil 模式追加 `pencil-prompt.md`）。
- 阶段 C → `docs/PRD.md`（定稿）+ `docs/api-contracts.md` + `docs/Plan.md` + 可选 `docs/data-system.json`。
- 统一规则：设计文档→`docs/`；流程状态/临时→`.sdd/`；临时 tmp→`.sdd/tmp/`。

**Q4. 如何根据已有产物判断当前阶段？**
按 SKILL.md 阶段判断表顺序检测：PRD 不存在/空 → R；PRD 缺完整数据契约章节 → A；PRD 契约完整且无 ui-design-spec → B1；ui-design-spec 存在 → B2；原型在但缺 api-contracts/Plan → C；四件套齐全且临时已清理 → 完成。仅凭产物存在性即可定位，支持断点恢复，无需额外状态文件。

**Q5. 完成后四件套（PRD/api-contracts/Plan/prototypes）是否齐全？还有没有其他文件被创建？**
四件套**齐全**。其他被创建的合法文件：`docs/prototypes/README.md`（B2 交接说明）、`docs/data-system.json`（可选报表类，本单存在）。初始化脚本产生的脚手架（`.sdd/project.json`、`docs/`、`pycore/`、README.md、.gitignore、pyproject.toml、注册表）。`.sdd/tmp/` 下三组临时产物已全部删除。被刻意**不创建**的：对齐澄清文档、roadmap-final.md/architecture-blueprint.md 等独立文件、经验/任务/测试报告、src 业务代码、startup.md。

**Q6. 有没有出现 data-system.json？如果有，为什么；如果没有，为什么？**
**有**。理由：
1. 本项目核心页面包含**统计仪表盘**（指标卡/趋势/状态分布/排行），属「数据系统 / 报表类」需求——SKILL.md 产出物映射表范围注释明确 `docs/data-system.json` 为「数据系统 / 报表类项目如需要，属可选产物」，全局规则亦将 `data-system.json`（如需要）列为 `docs/` 最终保留的核心设计产物之一。
2. 仪表盘的指标口径、维度、聚合规则属于产品级元数据，既不属于某个接口的响应格式（api-contracts 只管每个端点的请求/响应），又不适合塞进 PRD 表格（需结构化、可被前后端共同对齐），因此独立为 `docs/data-system.json`，阶段 C 产出、与四件套一并常驻 docs/。
3. 反例说明：若本项目无报表/仪表盘（纯 CRUD 流程），判定为「如不需要」就不产出——本单因存在统计仪表盘而产出。它**不占**四件套定义位（映射表权威四件套不含 data-system.json），属可选附加产物。

---

## 10. 各阶段用户交互/门禁点汇总（❗️❗️❗️）

| # | 位置 | 交互内容 |
|---|---|---|
| 0 | 入口 | 确认已绑定项目字段（project_id/name/path/repo_url） |
| 1 | R 门禁 | 确认竞品方向（融合方案）+ AI 默认配置项（本单 N/A） |
| 2~4 | A1/A2/A3 | 页面清单与跳转 / 功能与边界 / 版本规划 |
| 5 | A5-3 | 外部依赖与配置草稿逐项确认（本单 MVP 零外部依赖） |
| 6 | A 总确认 | 页面+功能+版本+外部依赖+PRD 一致，询问是否进入原型设计 |
| 7 | B1 | Design Spec 审阅确认，进入 B2 |
| 8 | B2 | 原型完成确认，进入 C |
| 9 | C | 完成自检与清理后，确认进入开发（「产品设计已完成。可以进入Agent 开发流程。」） |

R/B1/B2 三处阶段切换均由 Agent 先发起明确门禁问题，用户的前进意图只在 Agent 询问「是否进入下一阶段」之后才被解释为同意进入下一阶段（阶段切换协议）。

---

*（本文件为文字模拟产物，未真实创建/修改任何项目文件。真实执行本流程时，产物与路径与本文件所列完全一致。）*