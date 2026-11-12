# Eval Task T2 · Mobile H5 记账应用 · 产品设计阶段完整文字模拟

> 执行方式：g 全程文字模拟，**不真实创建任何目录/文件**。以 `active_project_id = project-accounting-h5`、`active_project_path = Projects_Repo/project-accounting-h5/`、`project_type = mobile` 为例。
> 依据：`harness-core/skills/sdd-product-design/SKILL.md` 及其 `phase-R.md / phase-A.md / phase-B1.md / phase-B2.md / phase-C.md`。SKILL.md「产出物映射表」为设计阶段产物的唯一权威口径，各阶段文件若与其有出入一律以映射表为准。

---

## 0. 入口前置检查（Skill 触发后、进入阶段判断前）

1. 确认项目字段
   - `project_id = project-accounting-h5`（仅英文/数字/短横线，可作目录名 ✓）
   - `project_name = 指尖记账 / 记账本 H5（展示名）`
   - `project_type = mobile`（✨ 用户明确"手机端 H5"，因此标记为 mobile 而非 unknown）
   - `repo_url = 未提供`

2. 检查 `project-registry.json`
   - 现有项目仅 `draw-telephone`（web），**不存在 `project-accounting-h5`** → 允许新建。
   - `active_project_id` 当前指向 `draw-telephone`，待绑定后切换到新项目。

3. 检查 `Projects_Repo/project-accounting-h5/`
   - 目录不存在 → 视为空项目，可走新建流程。

4. 创建/绑定新项目（模拟执行）
   ```
   python scripts/sdd_project.py new project-accounting-h5 --name "记账本 H5" --type mobile
   ```
   脚本负责：创建 `Projects_Repo/project-accounting-h5/`、初始化 `.sdd/project.json`、`docs/`、Git 仓库、写入 `project-registry.json`、设置 `active_project_id`。
   - 模拟的脚手架产物（"允许视为空项目"清单内的初始化文件）：`.sdd/`、`docs/`、`docs/prototypes/`、`docs/澄清文档/`、`pycore/`、`README.md`、`.gitignore`、`pyproject.toml`（由 `scripts/sdd_project.py` 的 `ensure_project_dirs` 逻辑生成）。

5. 进入阶段判断的必要条件全部满足后，向用户出示：
   ```
   已绑定新建项目：
   project_id = project-accounting-h5
   project_name = 记账本 H5
   active_project_path = Projects_Repo/project-accounting-h5/
   repo_url = 未设置
   ```

## 阶段判定
- `docs/PRD.md` 不存在 → **判定当前处于阶段 R**，读取并执行 `phase-R.md`。

---

## 1. 阶段 R：需求澄清 + 竞品调研 + 视觉证据

### R0 需求澄清与用户对齐
- **第一轮澄清**按模板向用户提出四个产品问题：解决什么问题 / 目标用户 / 使用场景 / 大致包含哪些功能。用户已给出基本描述，Agent 先总结已知信息、只追问缺口（如：单用户还是多用户、是否要预算/报表导出、是否要 AI 自动记账）。
- **功能拆解**（Agent 内部）：围绕默认栈（前端 React + TS + Vite / 移动端 H5 用 Ant Design Mobile / 后端 Python 3.11+ / FastAPI / PyCore / 响应 `code/message/data`）判断——添加账单、账单列表、分类统计、个人中心均为**普通 CRUD + 数据查询 + 页面交互，无 AI 功能** → PRD 不写 AI 章节，外部依赖草稿中 AI 行写"无"。
- **功能 Pipeline 拆解**（一次性整体呈现，随摘要一次确认，不逐条卡门禁）：
  1. 添加账单：选择分类 → 输入金额 → 选择支付方式/账户 → 备注/标签 → 保存 → 列表与统计即时刷新。默认：账本单本制、分类按收支预置 9 大类（餐饮/交通/购物/居住/娱乐/医疗/教育/其他 + 收入类）、金额两位小数、日期默认今天。
  2. 账单列表：按日期（默认当月）倒序聚合展示 → 可切换月份 → 点击进入编辑 → 滑动删除/长按删除（触发二次确认）。默认：按"今天/昨天/日期"分组、未做无限滚动（MVP 分页或加载更多）。
  3. 分类统计：时间范围（月/年/自选）→ 按分类聚合金额 → 环形/条形图 + 明细列表。默认：图表 MVP 用 Ant Design Mobile 图表或轻量 SVG 自绘，V2 评估引入专业图表库。
  4. 个人中心：显示头像昵称、账本信息、设置（默认币种、预算提醒开关）、关于。MVP 不做多账本/登录，本地优先（详见 A3）。
  → 关键节点口径全部采用推荐默认，标注"默认，可改"，无歧义节点不追问。
- **AI 功能补充澄清**：不触发（无 AI 功能）。
- **需求对齐摘要**在对话中输出，**经用户确认后**才进入 R1。

### R1 竞品调研执行
- 明确为 H5 场景，**至少 2 个竞品、至少 1 个国内产品**。模拟候选：
  1. 钱迹（Xiaomi 生态）——钱包/随手记类，参考：分类+日期双 tab 结构、清爽白底、卡片式分类统计入口。
  2. 鲨鱼记账——参考：按月切换的流水页、分类图标体系、统计环形图。
  3. 随手记 / 贴吧"记账 App"UI 合集、iOS 提醒事项式"清新列表"范式——作为相邻参考。
