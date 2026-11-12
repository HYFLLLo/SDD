# SDD 新建项目「运维工单管理后台」· 产品设计阶段全流程文字模拟

> 本文件是对勤务技能 `sdd-product-design-optimize-workspace/skill-snapshot`（SKILL.md + phase-R/A/B1/B2/C）的一次完整文字模拟执行，全程只模拟、不真实创建任何项目文件。
>
> 假设环境（本文档内所有项目相关路径均基于此）：
> - harness 根：`e:/SDD_V7_1_2/SDD_V7_1_2/`
> - `active_project_id = project-ops-desk`
> - `project_name = 运维工单管理后台`
> - `active_project_path = e:/SDD_V7_1_2/SDD_V7_1_2/Projects_Repo/project-ops-desk/`
> - `project_type = web`（用户明确要求桌面 Web 后台）
> - `repo_url = 未提供`
>
> 模拟假设：用户在每一道门禁处都回答「确认 / 继续」，否则流程按规则停滞（文中逐处标注门禁）。

---

## 0. 入口前置检查（对应 SKILL.md「入口前置检查」）

### 0.1 确认项目字段
从用户输入提取：

| 字段 | 值 | 判定 |
|------|-----|------|
| project_id | `project-ops-desk` | 合法（英数短横线），作为目录名 |
| project_name | `运维工单管理后台` | 展示名，可为中文 |
| project_type | `web` | 用户明确「后台 / 登录页…」，非 unknown |
| repo_url | 未设置 | 不写入注册表 repo_url 字段 |

字段齐全，不需向用户追问。

### 0.2 检查 project-registry.json
读取 `e:/SDD_V7_1_2/SDD_V7_1_2/project-registry.json`：
- `projects[].id` 中不存在 `project-ops-desk` → 允许创建新项目。
- 判定为「新项目」，不转入 `sdd-project-maintenance`。

### 0.3 检查 Projects_Repo 目录
检查 `Projects_Repo/project-ops-desk/` → 目录不存在（或为空壳）→ 符合「允许视为空项目」。

### 0.4 创建 / 绑定新项目
调用（按用户环境确认 python 指令）：
```text
python scripts/sdd_project.py new project-ops-desk --name "运维工单管理后台" --type web
```
脚本负责生成：
- `Projects_Repo/project-ops-desk/`
- `.sdd/project.json`
- `docs/`（空）
- `pycore/`、`README.md`、`.gitignore`、`pyproject.toml`（脚手架骨架）
- 初始化 Git 仓库
- 写 `project-registry.json`（新记录 + 置 `active_project_id = project-ops-desk`）

> 决策与理由：用户需求是一个全新后台，`project_type` 明确为桌面 Web，脚本不注入 repo_url。

### 0.5 进入阶段判断的必要条件（全满足）
- 注册表存在 `project-ops-desk` ✓
- `active_project_id = project-ops-desk` ✓
- `.sdd/project.json` 存在 ✓
- `docs/` 存在 ✓
- 无已有业务产物 ✓

按 SKILL.md 向用户输出绑定确认：
```text
已绑定新建项目：
project_id = project-ops-desk
project_name = 运维工单管理后台
active_project_path = Projects_Repo/project-ops-desk/
repo_url = 未设置
```

---

## 1. 阶段判断：判定起点在阶段 R

按 SKILL.md 判定表，对 `active_project_path` 内 `docs/` 与 `.sdd/` 依次检查（详细判定方法见第 10 节）：

- `docs/` 存在但为空、`docs/PRD.md` 不存在 → **阶段 R**，读取 `phase-R.md`。

---

## 2. 阶段 R 模拟（需求澄清 + 竞品调研 + 视觉证据）

### R0 需求澄清与用户对齐（一次门禁，不逐条 pipeline 卡）

**第一轮澄清**：用户已给出较完整描述，按「先总结已知、只追问缺口」策略：

```text
我先按当前信息理解为：
- 目标问题：企业内部工单录入 / 分派 / 跟踪 / 状态统计分散低效
- 目标用户：运维人员、客服人员
- 使用场景：每天录入、分派、跟踪工单；通过报表掌握工单状态
- 核心功能：登录、工单列表、工单详情、创建工单表单、统计仪表盘

还缺这些关键信息：
1. 工单状态有哪些（待处理/处理中/已完成/已关闭？）—— 未明确，我按默认枚举推进，标注「默认，可改」
2. 角色权限怎么分（运维/客服/管理员？）—— 同上按默认
3. 是否有附件/通知/SLA 诉求 —— 本期未提，按 V2 排期
```

用户确认（模拟）后进入**内部功能拆解 + 功能 Pipeline 拆解（一次整体呈现，随需求对齐摘要一次确认）**：

AI 功能识别：**本轮功能全部为普通 CRUD / 业务流程 / 数据查询 / 统计聚合，不含 AI 参与**。因此阶段 R 不补 AI 澄清，PRD 不写 AI 章节。

Pipeline 拆解（整体呈现，关键节点带默认值，仅歧义处追问）：