- 每个竞品记录：名称/URL、目标用户与核心场景、关键流程、核心交互、页面结构、视觉风格、组件形态（底部 Tab 导航、卡片、表单、列表、详情、CTA）、可借鉴点、不采用点、视觉证据路径。若无法截图，须说明原因并请用户提供截图或确认仅文字调研。
- 用户选定参考方向后进入 R2。

### R2 调研产出与视觉证据落盘
- 竞品参考方向在对话中给用户选 A/B/C 或融合方案，采用"融合方案"：**钱迹的列表聚合 + 鲨鱼的分类统计 + 统一清新浅色（白底 + 单一绿/青 accent）**，理由：契合"清新简单、手机浏览"的目标。
- 存在可复用视觉证据 → 写入 **`.sdd/tmp/visual-research.md`**，内容含：竞品视觉证据表、用户选定方向与原因、可复用视觉规则（页面结构/组件形态/色彩倾向/字号/间距圆角阴影/信息密度）、原型阶段必须参考的截图或 URL、禁止照搬清单。
- 关键产品结论摘要进后续 PRD.md 背景章节。
- **废弃分支（备查）**：若确认无可用视觉证据，则**不强制创建** visual-research.md，对话说明原因，B1 改用默认设计基底（Ant Design Mobile）继续。

### 阶段 R 门禁
```
请确认阶段 R 结果：
1. 竞品参考方向采用"融合方案"是否可以？
2. 本项目无 AI 功能，无需确认 AI 默认配置。
```
**未确认不得进入阶段 A。**

> R 阶段落盘产物：
> - `.sdd/tmp/visual-research.md`（临时产物，保留到阶段 C 完成后删除）
> - PRD.md 此时**尚未创建**（背景结论先在对话中沉淀，阶段 A 落盘时合并写入）

---

## 2. 阶段 A：页面 → 功能 → 版本规划 → PRD 初稿

### A1 页面梳理（必须先做，页面清单 + 跳转图门禁）

#### 页面清单
| 序号 | 页面名称 | 页面类型 | 可见角色 | 入口来源 | 跳转去向 |
|------|---------|---------|---------|---------|---------|
| P01 | 添加账单 | 表单页 | 普通用户 | 底部 Tab「+」/列表页悬浮按钮 | 保存后返回账本首页 |
| P02 | 账单列表（账本首页） | 列表页 | 普通用户 | 底部 Tab「明细」/默认落地页 | 账单详情/编辑、分类统计 |
| P03 | 分类统计 | 仪表盘 | 普通用户 | 底部 Tab「统计」 | 按日期筛选、点分类查看贡献流水 |
| P04 | 个人中心 | 详情页 | 普通用户 | 底部 Tab「我的」 | 设置项、关于 |

#### 页面跳转图
```text
[底部 Tab 常驻] 明细(P02) · 统计(P03) · 我的(P04) · 悬浮 + 按钮(P01)
   P01 添加账单 ──保存/取消──→ 返回 P02，列表刷新
   P02 列表 ──点击条目──→ 编辑账单弹层/详情（MVP 内联编辑，不单独建页）
   P03 统计 ──核对明细──→ 复用/跳回 P02（携带筛选参数）
   P04 个人中心 ──设置──→ 设置面板（MVP 为弹层或内页）
```

#### 全局布局结构
- 底部 navigation tab 固定 4 项（明细/统计/我的/中间悬浮「+」），符合移动端 Ant Design Mobile `TabBar` 范式。
- 移动端顶部导航 + 列表 + 底部 tab 的经典三段式；无侧边栏（区别于桌面 Web）。

**门禁**：用户确认页面清单与跳转逻辑。

### A2 主要功能定义与分析（按页组织）

**P01 添加账单**
功能清单：
| 功能编号 | 功能名称 | 一句话描述 | 用户可感知的完成标准 |
|---------|---------|-----------|-------------------|
| F-01-01 | 快速添加账单 | 选分类、填金额、选支付方式与账本后一键保存 | 用户输入后点击保存，2 秒内回到列表且新账单出现在列表与统计 |
| F-01-02 | 收入/支出切换 | 支出默认，可切换到收入 | 一个开关在保存后记住上次选择 |

功能边界：包含（金额两位小数校验、备注/标签、日期默认今天、常用分类记忆）；不包含（MVP 不做子分类、不做多账本切换、不做扫描票据自动识别）。

**P02 账单列表**
功能清单：
| 功能编号 | 功能名称 | 一句话描述 | 用户可感知的完成标准 |
|---------|---------|-----------|-------------------|
| F-02-01 | 按月账单流水 | 默认当月、日期倒序、按"今天/昨天/X月X日"分组展示 | 用户切换月份后列表内容随之更新 |
| F-02-02 | 月收支汇总 | 列表顶部展示本月收入/支出/结余 | 滚动列表时汇总仍可见（触顶置顶） |
| F-02-03 | 编辑/删除账单 | 点条目编辑、滑动或长按删除（二次确认） | 删除后列表与统计同步减掉该条 |