| 功能 | Pipeline 节点链 | 已确认/默认口径 |
|------|----------------|-----------------|
| 账号登录 | 输入账号密码 → 校验 → 签发 token → 进入仪表盘 | 账号密码登录（默认）；V2 可接企业 SSO/LDAP |
| 创建工单 | 填写工单信息（标题/描述/类型/优先级/分派人）→ 必填校验 → 创建 → 状态=待处理 | 必填：标题、描述、类型、优先级；分派人可选（默认，可改） |
| 工单列表 | 查询条件（状态/类型/优先级/关键字/时间范围）→ 分页列表 → 行内快操作（查看/分派/变更状态） | 筛选 + 分页 + 行内操作（默认） |
| 工单详情 | 查看全字段 → 状态流转（待处理→处理中→已完成/已关闭）→ 处理记录/留言 → 更新 | 状态机见 A3/A4；处理记录 V1 含文字记录 |
| 统计仪表盘 | 选择时间范围 → 聚合查询 → 指标卡片 + 状态分布 + 趋势 | V1 指标卡片 + 状态分布；趋势/下钻 V2 |

**需求对齐摘要**（对话中输出，用户确认后才能进竞品调研）：
```text
需求对齐摘要
- 项目目标：企业内部工单录入、分派、跟踪、统计的一体化后台
- 目标用户：运维人员、客服人员（管理员统一把关）
- 使用场景：桌面 Web，日常高频录入与处理，看板汇报
- 核心问题：工单流转不可见、统计靠手工
- 核心功能：登录 / 工单列表 / 工单详情 / 创建工单 / 统计仪表盘
- Pipeline 关键节点口径：见上表（含默认项）
- AI 功能判断：无
- AI 模型 / API 来源：不适用
- 智能边界：不适用
```

> 决策与理由：需求描述已足够清晰，**不转入** `alignment` Skill、**不产生** `docs/澄清文档/**` 文件；需求对齐全程在对话中完成，符合「禁止为过程产物单独建文件」精简原则。

**门禁 1**：用户确认需求对齐摘要。（未确认不得进入竞品调研。模拟假设已确认）

### R1 竞品调研执行（≥2 个，≥1 个国内）

方向 A — Jira Service Management（Atlassian，国际）：列表/详情严格工单流转、看板式仪表盘。
方向 B — PagerDuty（国际）：事件驱动的告警/工单，高信息密度，状态色标体系强。
方向 C — 腾讯蓝鲸智云 ITSM / BK（国内）：国内运维平台，结构朴素清晰、导航规整，贴合国内企业后台习惯。

| 竞品 | 目标用户/场景 | 核心交互/结构 | 视觉风格 | 可借鉴点 | 不采用点 |
|------|--------------|--------------|----------|----------|----------|
| JSM | IT 服务台工单 | 左导航+列表+详情页+状态流转 | 扁平台式、蓝灰 | 列表筛选+详情页的信息架构 | 不复制其商标/文案 |
| PagerDuty | 告警事件响应 | 高密度列表、状态色标、实时 | 深色底色可选、状态鲜明 | 状态色标体系、密度控制 | 不照搬品牌色彩 |
| 蓝鲸 ITSM | 国内企业运维 | 侧边栏+表单向导+工单流转 | 朴素、专业、中规中矩 | 导航结构、表单字段组织 | 不照搬其视觉细节 |

> 决策与理由：用户言明「参考主流的 SaaS 运维工具」。推荐**融合方案**：采用「ANT 蓝灰专业基底 + C 的规整导航 + A 的列表/详情信息架构 + B 的状态色标体系」。截图在模拟中按「无法自动截图」处理——按 phase-R.md，需要向用户说明并请求截图，或让用户明确允许基于文字调研继续（模拟假设：用户允许基于文字调研 + 用户口头描述继续，视觉方向在 B1 用 Ant Design 默认基底托底）。

### R2 调研产出与视觉证据落盘

用户在对话中选择「融合方案」后，将视觉证据写入（临时文件）：
```text
Projects_Repo/project-ops-desk/.sdd/tmp/visual-research.md
```
内容含：竞品视觉证据表、用户选定方向（融合）、可复用视觉规则（页面结构/组件形态/色彩倾向：专业蓝灰/信息密度：中）、原型阶段必须参考、禁止照搬清单。

> 决策与理由：本轮存在可复用视觉证据 → 按 phase-R.md 落盘视觉证据文件；该文件是临时产物，保留到 B2 之后（详见第 9 节清理时机）。关键产品结论（融合方案、竞品借鉴点）写入后续 `docs/PRD.md` 背景章节。

**阶段 R 门禁（门禁 2）**：向用户发起确认——竞品参考方向采用融合方案；无误导人。（无 AI 功能，第二问跳过。）
```text
请确认阶段 R 结果：
1. 竞品参考方向采用 融合方案（ANT 蓝灰专业基底 + 蓝鲸导航结构 + JSM 列表/详情架构 + PagerDuty 状态色标）？
确认后进入阶段 A。
```
（模拟假设已确认。）

---

## 3. 阶段 A 模拟（页面 → 功能 → 版本 → PRD）

进入条件：阶段 R 已确认。执行顺序禁止跳步：A1 → A2 → A3 → A4 → A5 → 落盘 PRD.md → 总确认。

### A1 页面梳理（门禁 3）

```markdown
### 页面清单

| 序号 | 页面名称 | 页面类型 | 可见角色 | 入口来源 | 跳转去向 |
|------|---------|---------|---------|---------|---------|
| P01 | 登录页 | 表单页 | 未登录用户 | 直接访问 | 仪表盘 / 工单列表 |
| P02 | 统计仪表盘 | 仪表盘 | 运维/客服/管理员 | 侧边栏 | 工单列表（携带筛选） |
| P03 | 工单列表 | 列表页 | 运维/客服/管理员 | 侧边栏 / 仪表盘卡片 | 工单详情 |
| P04 | 工单详情 | 详情页 | 运维/客服/管理员 | 列表行点击 | 状态流转 / 编辑 |
| P05 | 创建工单 | 表单页 | 运维/客服/管理员 | 工单列表「新建工单」按钮 | 工单详情 |
```

全局布局：桌面 Web，统一左侧边栏（工单列表 / 统计仪表盘）+ 顶部导航（当前用户、退出登录）；Ant Design 布局组件。

### A2 主要功能定义与分析（门禁 4）

按页逐项定义（功能编号 `F-{页面序号}-{功能序号}`），关键项摘录：

| 页面 | 功能 | 一句话描述 / 完成标准 | 边界（包含 / 不包含） |
|------|------|----------------------|----------------------|
| P01 | F-01-01 账号密码登录 | 凭账号密码获取 token 进入系统 | 不含第三方/OAuth登录（V2） |
| P01 | F-01-02 会话失效退出 | 退出登录并清除 token | 不含记住我（默认不做，可改） |
| P02 | F-02-01 工单指标概览 | 3-5 个指标卡片：待处理/处理中/今日新增/超时 | 不下钻明细（V2）；卡片点击跳转列表页带筛选 |
| P02 | F-02-02 工单状态分布 | 状态分布图（柱/饼） | 趋势图、SLA 达成率、导出（V2） |
| P03 | F-03-01 工单搜索与筛选 | 状态/类型/优先级/关键字/时间范围筛选 | 组合条件筛选；暂不存收藏视图 |
| P03 | F-03-02 工单分页列表 | 分页表格：编号/标题/类型/优先级/状态/分派人 | 列表不承载完整详情 |
| P03 | F-03-03 一行快操作 | 查看、分派、变更状态（下拉） | 批量操作（V2） |
| P04 | F-04-01 工单详情展示 | 全字段展示 + 创建/更新时间 | 附件展示（V2） |
| P04 | F-04-02 状态流转 | 按状态机变更：待处理→处理中→已完成/已关闭；已关闭可重新打开 | 不允许非法跳转（如待处理→已完成由后端校验） |
| P04 | F-04-03 处理记录留言 | 追加文字处理记录 | 回复通知、@提及（V2） |
| P05 | F-05-01 新建工单表单 | 必填(标题/描述/类型/优先级)+可打分派人 → 提交建单 | 附件上传（V2）、模板建单（V2） |

### A3 版本规划（门禁 5）

**Mission**：让运维与客服在一个干净专业的后台里，完成工单一站式录入、分派、跟踪与统计。
**Persona**：一线运维员工（录单/处理/报结）、客服坐席（代客录单/跟进）、运维组长/管理员（分派、盯看板）。

#### V1 / MVP
| 页面 | 包含功能 | 排除（延后） | 理由 |
|------|---------|-------------|------|
| P01 登录页 | F-01-01, F-01-02 | 第三方登录/SSO | 内部账号体系即可支撑 MVP，SSO 需企业目录配置 |
| P02 统计仪表盘 | F-02-01 指标概览、F-02-02 状态分布 | 趋势图/下钻/SLA 报表 | 基础看板先可用，深度报表需更多数据积累 |
| P03 工单列表 | F-03-01~F-03-03 | 批量操作、收藏视图 | 批量是高阶效率功能 |
| P04 工单详情 | F-04-01~F-04-03 | 附件、@提醒 | 附件需对象存储，属外部依赖 |
| P05 创建工单 | F-05-01 | 附件、模板 | 同 P04 |

#### V2+
| 功能 | 预计版本 | 延后理由 |
|------|---------|---------|
| 附件上传（对象存储 OSS） | V1.1 | 引入外部依赖与安全合规 |
| 趋势/下钻/SLA 报表导出 | V1.1 | 需聚合性能优化与图表库 |
| IM/邮件通知 Webhook | V1.2 | 需外部服务与配置 |
| 企业 SSO / LDAP 登录 | V1.2 | 需企业目录服务方配合 |
| 批量操作、模板建单、角色权限管理 | V1.2~V2 | 非核心高频 |