功能边界：包含（金额/分类/备注可编辑、删除二次确认）；不包含（MVP 不做多条件组合筛选、不做标签筛选、不做无限滚动——先做加载更多/分页）。

**P03 分类统计**
功能清单：
| 功能编号 | 功能名称 | 一句话描述 | 用户可感知的完成标准 |
|---------|---------|-----------|-------------------|
| F-03-01 | 分类占比统计 | 时间范围内按分类聚合金额并展示占比（环形图 + 条形 TopN） | 用户选择月/年/自定义范围后图表与明细同步更新 |
| F-03-02 | 分类明细核对 | 点击某分类查看该分类下的流水 | 点击后跳转/复用列表页并携带分类筛选 |

功能边界：包含（支出/收入分开展示、默认当月）；不包含（MVP 不做预算对比、不做趋势折线图——V2 再引入图表库）。

**P04 个人中心**
功能清单：
| 功能编号 | 功能名称 | 一句话描述 | 用户可感知的完成标准 |
|---------|---------|-----------|-------------------|
| F-04-01 | 账户与设置 | 展示头像昵称、默认币种、预算提醒开关、关于 | 用户修改设置后本地持久化生效 |

功能边界：包含（默认币种 CNY、预算提醒开关）；不包含（MVP 不做多账本、不做多用户/登录、不做数据导出）。

**门禁**：用户确认所有页面的功能清单与边界。

### A3 版本规划 roadmap
- **Mission**：让手机用户用最小的操作成本完成日常记账并看清钱花在哪。
- **Persona**：22–35 岁、习惯手机操作、看重界面清爽的个人记账用户；记账频率每日 1–3 笔；在意"打开即记、统计直观"。
- **业务规则（Business Rules）**：金额必须 > 0 且千分位两位小数；分类为预置收支两大类 9 小类（MVP）；日期不得晚于今天保存时校验；删除需二次确认；当日修改历史账单需记录修改时间。

**V1 / MVP**
| 页面 | 包含功能 | 排除功能 | 理由 |
|------|---------|---------|------|
| P01 添加账单 | F-01-01、F-01-02 | 票据 OCR、子分类 | OCR 需外部 AI 依赖且增加复杂度，MVP 手动录入 |
| P02 账单列表 | F-02-01、F-02-02、F-02-03 | 多条件筛选、无限滚动 | MVP 数据量小，日期筛选 + 加载更多即可 |
| P03 分类统计 | F-03-01、F-03-02 | 趋势折线、预算对比 | 图表库引入增加依赖与适配成本，MVP 用轻量自绘/组件内置图形 |
| P04 个人中心 | F-04-01 | 多账本、登录/多用户、导出 | 账号体系/后端存储复杂度高，MVP 本地优先 |

**V2+**
| 功能 | 预计版本 | 延后理由 |
|------|---------|---------|
| 多账本与多用户/登录 | V2.0 | 需完整账号体系与后端鉴权，MVP 本地存储即可验证核心价值 |
| 趋势折线 + 预算设置 | V1.2 | 依赖图表库选型与更完整数据模型 |
| 数据导出（CSV/二维码） | V2.1 | 涉及文件生成与共享，非 MVP 核心路径 |

**门禁**：用户确认版本规划与功能取舍。

### A4 关键功能实现思路（穿插对齐，不单独设门禁）
- 适用范围判断：本应用核心水面下为普通 CRUD/页面交互，**无复杂业务链路与关键技术选型**（无 AI、无支付、无实时通信）→ 按 phase-A 规则"普通 CRUD / 页面交互不需要单独写 A4"，本阶段仅作简短说明即可，无需逐节点技术对齐。
- 唯一值得记录的实现口径：**MVP 本地存储 vs 后端**。默认：MVP 前端本地持久化（localStorage/IndexedDB 封装的记账 Repository 接口），同时按后端数据契约定义 DTO，V2 再切真实后端。该口径随 PRD 在阶段 A 总确认中一并确认。

### A5 数据契约确认（不设用户门禁，Agent 逐项自检完整性）
A5-1 业务数据契约 —— 数据契约**不随 V1/V2 变化，即使 MVP 只开发部分功能也完整设计**：
```markdown
#### 账单主体 Bill
- [ ] bill_id（string/UUID）、user_id（string）
- [ ] type（枚举：expense 支出 / income 收入）
- [ ] category_id（枚举：餐饮/交通/购物/居住/娱乐/医疗/教育/通信/其他，支出 9 类；MVP 收入 1 类"收入"）
- [ ] amount（decimal 12,2，必填，> 0，保留两位）
- [ ] payment_method（枚举：现金/支付宝/微信/银行卡/V2 扩展）
- [ ] note（string 可空，≤ 200 字符）
- [ ] label（数组，MVP 预留，可空）
- [ ] bill_date（date，默认今天）
- [ ] created_at / updated_at（datetime）
- [ ] is_deleted（bool，软删标记，MVP 简化可硬删但契约保留）

#### 分类体系
- [ ] 一级：支出 / 收入（2 类）
- [ ] 二级（MVP 支出 9 类）：餐饮、交通、购物、居住、娱乐、医疗、教育、通信、其他；收入归属"收入"

#### 账户与设置
- [ ] nickname、avatar_url、default_currency（枚举，默认 CNY）
- [ ] budget_reminder（bool 开关）/ monthly_budget（decimal，MVP 预留）

#### 账单状态流转
- [ ] 新增 → 正常；编辑 → maintained（保留最近编辑时间）；删除 → 二次确认后移除

#### 接口响应格式契约（A5-2 在此锁死）
- [ ] 成功：{"code": 200, "message": "success", "data": {...}}
- [ ] 错误：{"code": <错误码>, "message": "<描述>", "data": null}
- [ ] 分页：{"code": 200, "data": {"items": [...], "total": N, "page": 1, "page_size": 20}}
- [ ] HTTP：200 成功 / 400 参数错误 / 401 未认证 / 403 无权限 / 404 不存在 / 500 内部错误
```
（业务数据契约与响应格式契约**不需要用户确认**，Agent 梳理完自检后直接进入 A5-3）