**业务规则（Business Rules）**：
- 工单状态机：`待处理 → 处理中 → 已完成`；`待处理 / 处理中 → 已关闭（需关闭原因）`；`已关闭 → 重新打开 → 处理中`。非法跳转由后端校验拒绝。
- 类型枚举：故障 / 咨询 / 变更 / 投诉（默认，可改）。
- 优先级枚举：紧急 / 高 / 中 / 低（默认，可改）。
- 分派对象仅限「运维」角色；客服可录单，管理员可删改。

### A4 关键功能实现思路（穿插式，不单独设门禁，随总确认）

只覆盖复杂链路/关键技术选型，普通 CRUD 不写 A4：

**链路 1：工单状态流转（P04）**
- 触发场景：详情页点击「处理中 / 完成 / 关闭」
- 实现思路：前端按状态机渲染可用动作，后端在 `PATCH /api/tickets/{id}/status` 校验源状态 → 目标状态合法性与权限；不合法返回 400。
- 待确认问题：已关闭后重新打开是否需管理员权限？（默认：允许运维角色，标注「默认，可改」）

**链路 2：统计仪表盘聚合（P02）**
- 触发场景：进入仪表盘 / 切换时间范围
- 实现思路：V1 由 `GET /api/dashboard/overview` 单接口聚合返回指标+分布；时间范围作为查询参数；后端按状态、type 字段 GROUP BY 聚合，去重索引保证列表查询不拖慢看板。
- 待确认问题：统计口径（按创建时间 vs 按更新时间）？（默认按创建时间，标注「默认，可改」）

### A5 数据契约确认（不设用户门禁，Agent 自检）

**A5-1 业务数据契约（checklist，进入 PRD）**：
- 用户/角色：id、name、username、role(枚举：ops 运维 / support 客服 / admin 管理员)
- 工单：id、ticket_no（编号，后端生成）、title、description、type(枚举)、priority(枚举)、status(枚举)、creator_id、assignee_id、closed_reason、created_at、updated_at、closed_at
- 状态枚举：pending 待处理 / processing 处理中 / completed 已完成 / closed 已关闭
- 处理记录：id、ticket_id、user_id、content、created_at
- 权限角色：管理员=全部；运维=创建/分派收单/处理/流转/看板；客服=录单/跟进/看板
- 分页契约：items / total / page / page_size；page_size 默认 20

**A5-2 接口响应格式契约（必须在此阶段锁死）**：
- 成功：`{"code":200,"message":"success","data":{...}}`
- 错误：`{"code":<错误码>,"message":"<描述>","data":null}`
- 分页：`{"code":200,"data":{"items":[...],"total":100,"page":1,"page_size":20}}`
- HTTP：200 成功 / 400 参数错误 / 401 未认证 / 403 无权限 / 404 不存在 / 500 服务器错误

**A5-3 外部依赖与配置草稿（需用户确认，逐项过）**：

| 依赖 | 用途 | 关键配置字段 | Key/账号来源 | 存放位置 | 缺失时策略 | 状态 |
|------|------|-------------|-------------|----------|-----------|------|
| LLM | — | — | 无 | — | 无 | 无（不适用） |
| 对象存储（OSS/S3） | 附件上传（V2） | `OSS_*` | 暂缺（V2 引入） | backend/.env | V1 不做附件，降级本地 | V2 暂缓 |
| IM/邮件通知 | 流转通知（V2） | `WEBHOOK_URL` 等 | 暂缺 | backend/.env | Mock | V2 暂缓 |
| 企业 SSO/LDAP | 单点登录（V2） | `LDAP_*`/`SSO_*` | 暂缺 | backend/.env | V1 内部账号体系 | V2 暂缓 |
| 短信/支付/地图/风控 | — | — | — | — | — | 无 |

> 决策与理由：MVP 功能链路中**不使用任何第三方外部服务**（数据库为自建 PostgreSQL、认证为自签 JWT，属于自研组件而非外部第三方依赖）→ 草稿中除 V2 候选人外显式按类别写「无」，符合「允许填占位但不得缺项」。V1 无外部依赖 doesn't 阻塞开发。

### 落盘：docs/PRD.md（阶段 A 初稿）

将 A1~A5 全部写入（单一文件持续迭代）：
```text
Projects_Repo/project-ops-desk/docs/PRD.md
```
结构：1 背景与调研结论（承接 R0/R1）→ 2 页面清单与跳转（A1）→ 3 主要功能定义与边界（A2）→ 4 Mission/Persona/版本规划（A3）→ 5 复杂链路+关键实现思路（A4）→ 6 数据契约确认清单（A5-1+A5-2）→ 7 外部依赖与配置草稿（A5-3）。

### 阶段 A 总确认（门禁 6）
```text
请确认：页面清单、功能定义与边界、版本规划、外部依赖与配置草稿（逐项过一遍）、PRD.md 是否一致且无重大遗漏。
是否进入原型设计阶段？
```
（模拟假设已确认。）

---

## 4. 阶段 B1 模拟（Design Context + Design Spec）

- 根据 PRD 列出 MVP 界面清单：P01 登录 / P02 仪表盘 / P03 工单列表 / P04 工单详情 / P05 创建工单。
- **读取视觉调研上下文**：`.sdd/tmp/visual-research.md` 存在 → 提取「融合方向、蓝灰专业基底、可借鉴结构/组件形态、信息密度」。
- **收集 Design Context**：无品牌规范/Logo/codebase → 采用默认设计基底（桌面 Web 走 Ant Design 风格），Design Spec 中标注 `visual_research_status: ready`。
- **确定设计方向**：阶段 R 已确认融合方案 → 沿用，不另起炉灶，**不触发**设计方向顾问 fallback。
- **撰写 Design Spec**（临时文件）：
```text
Projects_Repo/project-ops-desk/.sdd/tmp/ui-design-spec.md
```
内容严格按模板：界面清单（5 界面 + 视口 1440×900）、设计方向（企业专业·蓝灰白基底）、核心资产（Logo：无 / codebase：无 → 默认基底）、视觉规格（色板 Primary 为专业蓝、字体 sans-serif、信息密度：克制型）、组件与页面结构（侧边导航 / 表格 / 表单 / 详情区块 / 指标卡片 / 状态 Tag）、签名细节（状态 Tag + 色标体系）、设计禁区、气质关键词（专业、清晰、克制、可信、高效）。

**门禁 7**：`Design Spec 已完成，请审阅。确认后进入阶段 B2 原型设计。`（模拟假设已确认。）

---

## 5. 阶段 B2 模拟（原型设计）

### 前置加载
读取 `e:/SDD_V7_1_2/SDD_V7_1_2/harness-core/skills/ui-design-standard/SKILL.md`（可读性/中文/组件状态/视口/竞品参考边界/原型与生产边界）。

### 原型架构选择（先于工具选择）
根据 Design Spec：本项目为 **桌面 Web 后台（SaaS/工具控制台）** → 原型形态：1480 规格——「桌面 Web 原型」；考虑到需要点击走流程，同时具备**单机流程演示**性质。Design Spec 已给出建议 → 直接采用，不再二次询问。

### 工具选择
默认 **HTML 原型**；不使用 Pencil / Stitch（用户未指定画布偏好）。

### Junior Pass 判定 → 跳过
按触发条件核查：Design Spec 明确（含竞品视觉证据）✓；原型界面数 = 5（不超 5）✓；无复杂演示路径 ✓。**可跳过 Junior Pass，直接 Full Pass**，输出标注：
```text
已走快速路径：Design Spec 明确，直接生成高保真原型。
```

### Full Pass · 模式 A（HTML）
按 Design Spec 逐页绘制，中文真实示例数据，可点击流（登录 → 列表 → 详情 → 状态流转；列表 → 新建 → 详情），最小状态机；桌面 1440×900 视口验证。输出：
```text
Projects_Repo/project-ops-desk/docs/prototypes/
├── index.html              # 入口/总览
├── 01-login.html           # P01 登录页
├── 02-dashboard.html       # P02 统计仪表盘
├── 03-ticket-list.html     # P03 工单列表
├── 04-ticket-detail.html   # P04 工单详情
├── 05-create-ticket.html   # P05 创建工单
├── assets/                 # css/js/示意图
└── README.md               # 生产前端交接说明
```
`README.md` 标注：页面清单、关键组件清单（侧边导航/Table/Form/详情区块/指标卡片/状态 Tag）、交互状态、Mock 数据结构、需要真实 API 的位置、哪些视觉效果必须生产实现。

### 原型验证清单（全过）
浏览器可打开 / 无 JS 错误 / 无重叠溢出 / 与 ui-design-spec 组件清单一致 / 视口 1440×900 截图正常 / 关键点击路径可走通（≥3）/ 全中文。

### 收尾（清理时机在此）
1. 原型输出到 `docs/prototypes/` ✓
2. **删除临时文件 `.sdd/tmp/ui-design-spec.md`**（B2 收尾就删）
3. `.sdd/tmp/visual-research.md` **保留**到阶段 C 完成后再删（确保 C 的 api-contracts/Plan 可参考原型上下文）
4. 门禁 8：`阶段 B2 原型已完成，请确认是否进入阶段 C。`（模拟假设已确认。）

---

## 6. 阶段 C 模拟（PRD 定稿 + api-contracts + Plan）

### C1 PRD.md 定稿
在阶段 A 初稿上补充：路线图（版本规划终版）、技术架构蓝图（前端 React+TS+Vite+AntD / 后端 Python3.11+FastAPI+PyCore / PostgreSQL / JWT；部署 Docker）、原型说明（prototypes 5 页面 ↔ PRD 页面映射）、核心流程图（Mermaid `flowchart`：登录 → 列表 → 建单 → 详情 → 状态流转，含异常分支如非法状态流转返回 400、关闭需原因）、组件交互说明、技术选型与风险（图表库 V2、聚合查询索引、附件安全）。
**不生成** roadmap-final.md / architecture-blueprint.md 等独立文件——全部合并 PRD。