A5-3 外部依赖与配置草稿（**必须经用户确认**，允许占位、不允许缺项）：
```markdown
#### 外部依赖与配置草稿（草稿 → 待用户确认）
| 依赖 | 用途 | 关键配置字段 | Key/账号来源 | 存放位置 | 缺失时策略 | 状态 |
|------|------|-------------|-------------|---------|-----------|------|
| LLM（供应商） | 无（本项目无 AI 功能） | - | - | - | 无 | 不适用 |
| 图标/字体资源 | 分类图标、iconfont | 图标库 CDN 或本地 assets | 公开资源/本地打包 | frontend/src/assets | 本地打包不依赖 CDN | 默认 |
| 用户数据存储 MVP | 本地持久化（无后端） | Storage 方案（localStorage/IndexedDB） | 无需账号 | 浏览器本地 | 无 | 默认 |
| （V2 预留）后端存储 | 云数据库/自建 | DB_CONN | 未定（V2） | backend/.env | MVP 本地存储，不阻塞 | 待确认（V2） |
| （V2 预留）图表库 | 趋势折线 | - | 开源 | frontend | MVP 不引入 | 默认 |
```
- 自检：链路中凡涉及"外部服务/密钥/账号/回调/付费"的点均已列出；无外部付费依赖、无第三方登录、无推送/支付 → 草稿完整。

### PRD.md 落盘（阶段 A 初稿，单一文件持续迭代）
**`docs/PRD.md`** 包含章节：1 背景与调研结论（阶段 R 选定方案摘要）；2 页面清单与跳转（A1）；3 按页组织的主要功能与边界（A2）；4 Mission / Persona / 版本规划（A3）；5 关键实现口径说明（A4，本应用为普通 CRUD）；6 数据契约确认清单（A5-1 + A5-2）；7 外部依赖与配置草稿（A5-3，含状态）。

### 阶段 A 总确认
```
请确认：页面清单、功能定义与边界、版本规划、外部依赖与配置草稿（逐项过）、PRD.md 是否一致无遗漏。
是否进入原型设计阶段？
```
**未经用户确认不得进入阶段 B。**

---

## 3. 阶段 B1：Design Spec

1. 从 `docs/PRD.md` 列出 MVP 界面清单（P01–P04）。
2. 读取 `.sdd/tmp/visual-research.md`（存在）：
   - 已选定"融合方向"：钱迹列表聚合 + 鲨鱼分类统计 + 统一清新浅色。
   - 提取可借鉴页面结构、组件形态、配色（白底 + 单一绿/青 accent）、字号（大号金额）、间距圆角（卡片 12–16px 圆角）、信息密度（克制型）。
   - 明确不采用：竞品品牌 Logo、真实文案、商业数据。
3. 收集 Design Context：无设计系统/品牌手册/已有 codebase → 使用默认设计基底 **Ant Design Mobile（移动端 H5）**。
4. 确定设计方向：阶段 R 已定方向，**直接沿用，不进"设计方向顾问 fallback"**。
5. 撰写 **`.sdd/tmp/ui-design-spec.md`**（B2 原型的唯一输入，能直接驱动绘制）：