### C2 api-contracts.md（唯一对齐依据）
```text
Projects_Repo/project-ops-desk/docs/api-contracts.md
```
覆盖全部 V1 接口（每个含方法/路径/请求体/成功响应/至少一种错误响应，遵循 A5-2 锁死格式）：
- `POST /api/auth/login`（401 密码错）
- `POST /api/auth/logout`
- `GET  /api/users?role=`（分派人下拉）
- `GET  /api/tickets?status&type&priority&keyword&start&end&page&page_size`（分页/筛选）
- `POST /api/tickets`（创建，400 校验失败）
- `GET  /api/tickets/{id}`（详情+处理记录）
- `PUT  /api/tickets/{id}`（编辑）
- `POST /api/tickets/{id}/assign`（分派/转派）
- `PATCH /api/tickets/{id}/status`（状态流转，400 非法流转 / 403 无权限）
- `POST /api/tickets/{id}/comments`（处理留言）
- `GET  /api/dashboard/overview?range=`（指标+分布聚合）

### C3 Plan.md
```text
Projects_Repo/project-ops-desk/docs/Plan.md
```
一、功能清单总览表（F01 登录 / F02 指标概览 / F03 状态分布 / F04 列表筛选 / F05 分页列表 / F06 行内快操作 / F07 详情展示 / F08 状态流转 / F09 处理记录 / F10 建单，标 MVP）；二、数据契约摘要（指向 PRD，不重复）；二点五、外部服务与测试权限清单（与 A5-3 一致，全「无 / V2 暂缓」，V1 无悬空 Key）；三、前端开发清单（技术选型表：React/TS/Vite/react-router/Zustand/Axios/Ant Design/TanStack Query 可选；页面 ↔ Mock 数据来源 api-contracts）；四、后端开发清单（B00 基础设施 pycore GET /health → B01 认证 → B02 工单 → B03 详情/记录 → B04 分派 → B05 状态流转 → B06 统计）；五、功能详情（开发展开）；六、开发顺序建议（阶段 1 前端 Mock 用户验收 → 阶段 2 后端基础设施自动 → 阶段 3 逐功能闭环联调 → 阶段 4 E2E）。

### PRD 自检（逐项核对，不过则返回修复）
- 无「待定 / TBD」占位 ✓；每个功能有优先级 ✓；流程图含主流程+异常分支（非法状态流转、关闭缺原因）✓；技术选型已定 ✓；与原型一致 ✓；PRD 含路线图/架构蓝图/原型说明 ✓；api-contracts 全覆盖 ✓；Plan 全要素 ✓；外部服务清单无悬空 ✓；`docs/` 收齐、`.sdd/` 无残留草稿（删掉 visual-research.md）✓

### 阶段 C 完成
```
产品设计已完成。你可以在当前对话中说"开始开发"，我会按 Router 进入多 Agent 开发流程。
```

---

## 7. 问答 1：最终存在哪些文件（含完整路径）

产品设计完成、临时产物清理后，**最终保留**：

```text
e:/SDD_V7_1_2/SDD_V7_1_2/
├── project-registry.json                                   # harness 级：新增 project-ops-desk 记录 + active_project_id 指向
└── Projects_Repo/project-ops-desk/
    ├── .sdd/
    │   ├── project.json            # 项目状态（script 初始化；含 name/type/active 等）
    │   └── tmp/                    # 临时目录，已清空（两个临时文件均删）
    ├── docs/
    │   ├── PRD.md                  # 阶段 A 初稿 + 阶段 C 定稿
    │   ├── api-contracts.md        # 阶段 C2
    │   ├── Plan.md                 # 阶段 C3
    │   └── prototypes/             # 阶段 B2（持续产物）
    │       ├── index.html
    │       ├── 01-login.html
    │       ├── 02-dashboard.html
    │       ├── 03-ticket-list.html
    │       ├── 04-ticket-detail.html
    │       ├── 05-create-ticket.html
    │       ├── assets/
    │       └── README.md           # 生产前端交接说明
    ├── pycore/                     # script 初始化脚手架（开发阶段使用）
    ├── README.md                   # script 初始化
    ├── .gitignore                  # script 初始化
    ├── pyproject.toml              # script 初始化
    └── .git/                       # script 初始化
```

说明：`frontend/ backend/ mobile/`、`.sdd/tasks.json`、`.sdd/experience.md` 等属于**开发阶段**产物，产品设计阶段不计入；`docs/澄清文档/**`、`roadmap-final.md`、`architecture-blueprint.md` 在本流程中被明确禁止/不触发，不存在。

---

## 8. 问答 2：临时产物、删除阶段与时机

| 临时产物 | 完整路径 | 创建阶段/时机 | 删除阶段/时机 | 理由 |
|---------|---------|--------------|--------------|------|
| 视觉证据文件 | `Projects_Repo/project-ops-desk/.sdd/tmp/visual-research.md` | 阶段 R2（用户选定方向后落盘） | **阶段 C 完成收尾时删除**（phase-B2 明确「可保留到阶段 C 完成后再删除，确保 API 契约和 Plan 能参考原型上下文」） | 供 B1 提取视觉规则、B2 画原型、C 写契约/计划时回看；C 自检要求 `.sdd/` 无残留草稿 |
| Design Spec | `Projects_Repo/project-ops-desk/.sdd/tmp/ui-design-spec.md` | 阶段 B1（写 Design Spec） | **阶段 B2 收尾第 2 步删除**（原型产出并验证通过后立即删） | 原型已完成，Spec 的使命结束；避免与原型/生产前端产生双源歧义 |

> 两类文件删除后，`.sdd/tmp/` 目录内为空。SKILL.md 全局规则亦强调 `.sdd/` 只保留状态、任务、经验、日志、报告，无残留草稿。另注意 R2 提到视觉证据「保留到 B2 原型完成后再清理」，而 B2 收尾给出了更晚的具体时机（C 之后）——按 phase-B2 的最新、更具体表述执行。

---

## 9. 问答 3：各阶段产出写入路径

| 阶段 | 产出文件 / 动作 | 完整路径 |
|------|----------------|---------|
| 入口 | 注册表记录 + active 设置 + 项目脚手架 | `project-registry.json`（harness 根）；`Projects_Repo/project-ops-desk/.sdd/project.json`、`docs/`、`pycore/`、`README.md`、`.gitignore`、`pyproject.toml`、`.git/` |
| R | 需求对齐摘要（对话）→ 视觉证据（临时） | 摘要：仅对话，落 PRD 背景章节；证据：`Projects_Repo/project-ops-desk/.sdd/tmp/visual-research.md` |
| A | PRD.md 初稿 | `Projects_Repo/project-ops-desk/docs/PRD.md`（A1→A5 全部章节，单一文件） |
| B1 | Design Spec（临时） | `Projects_Repo/project-ops-desk/.sdd/tmp/ui-design-spec.md` |
| B2 | 原型 + 交接说明（持续产物） | `Projects_Repo/project-ops-desk/docs/prototypes/`（index.html + 5 个页面 + assets/ + README.md）；并删除 ui-design-spec.md |
| C | PRD 定稿 / api-contracts / Plan（持续产物） | `docs/PRD.md`（更新定稿）、`docs/api-contracts.md`、`docs/Plan.md`；并删除 visual-research.md |

---

## 10. 问答 4：如何根据已有产物判断当前阶段（判定表）

每次交互/切换前，只检查 `active_project_path` 下的 `docs/` 与 `.sdd/`（禁止读 harness 根同名目录），按序命中即止：

| 判定条件（按序检查） | 判定阶段 | 动作 |
|------|------|------|
| `docs/` 不存在或为空，或 `docs/PRD.md` 不存在 | 阶段 R | 读 phase-R.md |
| `docs/PRD.md` 存在，但缺少**完整数据契约章节**（数据契约确认清单 + 接口响应格式契约） | 阶段 A | 读 phase-A.md |
| `docs/PRD.md` + 数据契约完整，但 `.sdd/tmp/ui-design-spec.md` 不存在 | 阶段 B1 | 读 phase-B1.md |
| `.sdd/tmp/ui-design-spec.md` 存在，或 `docs/prototypes/` 缺少原型 | 阶段 B2 | 读 phase-B2.md |
| 原型已完成，但 `docs/api-contracts.md` 或 `docs/Plan.md` 缺失 | 阶段 C | 读 phase-C.md |
| `docs/PRD.md` + `docs/api-contracts.md` + `docs/Plan.md` + `docs/prototypes/` 齐全 | 产品设计完成 | 告知可进入开发 |

对本项目实际运行中的对照：
- 起点：`docs/` 空 → **阶段 R**。
- R 结束/A 中途中断：`PRD.md` 不存在 → R；`PRD.md` 存在缺契约章节 → A。
- A 完成/B1 前：`PRD.md` 完整、`ui-design-spec.md` 无 → **B1**。
- B1 完成/B2：`ui-design-spec.md` 存在 → **B2**；或 B2 删除 Spec 但原型缺失 → 仍命「`docs/prototypes/` 缺少原型」→ B2（该 OR 条件保证中断后的幂等恢复）。
- B2 完成/C：原型齐全、`api-contracts.md` 或 `Plan.md` 缺失 → **C**。
- 全部齐全 → 完成。判定表并用「`.sdd/tmp/` 有无」与「`docs/` 四件套齐缺」双维度，天然容忍中断恢复。

---

## 11. 问答 5：四件套是否齐全？还有其他文件被创建吗？

**齐全**。结束后 `docs/` 下四件套完整：
- `docs/PRD.md`
- `docs/api-contracts.md`
- `docs/Plan.md`
- `docs/prototypes/`（含 README.md / assets）