```markdown
# Design Spec
> visual_research_status: ready
> 设计方向来源：阶段 R 选定方向（融合方案）

## 界面清单（来自 PRD 的 MVP 界面）
| 界面 | 类型 | 目标视口 | 一句话用途 |
|------|------|----------|-----------|
| P01 添加账单 | 表单页 | 移动端 H5 390×844 | 选分类填金额快速记一笔 |
| P02 账单列表 | 列表页 | 移动端 H5 390×844 | 按月流水、月汇总、编辑删除 |
| P03 分类统计 | 仪表盘 | 移动端 H5 390×844 | 分类占比环形图 + TopN 条形 |
| P04 个人中心 | 详情页 | 移动端 H5 390×844 | 头像昵称与设置入口 |

## 设计方向
- 选定方向：清新浅色 + 单一绿色 accent 的个人记账
- 视觉特征：配色 白底(#FFFFFF)+浅灰底(#F7F8FA)+主绿 accent(#00B578)+正文深灰(#333)；字型 系统字体（移动端 sans-serif）；布局 列表分组 + 底部 Tab；信息密度 克制型（一屏一主任务）

## 核心资产
- Logo：无（不引入品牌资产，不手画剪影）
- 已有产品图/UI 截图：无
- 已有 codebase 的 theme/tokens：无（用 Ant Design Mobile 默认组件 token 做基底）

## 视觉规格
- 色板：Primary #00B578 / Background #F7F8FA / Text #333 / Border #E5E6EB / Accent #FF8F1F（预警/负向、可标注）
- 字型：Display=系统默认大号（金额 28–34px 加粗）；Body=系统字体 14px
- 间距·圆角·阴影：页面 16px 边距；卡片圆角 12px；列表分隔线 1px #F0F0F0；弱阴影可选
- 信息密度：克制型

## 组件与页面结构
- 关键组件：底部 TabBar（明细/统计/我的 + 中间悬浮"+"）、金额输入区（大号金额 + 收支分段）、分类宫格选择、按月列表分组头、汇总条、环形图 + TopN 条形（统计页）、设置项列表（个人中心）
- 每页主要区域结构：
  - P01：顶部导航(取消/标题/保存) → 金额输入 → 分类宫格 → 日期/支付方式 → 备注
  - P02：TabBar + 月切换	头 + 汇总条 + 分组列表
  - P03：TabBar + 时间范围选择 + 环形图区 + TopN 列表
  - P04：Tab 头 + 用户卡片 + 设置项列表

## 签名细节
- 120% 质感锚点：统计页环形图（选中态动画）+ 金额大号数字排版——值得截图

## 设计禁区（反 AI slop）
- 不用无依据紫渐变、emoji 当分类图标（用线性/面性图标库）、不用圆角卡片+左 border accent 滥用、不手画人物
- 不照搬竞品品牌 / Logo / 真实文案 / 商业数据

## 气质关键词
- 清新 · 轻盈 · 亲近 · 明亮 · 克制
```
6. 发起确认：「Design Spec 已完成，请审阅。确认后进入阶段 B2 原型设计。」
**未经确认不得进入 B2。** 采用快速原则：存在 visual-research + PRD 明确，不新搜索、不新增门禁、新手势设计。

---

## 4. 阶段 B2：原型设计

- **必须先加载** `harness-core/skills/ui-design-standard/SKILL.md`（可读性/中文显示/组件状态/视口验证/竞品参考边界/原型-生产边界，B2 阶段底线）。
- **原型架构选择（先于工具选择）**：由 Design Spec 界面清单给出明确建议 → **移动端 H5 原型 → 390×844 页面**（或 iOS frame，若考虑 iOS/Android frame 可套 iOS frame 420×844 外框，页面本体以 390×844 为准），不再二次询问工具。
- **工具选择**：默认 **HTML 原型**（模式 A）。未使用 Pencil/Stitch（Pencil 仅当用户明确要可编辑画布时；Stitch 仅当用户明确指定）。
- **Junior Pass（快路径判断）**：
  - 必做场景核对：Design Spec 缺少竞品截图？否（visual_research=ready）；视觉质量要求高/多方案比较？否；原型界面 > 5 个？否（4 个）；单机流程复杂？否；Agent 不确定？否。
  - **可跳过场景成立** → 直接 Full Pass，输出中标注：`已走快速路径：Design Spec 明确，直接生成高保真原型。`
- **Full Pass / 模式 A（HTML）执行**：
  1. 读取 `.sdd/tmp/ui-design-spec.md`；读取 `.sdd/tmp/visual-research.md`（存在则必须参考）。
  2. 目标视口：**移动端 H5 390×844**；布局选 Mobile frame。
  3. 用 HTML/CSS/JS 绘制 4 页；flow demo 需含最小状态机（保存→列表刷新、删除二次确认、tab 切换）。
  4. 全部中文真实示例数据（模拟示例：餐饮 ¥32 支付 微信；列表至少 2 条/分组；统计 TopN 5 条）。
  5. 禁止把 Markdown 当原型；原型代码仅用于设计验证，不作为生产前端源码。
  6. 输出路径：
     ```
     docs/prototypes/
     ├── index.html        （4 页统一入口/跳转壳，或并排预览）
     ├── 01-add-bill.html
     ├── 02-bill-list.html
     ├── 03-statistics.html
     ├── 04-profile.html
     └── assets/
     ```
  7. 在 `docs/prototypes/README.md` 中写生产前端交接说明：页面清单、关键组件清单、交互状态、Mock 数据结构、需要真实 API 的位置、哪些视觉效果必须生产实现、哪些仅原型展示。
- **原型关闭条件（验证清单）**：能在浏览器打开 ✓；控制台无明显 JS 错误 ✓；无重叠/裁切/溢出 ✓；关键页面与 ui-design-spec 组件清单一致 ✓；视觉规则来自 Design Context/默认基底 ✓；竞品仅借鉴结构不照搬内容 ✓；**移动端/桌面目标视口截图正常（390×844）** ✓；flow demo 至少验证 3 个关键点击（保存、删除二次确认、tab 切换）✓；显示文字全中文无英文占位符 ✓。
- **完成收尾**：
  1. 原型输出到 `docs/prototypes/`。
  2. **立即删除 `.sdd/tmp/ui-design-spec.md`**（映射表：B2 原型完成后立即删除）。
  3. `.sdd/tmp/visual-research.md` **保留到阶段 C 完成后删除**（映射表权威口径：供 API 契约与 Plan 参考原型上下文；与阶段文件"B2 完成后留到 C 后删"一致）。
  4. 发起最终确认：「阶段 B2 原型已完成，请确认是否进入阶段 C。」
  **未经用户明确确认"进入阶段 C"，不得执行阶段 C。**

---

## 5. 阶段 C：PRD 定稿 + api-contracts + Plan

### C1：PRD.md 定稿
在 A 阶段初稿上补充以下章节（**不生成独立的 roadmap-final.md / architecture-blueprint.md，全部合并进 PRD.md**）：
- 路线图（版本规划终版）
- 技术架构蓝图：前端 React + TypeScript + Vite + **Ant Design Mobile**；MVP 本地持久化（Repository 接口，Storage 实现）；V2 计划接入后端（Python 3.11+ / FastAPI / pycore）并`VITE_USE_MOCK`切真实，部署为移动端 H5（可挂微信内网页/PWA）→ V2 App 壳。
- 原型说明：`docs/prototypes/` 4 页文件与 P01–P04 对应关系。
- 核心流程图（Mermaid）：记账主流程 flowchart + 一条异常分支（删除二次确认 / 金额非法提示）。
- 组件交互说明：影响模块（TabBar/列表/分类宫格）、拟新增模块（统计环形图）、调用关系。
- 技术选型与风险：图表库延迟引入、本地存储到后端的数据迁移成本（缓解：契约先行）、H5 浏览器兼容（缓解：现代电商标准 + AntD Mobile）。

### C2：接口契约 `docs/api-contracts.md`
列出每个接口完整请求/响应，遵守 A5-2 锁定的统一响应格式，**字段名/类型/嵌套明确，禁止 `...`/`TBD` 占位**。模拟接口清单：
```
GET  /api/v1/bills?month=2026-08&page=1&page_size=20    # 按月账单列表
POST /api/v1/bills                                       # 新增账单
PUT  /api/v1/bills/{bill_id}                             # 编辑账单
DELETE /api/v1/bills/{bill_id}                           # 删除（软删）
GET  /api/v1/categories                                  # 预置分类
GET  /api/v1/statistics/summary?range=2026-08            # 分类统计（环形图数据）
GET  /api/v1/user/profile                                # 个人中心
PUT  /api/v1/user/settings                               # 设置保存
```
每个接口含：请求方法/路径/请求体/成功响应/至少一种错误响应。
（MVP 前端走 Mock 时，Mock 数据格式与 api-contracts.md 一致即满足前端自动验收。）

### C3：开发计划 `docs/Plan.md`（开发阶段主进度文件）
- 一、功能清单总览：F01–F04（对应 P01–P04，优先级 MVP）。
- 二、数据契约摘要：指向 PRD「数据契约确认清单」；统一响应格式与接口契约为**唯一权威源**，不在 Plan 重复列出。
- 二点五、外部服务与测试权限清单（= A5-3 落定版，两者必须一致；MVP 无必须外部服务，前端基建类本地依赖，无真实 Key 需求；标注 V2 预留项状态可取"V2"-占位但 MVP 不阻塞）：
  | 服务 | 用途 | 配置项字段 | MVP 必需 | Tester 联调权限 | 缺失时策略 | 状态 |
  |------|------|-----------|----------|----------------|-----------|------|
  | 无（MVP 本地优先，无外部服务） | - | - | 否 | - | 本地 Mock/Storage | 确认 |
- 三、前端开发清单：技术选型表（框架 React / 语言 TS / 构建 Vite / 路由 react-router / 状态管理 Zustand / 请求库 Axios / **移动端 H5 组件库 Ant Design Mobile** / 工程化 ESLint+Prettier+type-check+build）；页面清单表（P01–P04 + Mock 数据来源 api-contracts.md）；前端自动验收标准；用户 UI 门禁说明；**`VITE_USE_MOCK=false` 切真实路径说明**（V2 联调和后续业务任务时）。
- 四、后端开发清单：MVP 标注"无后端任务（本地优先）"，V2 预留 B00 基础设施 + 账单 CRUD；验收规则引用 pycore 框架（基础设施必须基于 pycore，禁止自写 config/server/logger）+ 真实联调闭环规则。
- 六、开发顺序建议：阶段1 前端 MVP（Mock，用户先验收 UI/UX）→ 阶段2（V2 时）后端基础设施 → 阶段3 逐功能闭环 → 阶段4 E2E。MVP 当下仅执行阶段1（输出中明确：MVP 本地优先，V2 再走后端阶段）。