**其他被创建的文件**（非四件套）：
1. `Projects_Repo/project-ops-desk/.sdd/project.json`——脚本初始化，属 `.sdd/` 状态文件（流程内更新）。
2. `Projects_Repo/project-ops-desk/docs/prototypes/README.md`——原型的生产交接说明，算 `prototypes/` 体系的组成部分。
3. `.sdd/tmp/visual-research.md`、`.sdd/tmp/ui-design-spec.md`——临时产物，阶段内存在、最终删除。
4. `project-registry.json`（harness 根）——注册表新增记录 + active 指向。
5. 脚本初始化文件 `pycore/`、`README.md`、`.gitignore`、`pyproject.toml`、`.git/`——入口阶段生成，非设计流程产物。

未创建：`data-system.json`（见问答 6）、`docs/澄清文档/**`、`docs/prototypes/pencil-prompt.md`（HTML 模式不产生）、`roadmap-final.md` / `architecture-blueprint.md`（C1 明确禁止单独建）、`.sdd/tasks.json`（开发阶段）。

---

## 12. 问答 6：data-system.json 是否出现？为什么？

**不出现（不创建）。** 理由：

1. 在 skill-snapshot 的全局规则中，`data-system.json` 被列为「如需要」的可选产物（`PRD.md、api-contracts.md、Plan.md、data-system.json（如需要）、prototypes/`）。
2. 本流程的 5 个阶段文件（phase-R/A/B1/B2/C）**没有任一步骤指示生成或写入 `data-system.json`**，也定义了它的结构/内容来源。数据契约的载体是：
   - PRD.md 的「数据契约确认清单」章节（A5-1 业务数据契约 + A5-2 接口响应格式契约）——锁业务口径；
   - api-contracts.md——锁每个接口的完整请求/响应，被定义为「前端 Mock 和后端实现的唯一对齐依据」，即接口层唯一权威源。
3. 本项目（运维工单）数据模型体量中等（用户/角色/工单/处理记录四类核心实体 + 枚举状态机），**全部可被 PRD 数据契约 + api-contracts 完整承载**，没有需要独立产出的跨域数据系统沉淀，因此不满足「如需要」的触发。
4. 结论：若未来项目出现复杂跨域数据模型（如多系统实体关系、需要独立数据集市/字典文件），可按 SKILL.md「如需要」的开关补生成；当前项目不生成。

---

## 13. 关键决策与理由汇总

| # | 决策点 | 结论 | 理由 |
|---|-------|------|------|
| D1 | project_type | web | 用户明确「登录页/后台」，桌面 Web |
| D2 | 竞品方向 | 融合方案（蓝灰专业基底+蓝鲸导航+JSM 列表/详情+PagerDuty 色标） | 匹配「主流 SaaS 运维工具」诉求，避免单一照搬 |
| D3 | AI 功能 | 无 | 全部功能为 CRUD/流程/统计，无理解/生成/推荐类需求，PRD 不写 AI 章节 |
| D4 | V1 范围 | 五页面全进 MVP，附件/通知/SSO/深度报表进 V2 | 复杂度、外部依赖、数据积累是切分依据，非随意罗列 |
| D5 | V1 外部依赖 | 无第三方外部依赖（数据库/认证自研） | A5-3 显式逐类写「无」，防缺项；V2 候选登记为占位暂缓 |
| D6 | 数据契约载体 | PRD 章节 + api-contracts，不生成 data-system.json | 「如需要」未触发；api-contracts 是接口唯一权威源 |
| D7 | 原型架构/工具 | 桌面 Web + HTML 原型（默认），可点击流 | 后台/SaaS 场景；DD spec 已给建议，不再二次问 |
| D8 | Junior Pass | 跳过，直接 Full Pass | Design Spec 明确、界面数=5、路径不复杂，符合跳过条件并标注 |
| D9 | 临时文件清理 | ui-design-spec 在 B2 收尾删；visual-research 在 C 完成后删 | B2/C 的明确收尾约定 + 保证 `.sdd/` 无残留草稿 |
| D10 | 定稿合并 | 不建 roadmap-final / architecture-blueprint 独立文件 | C1 强制并入 PRD，精简产出 |

---

## 14. 全流程门禁点汇总（用户确认时机）

| 门禁 | 位置 | 确认内容 |
|------|------|---------|
| 1 | R0 结束 | 需求对齐摘要 |
| 2 | 阶段 R 门禁 | 竞品参考方向（融合方案） |
| 3 | A1 结束 | 页面清单与跳转逻辑 |
| 4 | A2 结束 | 所有页面功能清单与边界 |
| 5 | A3 结束 | 版本规划（V1/V2 取舍） |
| 6 | 阶段 A 总确认 | 页面+功能+版本+外部依赖草稿（A5-3 逐项）+ PRD.md |
| 7 | B1 结束 | Design Spec 审阅，确认进入 B2 |
| 8 | B2 收尾 | 原型确认，明确「进入阶段 C」（未经明确确认不得执行 C） |
| — | 阶段 C 完成 | 产品设计完成，告知可进入开发（A5-1/A5-2 数据契约为 Agent 自检，不设用户门禁） |