### 阶段 C 自检（逐项核对）
- [x] 无"待定/TBD/后续补充"占位符
- [x] 每个功能模块有明确优先级（MVP / V2+）
- [x] 核心流程图覆盖主流程 + 至少一条异常分支（删除/金额校验）
- [x] 技术选型确定，无"A 或 B 待定"（图表库 V2、后端 V2 属版本规划内的明确取舍，非待定）
- [x] PRD 与已确认原型一致
- [x] PRD 含路线图/架构蓝图/原型说明章节
- [x] api-contracts.md 已输出，覆盖所有接口
- [x] Plan.md 已输出，含功能清单/数据契约/前端后端清单
- [x] 外部服务与测试权限清单已输出（MVP 无外部服务，逐项有状态）
- [x] `docs/` 含 PRD/接口契约/Plan/原型；`.sdd/` 仅保留状态/任务/经验/日志/报告，无残留草稿
- 自检不通过 → 修复后重新输出，不得进入开发。

### 阶段 C 收尾（临时产物清理）
- **删除 `.sdd/tmp/visual-research.md`**（映射表：保留到阶段 C 完成后删除）。⚠️ 重要：B2 收尾时只删 `ui-design-spec.md`，**visual-research.md 必须留到本步才删**，因为 API 契约与 Plan 需要参考原型上下文。
- 可选：`docs/prototypes/pencil-prompt.md` 本流程未用 Pencil → 不产出，无需清理。
- 最终确认四件套：`docs/PRD.md` + `docs/api-contracts.md` + `docs/Plan.md` + `docs/prototypes/` 齐全且临时产物清空后，告知用户：
  「产品设计已完成。可以进入 Agent 开发流程。」

---

## 6. 五个必答问题的明确回答

### 1. 移动端 H5 项目的产品设计产出物遵循什么路径？
所有产出物**基于 `<active_project_path>/`（= `Projects_Repo/project-accounting-h5/`）**，不得写入 Harness 根目录同名目录。规则：
- 核心/交付文档 → `docs/`：`docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`docs/prototypes/`。
- 临时产物 → `.sdd/tmp/`：`.sdd/tmp/visual-research.md`、`.sdd/tmp/ui-design-spec.md`。
- 移动端 H5 与桌面 Web 的路径规则一致，差异在**内容口径**：原型架构选「移动端 H5 原型 → 390×844 页面」、组件库用 **Ant Design Mobile**；阶段判定/产物路径不因 mobile/web 而不同。
- 权威路径口径 = **SKILL.md「产出物映射表」**，各阶段文件若有出入以映射表为准。

### 2. 走完流程后，最终应该存在哪些文件（含完整路径）？
假设根为 `E:\SDD_V7_1_2\SDD_V7_1_2\`，`active_project_path = Projects_Repo/project-accounting-h5/`：

**A. 脚手架（脚本初始化、设计阶段全程常驻）**
```
Projects_Repo/project-accounting-h5/.sdd/project.json
Projects_Repo/project-accounting-h5/.sdd/status.json
Projects_Repo/project-accounting-h5/.sdd/experience.md
Projects_Repo/project-accounting-h5/.sdd/work-log.md
Projects_Repo/project-accounting-h5/.sdd/test-reports/     （空目录）
Projects_Repo/project-accounting-h5/.sdd/bug-logs/         （空目录）
Projects_Repo/project-accounting-h5/.sdd/bug_fix/          （空目录）
Projects_Repo/project-accounting-h5/README.md
Projects_Repo/project-accounting-h5/.gitignore
Projects_Repo/project-accounting-h5/pyproject.toml
Projects_Repo/project-accounting-h5/pycore/                （运行时脚手架）
project-registry.json                                       （根，记录新项目且 active_project_id 已切换）
```

**B. 核心交付产物（四件套，保留到开发）**
```
Projects_Repo/project-accounting-h5/docs/PRD.md
Projects_Repo/project-accounting-h5/docs/api-contracts.md
Projects_Repo/project-accounting-h5/docs/Plan.md
Projects_Repo/project-accounting-h5/docs/prototypes/
  ├── index.html
  ├── 01-add-bill.html
  ├── 02-bill-list.html
  ├── 03-statistics.html
  ├── 04-profile.html
  ├── assets/
  └── README.md          （生产前端交接说明）
```

**C. 设计阶段结束后应当已清理（不存在的文件）**
```
Projects_Repo/project-accounting-h5/.sdd/tmp/              （目录存在；其中临时产物已清空）
   .sdd/tmp/ui-design-spec.md        → B2 完成后删除
   .sdd/tmp/visual-research.md       → 阶段 C 完成后删除
docs/prototypes/pencil-prompt.md     → 本流程未用 Pencil，不产出
```

### 3. 哪些是临时产物？什么时机删除？
| 临时产物 | 删除时机 | 备注 |
|---------|---------|------|
| `.sdd/tmp/visual-research.md` | **阶段 C 完成后删除** | B1/B2 必须读取；保留到 C 是为供 API 契约与 Plan 参考原型上下文——B2 收尾时**不要**删它 |
| `.sdd/tmp/ui-design-spec.md` | **B2 原型完成后立即删除** | Design Spec 是 B2 唯一输入，出完原型即使命完成 |
| `docs/prototypes/pencil-prompt.md` | Pencil 回退模式 `.pen` 产出后清理（可选） | 本流程走 HTML 模式，不产出 |
- 权威口径：SKILL.md「产出物映射表」；**临时产物未按时机清理即视为流程未收尾**。
- `.sdd/tmp/` 目录本身由脚本初始化常驻，仅其中的临时文件需清理。

### 4. 完成后四件套是否齐全？
**齐全** ✅：
1. `docs/PRD.md`（A 初稿 → C 定稿，含路线图/架构蓝图/原型说明/流程图/技术选型与风险）
2. `docs/api-contracts.md`（阶段 C，覆盖 P01–P04 全部 8 个接口，遵守统一响应格式）
3. `docs/Plan.md`（阶段 C，功能清单/数据契约摘要/外部服务清单/前端清单/开发顺序）
4. `docs/prototypes/`（阶段 B2，HTML 高保真 4 页）
且 `.sdd/tmp/` 两件临时产物均已按时机删除 → 满足阶段判定表中"产品设计完成"行（PRD + api-contracts + Plan + prototypes 齐全，visual-research / ui-design-spec 已按映射表清理）。

### 5. 移动端视口相关说明（390×844）出现在哪个产物里？
「移动端 H5 → 390×844」的**权威出现位置**是 **`.sdd/tmp/ui-design-spec.md` 的「界面清单」表（`目标视口` 列）**，由 B1 产出；后续被 B2 消费：
- `phase-B2.md`「原型架构选择」表：**移动端 H5 原型 → iOS/Android frame 或 390×844 页面**；工具选择与批量绘制（桌面 1440×900 / **移动端 390×844**）再重申。
- B2 模式 C（Stitch）提示词要求：视口 1440×900 或 **390×844**。
- `phase-B2.md`「原型质量要求」：**移动端 H5 必须检查 390×844 视口**；验证清单含"移动端/桌面目标视口截图正常"。
- B2 产物 `docs/prototypes/*.html` 的 HTML 头（`viewport` meta + 390×844 布局壳）是其落地载体。
- `docs/PRD.md` C1「技术架构蓝图 / 原型说明」中描述移动端 H5 适配与 390×844 基准（沿用于生产实现）。

> 一句话：Design Spec（B1 产物）负责"声明"，B2 阶段文件负责"强制检查"，`docs/prototypes/*.html` 负责"落地"。

---

## 7. 关键决策与理由汇总

| # | 决策点 | 决策 | 理由 |
|---|--------|------|------|
| 1 | project_type | `mobile` | 用户明确"手机端 H5"；影响组件库（Ant Design Mobile）与视口（390×844）基准 |
| 2 | 技术栈 | React + TS + Vite + Ant Design Mobile | SDD 默认移动端 H5 栈，无需回退到技术选型确认（非原生 App/小程序/RN/Flutter） |
| 3 | MVP 存储 | 本地持久化（Storage Repository），V2 接后端 | 个人记账 MVP 验证核心价值无需账号体系；数据契约仍完整设计（不随 V1/V2 变化） |
| 4 | AI 功能 | 无 | 四页面均为普通 CRUD/查询，无 AI 材料；PRD 不写 AI 章节、外部依赖草稿 AI 行"无" |
| 5 | 竞品方向 | 融合：钱迹列表聚合 + 鲨鱼分类统计 + 清新浅色 | 契合"清新简单、手机浏览"目标；R1 至少 2 竞品且含 1 国内产品 ✓ |
| 6 | A4 展开 | 不单独写复杂链路 | 本应用无复杂业务链路/关键技术选型，普通 CRUD 不建 A4（phase-A 规则明确允许跳过） |
| 7 | 原型工具 | HTML 原型（模式 A） | 默认方式，速度最快、可点击/截图/验证；本应用 Pencil/Stitch 无用户要求 |
| 8 | Junior Pass | 跳过（可跳过场景成立） | Design Spec 明确（visual_research=ready、界面 ≤5、无复杂流程），标注快速路径后直走高保真 |
| 9 | 原型分拆 | 4 页多 HTML + index.html + assets | 符合 phase-B2 模式 A 多页面输出路径；README 承接生产交接说明 |
| 10 | 临时产物清理 | ui-design-spec（B2 后删）+ visual-research（C 后删） | 严格按映射表：后者需存活到 C 供 api-contracts / Plan 参考原型上下文 |

---

## 8. 门禁与阶段切换核对

- R0 需求对齐摘要确认 → 才进 R1 调研 ✋ 已模拟确认
- R 门口禁（参考方向 A/B/C/融合）→ 才进 A 　✋
- A1 页面清单/跳转 门禁 → A2；A2 功能与边界 门禁 → A3；A3 版本规划 门禁 → A4；A5-1/A5-2 数据契约**无**用户门禁（Agent 自检）→ A5-3 外部依赖草稿**需**用户确认 → 阶段 A 总确认 → B
- B1「Design Spec 完成请审阅」确认 → B2；B2 结束后「是否进入阶段 C」确认 → C
- C 完成后：`docs/` 四件套 + `.sdd/tmp` 清空 + PRD 自检通过 → 告知可进入开发
- 全程遵循「禁止跳步 + 阶段切换协议（Agent 先发门禁问题，用户前进意图仅当 Agent 已明确询问阶段切换后才解释为同意）」与「精简产出（过程结论在对话中完成，不单独建文件）」。

（本次为文字模拟：以上"创建/写入/删除"均未真实执行，仅描述流程应发生的动作。）