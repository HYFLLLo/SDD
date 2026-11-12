# SDD 产品设计流程 — 文字模拟执行输出

## 记账 H5 应用（移动端 mobile）

- eval：`eval-t2-mobile-h5`（without_skill 变体）
- 执行方式：**纯文字模拟**，不真实创建任何项目目录或文件；本文件是唯一的模拟产物落盘物。
- 依据规范：
  - `e:/SDD_V7_1_2/SDD_V7_1_2/.claude/skills/sdd-product-design-optimize-workspace/skill-snapshot/SKILL.md`
  - `phase-R.md` / `phase-A.md` / `phase-B1.md` / `phase-B2.md` / `phase-C.md`
  - `e:/SDD_V7_1_2/SDD_V7_1_2/harness-core/router.md`（入口契约）
  - `e:/SDD_V7_1_2/SDD_V7_1_2/harness-core/skills/ui-design-standard/SKILL.md`（B2 必须加载）

---

## 0. 项目身份与入口前置检查（入口行为）

**用户意图**：新建项目 → Router 顶层路由进入「新建项目」分支，转入 `sdd-product-design` Skill。

**字段确认**：

```text
project_id = project-accounting-h5
project_name = 记账 H5（清新记账）
project_type = mobile
repo_url = 未设置
active_project_id = project-accounting-h5
active_project_path = Projects_Repo/project-accounting-h5/
```

**前置检查（模拟结果）**：

1. **project-registry.json**：读取 `e:/SDD_V7_1_2/SDD_V7_1_2/project-registry.json`。假设当前 `projects[]` 中**不存在** `project-accounting-h5`，`active_project_id` 指向其他项目 → 允许创建新项目，并在脚本执行后切换 `active_project_id`。不覆盖任何已有记录。
2. **Projects_Repo 空项目判断**：`Projects_Repo/project-accounting-h5/` 不存在 → 符合「允许视为空项目」第一条 → 判定为全新空项目，不转入 `sdd-project-maintenance`。
3. **创建/绑定**：调用 `scripts/sdd_project.py`（运行时先确认 python 命令可用性，本项目模拟使用 `python`）：
   ```text
   python scripts/sdd_project.py new project-accounting-h5 --name "记账 H5（清新记账）" --type mobile
   ```
   脚本负责：创建 `Projects_Repo/project-accounting-h5/`、初始化 `.sdd/project.json`、`docs/`、Git 仓库、写入 `project-registry.json`、设置 `active_project_id`。
4. **可进入阶段判断**：五项必要条件全部满足（registry 有该 id、active=该 id、`.sdd/project.json` 存在、`docs/` 存在、无业务产物）→ 进入阶段判断。

**阶段判断**：`docs/PRD.md` 不存在 → **阶段 R**，读取 `phase-R.md`。

> 向用户绑定确认：
> ```text
> 已绑定新建项目：
> project_id = project-accounting-h5
> project_name = 记账 H5（清新记账）
> active_project_path = Projects_Repo/project-accounting-h5/
> repo_url = 未设置
> ```

---

## 1. 阶段 R：项目理解与调研

### R0 需求澄清与用户对齐

目标任务描述已给出四个核心页面，但按 phase-R 仍需先与用户对齐四个产品问题。模拟中用户补充/确认内容如下（假设已确认，摘要见下）：

1. **要解决什么问题**：个人日常记账——快速记录每一笔收支，让月度消费结构一目了然，帮助控制开销。
2. **目标用户**：个人用户，以 20-35 岁有记账习惯或想开始记账的年轻上班族/学生为主。
3. **使用场景**：手机浏览器/微信内打开；饭后、购物后「随手记」；睡前或月末复盘分类消费；碎片化、单手、通勤场景。
4. **大致功能**：添加账单、账单列表（按日期分组）、分类统计、个人中心（预算、分类、资料）。

**技术栈默认**：前端 React + TypeScript + Vite + **Ant Design Mobile**（移动端 H5 默认组件库）；后端 Python 3.11+ / FastAPI / PyCore；响应格式 `code / message / data`。

**AI 功能识别（内部类型识别）**：四个功能均为普通 CRUD + 数据聚合统计，**无 AI 参与** → 不补问 AI 材料，不写 AI 章节，无 LLM 类外部依赖。

**功能 Pipeline 拆解（一次整体呈现，不逐条卡门禁）**：

| 核心功能 | Pipeline 节点链 | 关键节点口径（已确认 / 默认） |
|---|---|---|
| 添加账单 | 选择收支类型 → 输入金额 → 选分类 →（备注/日期）→ 校验 → 保存 → 列表/统计刷新 | 类型：支出/收入切换（默认支出）；金额：数字大键盘、≤2 位小数（默认）；分类：宫格图标单选，最近使用置顶（默认）；备注：可选 ≤200 字（默认）；日期：默认今天可改；校验失败 Toast 提示，不阻断 |
| 账单列表 | 进入 → 按月分组加载 → 下拉分页 → 点击条目 → 详情/编辑/删除 | 按日期倒序、当日按时间倒序（默认）；月份左右切换；删除需二次确认（默认） |
| 分类统计 | 选时间范围 → 后端按月聚合 → 环形图 + 分类排行 → 点击分类下钻账单 | 只统计支出为主、可切收入（默认）；排行可点击跳列表筛选（默认） |
| 个人中心 | 展示本月经收/支/预算占比 → 预算设置 → 分类管理 → 资料 → 关于 | 预算按月设置、超出提醒（默认）；分类 MVIP 只允许启用/关闭内建分类，自定义分类 V2（默认） |

> 「功能 Pipeline 拆解」是 R0 内部梳理动作，不设逐条门禁；随「需求对齐摘要」一次确认。

**需求对齐摘要（模拟输出，用户已确认）**：

```text
需求对齐摘要
- 项目目标：让个人记账回归简单——3 秒记一笔，月度消费一目了然
- 目标用户：20-35 岁个人用户，有/想建立记账习惯
- 使用场景：手机端随手记账 + 月度复盘，碎片化、单手
- 核心问题：记账动作太重、统计看不懂（现状痛点）
- 核心功能：首页账单列表（含月度收支概览）、快速添加账单、分类统计、个人中心
- 功能 Pipeline 关键节点口径：见上表（全部带默认，可改）
- AI 功能判断：无
- AI 模型/API 来源：不适用
- AI 材料状态：不适用
- 智能边界：不适用
```

**写入规则**：对齐摘要先在对话完成，不单独建文件；用户确认后，内容在阶段 A 合并进 `PRD.md` 的背景/目标用户/核心功能章节。输入不冗长、无分支争议 → 不转入 alignment Skill，不产生 `docs/澄清文档/`。

### R1 竞品调研执行

至少 2 个竞品、至少 1 个国内产品，同时覆盖「产品结论」与「视觉证据」：

| 竞品 | URL（模拟） | 目标用户/场景 | 关键流程 | 核心交互 | 页面结构 | 视觉风格 | 组件形态 | 可借鉴点 | 不采用点 |
|---|---|---|---|---|---|---|---|---|---|
| 随手记（国内） | https://www.shouji.com/ | 全民记账，功能全 | 记一笔 → 分类 → 资产 | 快速记账大按钮、多账本 | Tab + 首页概览 | 偏商务、信息密度高 | 卡片、列表、FAB、饼图 | 记一笔的快捷路径设计、首页收支概览卡片 | 功能堆叠过重，视觉噪点多，不符「清新」 |
| 鲨鱼记账（国内） | https://www.shayubook.com/ | 年轻用户，颜值党 | 记账 → 账本 → 圆环图 | 卡通插画、清爽图标 | Tab + 环形图首页 | 清新浅色、圆润卡片 | 环形图、卡片、分类宫格 | 米白浅底色、大圆角、绿色主调、低信息密度 | 卡通插画占版面，商业模式推广入口多 |
| Money Manager（国外） | https://www.realbyteapps.com/ | 个人理财工具 | 交易 → 账户 → 报表 | 纯工具、无广告 | 抽屉 + 列表 | 极简、中性 | 列表、图表、抽屉 | 克制排版、数字呈现、金额千位分隔 | 冷色工具感，缺「日常温度」 |

**视觉证据说明**：模拟环境无法通过浏览器/Playwright 截图 → 按 phase-R 要求**向用户说明原因**，请用户提供截图；用户明确允许**基于文字调研继续**。因此视觉证据以「URL + 文字特征」形式落盘，截图列为待补充。

### R2 调研产出与视觉证据落盘

参考方案在对话中呈现，供用户 A/B/C 或融合选择（模拟用户选择**融合方案**）：

> 采用：**融合方案** = 鲨鱼记账的清新浅绿/圆润卡片（视觉基底） + 随手记的「记一笔」快速路径（结构） + Money Manager 的克制数字呈现/千位分隔（细节）。选择原因：与「界面清新简单、适合手机浏览」诉求一致；快速添加路径符合「随手记」核心场景。

确认后写入视觉证据文件：

```text
<active_project_path>/.sdd/tmp/visual-research.md
```

内容包含：竞品视觉证据表（上表）+ 用户选定方向（融合）+ 可复用视觉规则（页面结构 / 组件形态 / 色彩倾向 / 字体字号 / 间距圆角阴影 / 信息密度）+ 原型阶段必须参考（URL 清单）+ 禁止照搬（不复制竞品品牌/Logo/文案/数据，只借鉴结构与规律）。

**关键产品结论**将在阶段 A 写入 `docs/PRD.md` 背景章节；visual-research.md 保留到 B2 原型完成后再清理（最终清理时点见第 7 节）。

### 阶段 R 门禁

```text
请确认阶段 R 结果：
1. 竞品参考方向采用 A/B/C 还是融合方案？  → 用户确认：融合方案
2. 是否存在 AI 功能？                    → 无 AI，不适用
确认后进入阶段 A。
```

**未确认不得进入阶段 A。**（模拟中已确认。）❗️❗️❗️

---

## 2. 阶段 A：页面 → 功能 → 版本规划 → PRD

### A1 页面梳理（必须先做）

#### 页面清单

| 序号 | 页面名称 | 页面类型 | 可见角色 | 入口来源 | 跳转去向 |
|---|---|---|---|---|---|
| P01 | 首页·账单列表 | 列表页 | 全部用户 | 启动默认页 / Tab「首页」 | P02 添加账单、P05 账单详情、P03/P04 |
| P02 | 添加账单 | 表单页 | 全部用户 | P01 底部中间「+」按钮 / 空状态引导 | 保存后回 P01（列表刷新） |
| P03 | 分类统计 | 数据统计页 | 全部用户 | Tab「统计」 | 点排行项 → P01 按分类筛选 |
| P04 | 个人中心 | 个人中心 | 全部用户 | Tab「我的」 | 内部：预算设置 / 分类管理 / 资料 / 关于（弹层或子页） |
| P05 | 账单详情/编辑 | 详情页（表单） | 全部用户 | P01 点击账单条目 | 保存回 P01；删除（二次确认）回 P01 |

#### 页面跳转图

```text
启动 → P01 首页
TabBar：P01 首页 | P03 统计 | P04 我的（中间为独立「+」添加入口）
P01 --中间 + 按钮--> P02 添加账单
P01 --点击账单条目--> P05 账单详情（内可编辑/删除）
P01 --点击统计排行项--> P01（携带 category_id 筛选态）
```

**全局布局**：底部 TabBar（Ant Design Mobile `TabBar`），无侧边栏/顶部导航（移动端 H5 用底部导航 + 页面级标题栏）。

**门禁**：页面清单与跳转逻辑 → 用户确认后进入 A2。（模拟已确认。）❗️❗️❗️

### A2 主要功能定义与分析

按页面逐个分析（摘录关键部分，完整内容写入 PRD.md）。

#### P01 首页·账单列表

| 编号 | 功能名称 | 一句话描述 | 用户可感知完成标准 |
|---|---|---|---|
| F-01-01 | 月度收支概览卡 | 顶部展示本月收入/支出/结余 | 进入首页即看到本月收支与结余卡片 |
| F-01-02 | 账单列表（按月分组） | 按日期倒序展示账单，日期分组头 | 列表按日分组，每条显示时间/分类图标/金额 |
| F-01-03 | 月份切换 | 左右滑动/点月份切换月度数据 | 切换后列表与概览同步更新 |
| F-01-04 | 添加入口 | 底部中间「+」按钮 | 点击可进入 P02，按钮常驻显眼 |
| F-01-05 | 条目进入详情 | 点击条目进入 P05 | 点击后打开对应账单详情 |

功能边界：F-01-01 不含环比、趋势图；F-01-02 不含标签筛选与关键词搜索（V2）；列表为空显示 Empty 引导记第一笔。

#### P02 添加账单

| 编号 | 功能名称 | 一句话描述 | 用户可感知完成标准 |
|---|---|---|---|
| F-02-01 | 收支类型切换 | 支出/收入 Tab 切换 | 切换后分类宫格随之切换 |
| F-02-02 | 金额输入 | 数字大键盘，≤2 位小数，千位分隔 | 输入完整、回车后可下一步 |
| F-02-03 | 分类选择 | 宫格图标+名称单选，最近使用置顶 | 必选，未选时保存被拦截并提示 |
| F-02-04 | 备注与日期 | 备注可选；日期默认今天可改 | 可留空保存；日期可回选 |
| F-02-05 | 保存 | 校验后保存，Toast 成功，回首页刷新 | 保存成功立即回到首页且列表出现新账单 |

边界：不做周期账单、拆分账单、拍照/语音识别（V2）。

#### P03 分类统计

| 编号 | 功能名称 | 一句话描述 | 用户可感知完成标准 |
|---|---|---|---|
| F-03-01 | 支出/收入切换 + 月份 | 统计口径切换 | 切换后环形图与排行更新 |
| F-03-02 | 分类占比环形图 | 各分类支出占比 | 环形图展示分类占比（MVP 自绘 SVG） |
| F-03-03 | 分类排行列表 | 各分类金额/占比/笔数 | 列表按金额降序，点击下钻 P01 筛选 |
| F-03-04 | 预算进度 | 显示当月预算消耗进度 | 预算卡展示已用/总额（数据来自 P04 设置） |

边界：每日/月度趋势折线图、按账户维度统计 → V2。

#### P04 个人中心

| 编号 | 功能名称 | 一句话描述 | 用户可感知完成标准 |
|---|---|---|---|
| F-04-01 | 资料 | 昵称展示/编辑 | 可修改昵称并保存 |
| F-04-02 | 预算设置 | 月度总预算金额设置 | 设置后 P01/P03 预算进度联动态更新 |
| F-04-03 | 分类管理 | 内建分类启用/停用 | 停用后不可在添加页选择 |
| F-04-04 | 关于与数据说明 | 版本、隐私、本地数据说明 | 展示说明文案 |

边界：自定义分类、多账本、导出 CSV、云同步 → V2+。

#### P05 账单详情/编辑

| 编号 | 功能名称 | 一句话描述 | 用户可感知完成标准 |
|---|---|---|---|
| F-05-01 | 明细查看 | 展示金额/时间/分类/备注/类型 | 打开即见完整信息 |
| F-05-02 | 编辑 | 复用 P02 表单编辑并保存 | 保存后列表刷新 |
| F-05-03 | 删除 | 二次确认后删除 | 删除后回列表且数据消失 |

**门禁**：所有页面功能清单与边界无歧义 → 用户确认后进入 A3。（模拟已确认。）❗️❗️❗️

### A3 版本规划（Roadmap）

- **Mission**：让个人记账回归简单——3 秒记一笔，月度消费一目了然。
- **Persona**：小雅，25 岁女性上班族，每月「月光」想控制开销；通勤与餐后碎片时间随手记账，月末看统计找「钱去哪了」。

#### V1 / MVP

| 页面 | 包含功能 | 排除功能 | 理由 |
|---|---|---|---|
| P01 | F-01-01~05 | 搜索、标签筛选 | 搜索非核心闭环，V2；月度回顾是核心 |
| P02 | F-02-01~05 | 周期账单、拍照/语音 | 核心是「3 秒记一笔」，美化交互领先于识别能力 |
| P03 | F-03-01~03（环形图+排行） | 趋势折线图（F-03-04 预算卡保留） | 环形图用自绘 SVG 足够，图表库引入延迟；趋势图 V2 |
| P04 | F-04-01~04 | 自定义分类、多账本、导出 | 导出/多账本非 MVP 必需，依赖增多 |
| P05 | F-05-01~03 | — | MVP 必须 |

**MVP 整体边界**：单账本；**无账号体系**（按设备 clientId 隔离数据，见 A4 决策 3）；无云同步；无外部服务依赖。

#### V2+

| 功能 | 预计版本 | 延后理由 |
|---|---|---|
| 月度/每日趋势折线图 | V1.1 | 需引入图表库（echarts），MVP 环形图可承接统计需求 |
| 搜索与标签筛选 | V1.1 | 提升老用户检索效率，非新用户核心路径 |
| 自定义分类 | V1.2 | 需支持用户自建 icon/排序，数据契约扩展 |
| 多账本 | V1.2 | 依赖模型扩展与迁移复杂 |
| 账号体系 + 云同步/多端 | V2 | 需短信/三方登录等外部依赖，阻塞 MVP，见 A4 决策 |
| 语音/拍照记账（AI 类） | V2 | 涉及 AI 能力与外部 OCR/ASR，MVP 明确不做 AI |
| 数据导出（CSV） | V2 | 非高频，MVP 不占研发预算 |

**规则落实**：每项取舍都给出实现复杂度/依赖/风险依据，非罗列。

**门禁**：版本规划与取舍无误 → 用户确认后进入 A4。（模拟已确认。）❗️❗️❗️

### A4 关键功能实现思路（穿插式对齐，无独立门禁）

本项目是 CRUD + 统计，「普通 CRUD/页面交互不单独写 A4」，仅对 3 条有产品/技术选型意义的链路做对齐：

#### 关键链路 1：分类统计聚合（P03）

- 触发场景：用户进入统计页选择月份后
- 实现思路：后端按 `month + type` 对 bills 做 `GROUP BY category_id` 聚合，返回每分类 `sum(amount_cents)` / `count` / `percent`；前端只用「自绘 SVG 环形图 + 排行列表」渲染
- 关键技术选型：MVP **不引入 echarts/chart.js**，用轻量自绘 SVG（依赖少、体积小、符合移动端）；V2 引入 echarts 画趋势图
- 待确认问题：图表方案 MVP 用自绘环形图，V2 引入 echarts —— 已按默认确认，可改

#### 关键链路 2：金额快速录入（P02）

- 触发场景：用户点击金额输入框
- 实现思路：Ant Design Mobile `NumberKeyboard` 自定义数字键盘；金额以**分（int）在数据库存储**，前端展示转元，杜绝浮点误差；附加 `0.5 / 1 / 2 / 5 / 10 / 20 / 50 / 100` 常用金额快捷块
- 待确认问题：快捷键金额档位默认值，用户可改

#### 关键链路 3：数据隔离与「无账号」决策（全局）

- 触发场景：首个 MVP 版本所有请求
- 实现思路：MVP **不做登录/账号体系**——前端首次启动生成持久化 `clientId`（UUID，保存 localStorage），所有请求头携带 `X-Client-Id`，后端按 clientId 隔离数据（逻辑上「一人一库」）
- 理由：避免短信登录/三方登录/账号找回等外部依赖与合规成本，让 MVP 无任何外部密钥即可交付；V2 做账号 + 云同步时以 clientId 作为匿名引导绑定迁移
- 待确认问题：接受「MVP 无账号、设备隔离，V2 再做云同步」默认方案 → 用户确认

### A5 数据契约确认（Agent 自检，不设用户门禁，但必须完整）

> 全量数据契约不随 V1/V2 变化，即使 MVP 只开发部分功能，契约也要完整设计。

#### A5-1 业务数据契约（摘录确认清单，完整写入 PRD.md）

```text
#### 账单 Bill
- [ ] id（int，自增）、type（enum：expense 支出 / income 收入）
- [ ] category_id（int，外键→Category，不可空）
- [ ] amount_cents（int，金额以「分」存储，>0）
- [ ] remark（string，可空，≤200 字符）
- [ ] occurred_at（datetime，精度到分钟，记账发生时间）
- [ ] created_at / updated_at（datetime，自动维护）

#### 分类 Category
- [ ] id、name、type（expense/income）、icon（string）、sort（int）、enabled（bool 默认 true）
- [ ] 内置支出分类（8）：餐饮/交通/购物/居住/娱乐/医疗/教育/其他
- [ ] 内置收入分类（5）：工资/奖金/理财/兼职/其他

#### 月度预算 Budget
- [ ] id、month（string "YYYY-MM"）、amount_cents（int）、与 clientId 对应（设备唯一）

#### 用户资料 Profile
- [ ] client_id（string，主键，设备隔离语义）、nickname（string，默认「记一笔」）
- [ ] avatar（string，可空，MVP 可不传）

#### 设备标识与隔离
- [ ] 前端生成 clientId（UUID），请求头 X-Client-Id 传递；后端所有数据按 clientId 隔离
```

#### A5-2 接口响应格式契约（必须在此阶段锁死）

```text
#### 统一响应格式
- [ ] 成功：{"code": 200, "message": "success", "data": { ... }}
- [ ] 错误：{"code": <错误码>, "message": "<错误描述>", "data": null}
- [ ] 分页：{"code": 200, "data": {"items": [...], "total": 100, "page": 1, "page_size": 20}}

#### HTTP 状态码约定
- [ ] 200 成功 / 400 参数错误 / 404 资源不存在 / 500 服务器内部错误
- [ ] 401 未认证、403 无权限：MVP 无账号体系暂不产生，仍作为契约预留在案
```

**规则**：业务数据契约 + 接口响应格式契约不需要与用户确定，Agent 梳理后**自检一遍**即可（本模拟已自检通过）。

#### A5-3 外部依赖与配置草稿（需用户确认）

> 依据 A2 功能 + A4 链路逐个对照，任何外部服务/密钥/账号/回调/付费资源都必须落一行；**没有就显式写「无」**（完备性要求）。

| 依赖 | 用途 | 关键配置字段 | Key/账号来源 | 存放位置 | 缺失时策略 | 状态 |
|---|---|---|---|---|---|---|
| LLM（AI 模型） | 无 AI 功能 | — | — | — | — | 无 |
| Embedding / Rerank | 无 RAG | — | — | — | — | 无 |
| 第三方 API / 数据源 | 无 | — | — | — | — | 无 |
| 支付 / 结算 | 无 | — | — | — | — | 无 |
| 短信 / 邮件 / 推送 | 无（无账密/验证码/推送） | — | — | — | — | 无 |
| 对象存储 / 文件服务 | 无（MVP 不传图片，头像可省略） | — | — | — | — | 无 |
| 第三方登录 / SSO / OAuth | 无（MVP 无账号体系，设备隔离） | — | — | — | — | 无 |
| 地图 / 定位 / 实名 / 风控 | 无 | — | — | — | — | 无 |

**结论**：本项目外部依赖草稿全部类别为「无」；无任何关联过滤项，天然满足 Router「开发门禁」第 7 条（无需 .env 外部密钥，仅 PyCore 运行时默认配置）。该草稿需用户确认战役（模拟已确认）。

**自检**：A2/A4 中未用到任何外部服务 → 草稿无遗漏。

### 落盘与 PRD.md 结构（阶段 A 初稿）

输出到：

```text
<active_project_path>/docs/PRD.md
```

包含（此时为初稿状态，阶段 C 补充定稿章节）：
1. 背景与调研结论（R 阶段融合方向摘要 + 竞品结论）
2. 页面清单与跳转逻辑（A1）
3. 主要功能定义与分析（A2，按页面组织，含完成标准与边界）
4. Mission / Persona / 版本规划（A3 MVP/V2+ 切分及理由）
5. 复杂功能业务链路 + 关键实现思路（A4，三条链路）
6. 数据契约确认清单（A5-1 业务数据 + A5-2 接口响应格式，**完整不缩水**）
7. 外部依赖与配置草稿（A5-3，全部「无」，含用户确认记录）
8. 无 AI 功能 → 不写 AI 章节（显式标注「本项目无 AI 功能」）

### 阶段 A 总确认

```text
请求确认：页面清单、功能定义与边界、版本规划、外部依赖与配置草稿（全部为「无」）、PRD.md 一致且无重大遗漏。
是否进入原型设计阶段？
```

（模拟已确认。）❗️❗️❗️

> 阶段判断推进条件（进入 B1 前自检）：`docs/PRD.md` 存在 + **数据契约章节完整**（确认清单 + 接口响应格式契约都在）→ 进入阶段 B1。满足。

---

## 3. 阶段 B1：Design Spec

**快速原则**：visual-research.md 存在 → 直接提炼，不重复搜索；只写影响原型与前端实现的轻量内容。

1. **MVP 界面清单**：来自 PRD，5 个界面（P01~P05）。
2. **读取视觉调研上下文**：读取 `.sdd/tmp/visual-research.md`，提取：融合方向（清新浅绿+圆润卡片）、竞品 URL 证据、可借鉴的页面结构/组件形态/配色/字体/间距/信息密度、不采用点。
3. **Design Context 收集**：无品牌规范/Logo/设计系统、无已有 codebase、无用户截图（模拟允许基于文字调研）→ **默认设计基底 = Ant Design Mobile 风格**；截图缺失以竞品 URL 替代。
4. **确定设计方向**：阶段 R 已确认融合方向 → **沿用，不再另起炉灶**，不触发「设计方向顾问 fallback」。
5. **撰写 Design Spec** → 输出：

```text
<active_project_path>/.sdd/tmp/ui-design-spec.md
```

   关键内容（完整结构写入该临时文件）：

```text
# Design Spec
> visual_research_status: ready（有 URL 依据；截图缺：模拟环境无法截图，用户已允许文字调研，截图可后续补）
> 设计方向来源：阶段 R 选定融合方向

## 界面清单（来自 PRD 的 MVP 界面）
| 界面 | 类型 | 目标视口 | 一句话用途 |
|------|------|----------|-----------|
| 首页·账单列表 | 列表页 | 移动端 390×844 | 月度收支概览 + 按月分组账单 |
| 添加账单 | 表单页 | 移动端 390×844 | 3 秒记一笔（类型/金额/分类/备注） |
| 分类统计 | 数据统计页 | 移动端 390×844 | 分类占比环形图 + 排行 |
| 个人中心 | 个人中心 | 移动端 390×844 | 预算/分类管理/资料/关于 |
| 账单详情/编辑 | 详情页(表单) | 移动端 390×844 | 查看/编辑/删除账单 |

## 设计方向
- 选定方向：清爽浅绿 · 开阔留白 · 圆润卡片（融合）
- 视觉特征：配色倾向 = 薄荷绿主色 + 米白底；字型 = 系统 sans-serif（PingFang 优先）；布局 = 单列、卡片化；信息密度 = 低，克制
- 参考来源：visual-research.md（鲨鱼记账 浅底圆角 / 随手记 记一笔路径 / Money Manager 数字呈现）

## 核心资产
- Logo：无
- 已有产品图/UI 截图：无（竞品以 URL 替代，截图待用户补）
- 已有 codebase theme/tokens：无 → 用 Ant Design Mobile 默认基底

## 视觉规格
- 色板：Primary #00B96B（薄荷绿）/ Background #F7F8FA / Text #1F2329 / Border #EDF1F4 / Accent #E8F8F0（浅绿卡底）；金额 支出 #E64A4A、收入 #00B96B（同主色系）
- 字型：系统栈 -apple-system, PingFang SC, sans-serif；金额 tabular-nums
- 间距：卡片内边距 16、区块间距 12；圆角：卡片 16px、按钮/输入 10px；阴影：极轻（0 2 8px rgba(0,0,0,.04)）
- 信息密度：克制型（列表项高约 56-64px）

## 组件与页面结构
- 关键组件：TabBar（中间凸起「+」）、NumberKeyboard 数字键盘、Grid 分类宫格、SVG 环形图、List、Popup/ActionSheet、Toast、Empty、Skeleton
- 每页主要区域：P01 顶部收支卡 → 月份选择 → 日分组账单列表；P02 类型切换 → 金额输入卡 → 分类宫格 → 备注/日期 → 保存按钮；P03 类型/月份切换 → 环形图卡 → 排行列表；P04 资料卡 → 功能列表（预算/分类/关于）；P05 账单主信息卡 → 编辑按钮 → 删除

## 签名细节
- 1 处做到 120% 的质感锚点：P01 顶部「本月结余」环形卡（浅绿卡底 + 主色圆环 + 数字）

## 设计禁区（反 AI slop）
- 不用无依据紫渐变、emoji 当图标、圆角卡片+左 border accent、SVG 手画人物、系统字体当 display
- 不照搬竞品品牌 / Logo / 真实文案 / 商业数据

## 气质关键词
- 清新、轻快、克制、圆润、通透
```

6. 发起确认：**「Design Spec 已完成，请审阅。确认后进入阶段 B2 原型设计。」**

**未经用户确认不得进入 B2。**（模拟已确认。）❗️❗️❗️

---

## 4. 阶段 B2：原型设计

### 设计规范底座（必须加载）

读取 `harness-core/skills/ui-design-standard/SKILL.md`（已读取），遵守：可读性、全中文显示、组件状态（默认/Hover/Pressed/Disabled/Loading/Empty）、视口验证、竞品参考边界、原型与生产代码边界。

### 原型架构选择（先于工具选择）

Design Spec 明确为移动端 H5、单机流程演示、5 个界面 → 原型形态 = **移动端 H5 原型（390×844 页面）**，不再二次询问工具。

### 工具选择

默认使用 **HTML 原型**（速度最快、可点击、可截图、可验证）。用户无特殊要求 → 不启用 Pencil / Stitch。

### Junior Pass（必做场景命中）

**命中理由**：Design Spec 中**缺少竞品截图**（只有 URL，截图缺失）。→ 必须先做 Junior Pass，再进 Full Pass。

Junior Pass 内容（写在与用户对话 + 原型 HTML 注释中）：原型形态（mobile H5 flow demo）、页面清单（5 页）、每页主要区域、关键用户路径（记一笔闭环：首页 →+ → 添加 → 保存 → 列表刷新；点击条目 → 详情 → 编辑 → 保存；统计 Tab 查看）、assumptions、placeholders（灰块+文字标签）、未确认问题、参考竞品 URL 的使用位置。

确认文案：

```text
我已完成 Junior Pass：页面结构、主要路径、占位内容和设计假设已列出。
请确认方向是否正确。确认后我再进入 Full Pass 高保真原型绘制。
```

**未经用户确认 Junior Pass，不得进入 Full Pass。**（模拟已确认方向正确。）❗️❗️❗️

### Full Pass · 模式 A：HTML 原型

执行步骤：
1. 读取 `.sdd/tmp/ui-design-spec.md`（唯一输入，不凭记忆画）
2. 读取 `.sdd/tmp/visual-research.md`（存在则参考其 URL 证据）
3. 布局：iOS/移动端 frame，容器宽度 390，视口 `width=device-width, initial-scale=1`；页面间跳转用最小 JS 状态机
4. HTML/CSS/JS 绘制 5 个页面，**全中文真实示例内容**（禁止 Markdown 当原型、禁止英文占位符）
5. 可点击 flow demo，验证 ≥3 个关键点击（+ 添加 → 保存 → 回列表刷新；账单条目 → 详情 → 编辑 → 保存；Tab 统计查看）
6. 原型 HTML **仅作设计验证，不作为生产前端源码**

**输出（多页面分拆）**：

```text
docs/prototypes/
├── index.html          # P01 首页·账单列表
├── 01-add-bill.html    # P02 添加账单
├── 02-stats.html       # P03 分类统计
├── 03-profile.html     # P04 个人中心
├── 04-detail.html      # P05 账单详情/编辑
├── assets/
│   └── style.css       # 原型共享样式（含 390 宽容器）
└── README.md           # 生产前端交接说明（必写）
```

`docs/prototypes/README.md` 必须包含：页面清单、关键组件清单、交互状态、Mock 数据结构、需要真实 API 的位置、哪些视觉效果必须生产实现 / 哪些只是原型展示效果、**390×844 视口验证结果**。

### 原型质量要求与验证清单（全部通过）

- [x] 原型能在浏览器打开
- [x] 控制台无明显 JS 错误
- [x] 页面无重叠、裁切、明显溢出
- [x] 关键页面与 ui-design-spec.md 组件清单一致
- [x] 关键视觉规则来自已确认 Design Context（Ant Design Mobile 默认基底 + Design Spec 色板）
- [x] 竞品只借鉴结构/交互/视觉规律，不照搬品牌和内容
- [x] **移动端 390×844 目标视口截图/检查正常**
- [x] flow demo 关键按钮可点击，路径走通（≥3 个关键点击）
- [x] 所有显示文字为中文，无英文占位符
- [x] 列表/卡片示例数据 ≥2 条
- 交互状态覆盖：默认/Disabled/Loading（保存中）/Empty（无账单）/Error（校验失败 Toast）

### 完成收尾

1. 原型输出到 `docs/prototypes/`（已完成）
2. **删除临时文件 `.sdd/tmp/ui-design-spec.md`**（阶段 B2 收尾动作）
3. `.sdd/tmp/visual-research.md`：按 R2 应在 B2 完成后清理，但按 phase-B2 允许**保留到阶段 C 完成后再删除**，确保 api-contracts/Plan 可参考原型上下文 → 本项目选择保留至 C 完成，最终清理
4. 发起最终确认：**「阶段 B2 原型已完成，请确认是否进入阶段 C。」**

**未经用户明确确认「进入阶段 C」，不得执行阶段 C。**（模拟已确认。）❗️❗️❗️

---

## 5. 阶段 C：最终 PRD 定稿 + 接口契约 + 开发计划

### C1：定稿 PRD.md

在阶段 A 初稿基础上补充以下章节（**全部合并在 PRD.md，不生成 roadmap-final.md / architecture-blueprint.md 等独立文件**）：

1. **路线图（版本规划终版）**：单账本 MVP（P01~P05 功能闭环）；V1.1 趋势图/搜索；V1.2 自定义分类/多账本雏形；V2 账号+云同步。
2. **技术架构蓝图**：
   - 前端：React 18 + TypeScript + Vite + **Ant Design Mobile** + react-router（H5 路由/鉴权守卫只是为了底部 Tab 结构，无登录态）+ Zustand（全局 UI/筛选状态）+ Axios（统一实例、拦截器、`clientId` 注入）
   - 后端：Python 3.11 + FastAPI + PyCore（`ConfigManager` / `APIServer` / DB 模板，禁止自造基础设施）+ SQLite（MVP）→ MySQL（V2 云同步）
   - 分层：controller → service → repository；统一 `code/message/data` 响应
   - 部署：MVP 单机（FastAPI 服务 + 静态 H5）；V2 上云
3. **原型说明**：`docs/prototypes/` 5 文件与 P01~P05 一一对应（含 390×844 视口验证说明）。
4. **核心流程图（Mermaid）**：
   - 主流程：记一笔 `sequenceDiagram 用户→前端: 点+ → 前端→后端: POST /api/bills → 后端→DB: size + id → 前端刷新列表`；
   - 异常分支：金额 ≤ 0 / 未选分类 → 前端校验 Toast；后端校验 400；删除二次确认；统计接口无数据 → Empty 态。
5. **组件交互说明**：新增模块（bills / categories / budget / profile / stats）、调用关系、前端组件与后端接口映射。
6. **技术选型与风险**：图表库 MVP 不引入（自绘 SVG，风险低）；无账号设备隔离 → V2 云同步需起迁移方案（clientId 绑定）；金额以分存储规避浮点；SQLite 并发限制 → V2 MySQL。

补入说明：`docs/data-system.json` 未生成 —— 本项目数据模型仅 5 个实体、契约已完整落入 PRD「数据契约确认清单」与 api-contracts.md，按「精简产出」原则不需要独立的 `data-system.json`（该文件为「如需要」项）。

### C2：输出接口契约文件（必出）

```text
<active_project_path>/docs/api-contracts.md
```

> 前端 Mock 和后端实现的唯一对齐依据，任何变更必须同步更新。

通用约定：统一响应 `code/message/data`（锁自 A5-2）；请求头统一携带 `X-Client-Id`；MVP 无鉴权。

接口清单（每个接口含：方法/路径、请求体、成功响应、至少一种错误响应；**禁止 `...` / TBD 占位**）：

| 接口 | 说明 |
|---|---|
| `POST /api/bills` | 新增账单 |
| `GET /api/bills?month=YYYY-MM&type=&category_id=&page=&page_size=` | 账单列表（分页） |
| `GET /api/bills/{id}` | 账单详情 |
| `PUT /api/bills/{id}` | 编辑账单 |
| `DELETE /api/bills/{id}` | 删除账单 |
| `GET /api/categories?type=expense\|income` | 分类列表 |
| `GET /api/stats/summary?month=YYYY-MM&type=` | 月度聚合：总收支/结余/笔数 + 分类 items（amount_cents/count/percent） |
| `GET /api/budget?month=YYYY-MM` / `PUT /api/budget` | 预算查询/设置 |
| `GET /api/profile` / `PUT /api/profile` | 资料查询/更新 |

示例（完整写入文档）：

```jsonc
// POST /api/bills
// 请求体
{"type": "expense", "category_id": 3, "amount_cents": 2850, "remark": "午餐", "occurred_at": "2026-08-27T12:30:00"}
// 响应 200
{"code": 200, "message": "success", "data": {"id": 1024, "type": "expense", "category_id": 3, "amount_cents": 2850, "remark": "午餐", "occurred_at": "2026-08-27T12:30:00", "created_at": "2026-08-27T13:01:00"}}
// 响应 400
{"code": 400, "message": "amount_cents 必须大于 0", "data": null}
```

### C3：输出开发计划文件（必出）

```text
<active_project_path>/docs/Plan.md
```

- **一、功能清单总览**：F-01-01~F-05-03 汇总表（一句话描述 / 对应页面 / 优先级 MVP / 状态待开发）
- **二、数据契约摘要**：指向 PRD 契约清单；统一响应格式与接口见 api-contracts.md（唯一权威源，不重复）
- **二点五、外部服务与测试权限清单**：本项目 A5-3 全部类别为「无」→ 显式声明「本项目无外部服务依赖，无 Key/账号/Base URL/付费资源项，本清单不适用，视为已锁定」；无真实密钥进入任何文档
- **三、前端开发清单**：
  - 技术选型表（React / TS / Vite / react-router / Zustand / Axios / **Ant Design Mobile** / ESLint+Prettier+type-check+build / TanStack Query 可选）
  - 页面清单 P01~P05（Mock 数据来源：api-contracts.md）
  - 前端自动验收标准（UI 与原型一致 / Mock 可交互 / Mock 格式与契约完全一致 / Agent・Tester 自动验收通过）；前端 Mock 后触发用户门禁，用户确认后进入后端基础设施；后端任务完成后各 page/service 切 `VITE_USE_MOCK=false` 真实联调
- **四、后端开发清单**（基于 pycore，禁止重写 infra）：B00 基础设施（`GET /health`）→ B01 bills CRUD → B02 stats 聚合 → B03 budget → B04 profile → B05 categories 种子数据；附后端任务验收规则（qfruff/mypy、单元测试、health 200、每功能完整闭环真实联调、外部服务缺失只能 Mock/降级验收）
- **五、功能详情**：开发阶段由 Developer/Tester 逐个展开
- **六、开发顺序建议**：阶段 1 前端 MVP(Mock)→用户验收门禁 → 阶段 2 后端基础设施(自动) → 阶段 3 逐功能闭环(每功能用户门禁) → 阶段 4 E2E 回归

**Plan.md 维护规则**：设计阶段结束由 Agent 生成初始版本；禁止跳过 Plan.md；禁止另建进度文件。

### PRD 自检（逐项核对，全部通过）

- [x] 无「待定/TBD/后续补充」占位符
- [x] 每个功能模块有明确优先级（MVP / V2+）
- [x] 核心流程图覆盖主流程 + 异常分支（校验失败 / 删除确认 / 空数据）
- [x] 技术选型已确定，无「A 或 B 待定」
- [x] PRD 内容与已确认原型一致（5 页对应，390×844 视口）
- [x] PRD 包含路线图、架构蓝图、原型说明章节
- [x] api-contracts.md 已输出，覆盖全部接口（9 个）
- [x] Plan.md 已输出，含功能清单、契约摘要、前端/后端清单、外部服务清单
- [x] 外部服务与测试权限清单已输出（本项目显式「无」）
- [x] `docs/` 包含 PRD / 接口契约 / Plan / 原型；`.sdd/` 无残留草稿，仅状态（`project.json` → 待补 tasks.json 属开发阶段）

**自检不通过 → 修复后重新输出，不得进入开发。**（本项目通过。）

### 阶段 C 完成后

```text
产品设计已完成。可以在当前对话中说「开始开发」，Router 将按开发门禁进入多 Agent 开发流程。
```

---

## 6. 门禁与确认点记录

| 阶段 | 确认点 | 结果 |
|---|---|---|
| 入口 | 绑定新项目字段确认 | 已确认 |
| R0 | 需求对齐摘要确认 | 已确认 |
| R 门禁 | 竞品方向（融合）/ 无 AI | 已确认 |
| A1 | 页面清单与跳转逻辑 | 已确认 |
| A2 | 全部页面功能清单与边界 | 已确认 |
| A3 | 版本规划与取舍 | 已确认 |
| A5 | A5-3 外部依赖草稿（全部「无」）逐项过 | 已确认 |
| A 总确认 | PRD 初稿一致、进入 B？ | 已确认 |
| B1 | Design Spec 审阅 | 已确认 |
| B2-Junior | Junior Pass 方向 | 已确认 |
| B2 收尾 | 原型完成、进入 C？ | 已确认 |
| C | PRD 定稿 + 契约 + Plan + 自检 | 用户确认 → 完成 |

> 全局规则落实：每个子阶段结束都发起明确的阶段切换门禁；「继续/可以」只在 Agent 明确询问「是否进入阶段 X？」后才视为前进；数据契约（A5-1/A5-2）不设用户门禁但 Agent 自检；精简产出——调研/草稿结论在对话完成并入核心文件，不为过程产物单独建文件。

---

## 7. 产物清单与路径总表

根目录约定：`active_project_path`（相对）＝ `Projects_Repo/project-accounting-h5/`；Harness 根（绝对）＝ `e:/SDD_V7_1_2/SDD_V7_1_2/`。

以下共享 `e:/SDD_V7_1_2/SDD_V7_1_2/` 前缀。

### 7.1 最终应存在的文件（产品设计阶段完成后）

| # | 完整路径 | 来源阶段 | 说明 |
|---|---|---|---|
| 1 | `project-registry.json`（Harness 根） | 入口 | 由 `sdd_project.py` 写入 `project-accounting-h5` 记录并置为 active |
| 2 | `.sdd/project.json` | 入口 / script | 项目身份、project_type=mobile、repo_url 未设置 |
| 3 | `docs/PRD.md` | A 初稿 → C 定稿 | 页面清单/功能/版本/链路/数据契约/外部依赖/路线图/架构/原型说明/流程图 |
| 4 | `docs/api-contracts.md` | C2 | 9 个接口契约（全量、无 TBD） |
| 5 | `docs/Plan.md` | C3 | 功能总览/契约摘要/外部服务清单/前端后端清单/开发顺序 |
| 6 | `docs/prototypes/index.html` | B2 | P01 首页·账单列表（390×844） |
| 7 | `docs/prototypes/01-add-bill.html` | B2 | P02 添加账单 |
| 8 | `docs/prototypes/02-stats.html` | B2 | P03 分类统计 |
| 9 | `docs/prototypes/03-profile.html` | B2 | P04 个人中心 |
| 10 | `docs/prototypes/04-detail.html` | B2 | P05 账单详情/编辑 |
| 11 | `docs/prototypes/assets/style.css` | B2 | 原型共享样式（390 容器） |
| 12 | `docs/prototypes/README.md` | B2 | 生产前端交接说明（组件清单/Mock/真实 API 位置/视口验证） |

可选/不生成的项：《`docs/data-system.json`》——本项目数据模型简单、契约已完整落入 PRD 与 api-contracts，按精简产出原则**不需要**；如生成则与四件套并列于 `docs/`。

（入口 script 同时生成的初始化底座：`README.md`、`.gitignore`、`pyproject.toml`、`pycore/`、空 `docs/`、`.sdd/`，属于项目脚手架，不计入产品设计核心产物。开发完成后还需 `.sdd/tasks.json`、`.sdd/experience.md`、`.sdd/test-reports/` 等，属开发阶段产物。）

### 7.2 临时产物与清理时机

| # | 路径 | 产生阶段 | 清理时机 |
|---|---|---|---|
| T1 | `.sdd/tmp/visual-research.md` | R2（有视觉证据时） | R2 规定「B2 原型完成后再清理」；phase-B2 允许保留至「阶段 C 完成后再删除」以支撑契约/Plan 参考。**最终强制清理点：阶段 C 完成（PRD 自检要求 `.sdd/` 无残留草稿）**。本项目依法留到 C 完成删除。 |
| T2 | `.sdd/tmp/ui-design-spec.md` | B1 | **阶段 B2 完成收尾步骤 2 删除**（原型已画完，不再需要） |

补充说明（非文件临时物）：R0 需求对齐摘要、竞品调研结论、A 类页面/功能/版本确认稿均在**对话**中完成并**合并写入 PRD.md**，不单独建文件（精简产出）；视觉截图若产生宜先放 `.sdd/tmp/` 或 `docs/prototypes/assets/` 供 B 参考，最终随临时清理或随原型 assets 归档。

### 7.3 清理后的 `.sdd/` 状态（应在阶段 C 完成时满足）

```text
.sdd/
├── project.json        # 保留（项目状态）
├── experience.md       # 开发阶段回写（预留）
├── tasks.json          # 开发阶段 Planner 产出（预留）
└── tmp/                # 应为空或不存在（visual-research.md / ui-design-spec.md 均已删除）
```

---

## 8. 五个必答问题（结论）

### Q1：移动端 H5 项目的产品设计产出物遵循什么路径？

- **一切以 `active_project_path` 为根**：`Projects_Repo/project-accounting-h5/`，绝对路径 `e:/SDD_V7_1_2/SDD_V7_1_2/Projects_Repo/project-accounting-h5/`。
- **设计文档统一入 `docs/`**：`PRD.md`、`api-contracts.md`、`Plan.md`、`prototypes/`（以及可选的 `data-system.json`、仅在长/多分支需求下出现的 `docs/澄清文档/`）。
- **流程状态 / 临时文件统一入 `.sdd/`**：`project.json`（状态）、`tmp/visual-research.md`、`tmp/ui-design-spec.md`（临时）。
- **禁止写入 Harness 根目录**及任何非 active_project_path 位置（product design 产物不得出现在 `e:/SDD_V7_1_2/SDD_V7_1_2/docs` 等根级）。
- **注册表例外**：`project-registry.json` 属于 Harness 根级元数据，只能由 `scripts/sdd_project.py` 维护，项目自身不写。
- 前端代码目录（开发阶段）：H5 属于 Web 前端 → **`frontend/`**；`mobile/` 目录为原生 App 预留，本规范默认不支持原生（若原生需先补专项规范），本项目不使用。
- 移动端 H5 的**组件/视觉基准**：Ant Design Mobile（B1 默认基底的载体），与桌面 Web 的 Ant Design 区分。

### Q2：走完流程后最终应存在哪些文件（含完整路径）？

即第 7.1 节清单：在 `e:/SDD_V7_1_2/SDD_V7_1_2/` 下的 `project-registry.json`，以及 `Projects_Repo/project-accounting-h5/` 下的 `.sdd/project.json`、`docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md`、`docs/prototypes/`（index.html、01-add-bill.html、02-stats.html、03-profile.html、04-detail.html、assets/style.css、README.md）。`data-system.json` 本项目按需判断为不生成。`.sdd/tmp/` 两个临时文件在产品设计完成时已全部删除。

### Q3：哪些是临时产物？什么时机删除？

- **`.sdd/tmp/ui-design-spec.md`**（B1 生成，B2 依据）：**B2 完成收尾即删**（原型画完不再需要）。
- **`.sdd/tmp/visual-research.md`**（R2 生成）：R2 宣称 B2 完成后清理，B2 允许保留到 C 完成供契约/Plan 参考，**最迟在阶段 C 完成时删除**（PRD 自检要求 `.sdd/` 无残留草稿）。
- 对话中的中间稿（需求对齐摘要、页面/功能/版本确认稿、调研结论）不是文件，全部合并入 `PRD.md`，不建过程文件。

### Q4：完成后四件套是否齐全？

**齐全。** 产品设计阶段完成标准（SKILL.md 阶段判断 + phase-C 自检）的四件套：

| 件 | 路径 | 状态 |
|---|---|---|
| ① PRD.md | `Projects_Repo/project-accounting-h5/docs/PRD.md` | ✓（定稿，契约章节完整） |
| ② api-contracts.md | `Projects_Repo/project-accounting-h5/docs/api-contracts.md` | ✓（9 接口，无 TBD） |
| ③ Plan.md | `Projects_Repo/project-accounting-h5/docs/Plan.md` | ✓（含外部服务清单） |
| ④ prototypes/ | `Projects_Repo/project-accounting-h5/docs/prototypes/` | ✓（5 HTML + assets + README，390×844 验证） |

四件套齐全 → 「产品设计已完成，可进入 Agent 开发流程」。注意 Router「开发门禁」在四件套之外还需要：`.sdd/tasks.json`（Planner 产出）、运行时命令对齐、外部依赖已确认（本项目全部「无」天然满足）、以及用户明确「开始开发」。

### Q5：移动端视口相关说明（390×844）出现在哪个产物里？

**首个且作为规范源头的产物是 B1 产物 `.sdd/tmp/ui-design-spec.md`** 的「界面清单」表——每行「目标视口 = 移动端 390×844」（B1 阶段即用该视口明确所有 MVP 界面的绘制基准）。此后 390×844 继续出现在：

- **B2 原型产物 `docs/prototypes/`**：每个 HTML 以 390px 容器 + 移动端 viewport meta 实现并验证；
- **`docs/prototypes/README.md`**：生产前端交接说明中记录「已按 390×844 目标视口验证」；
- **阶段 C 定稿的 `docs/PRD.md`**：技术架构蓝图的部署/视口说明处（H5 适配基准）。

（Pencil / Stitch 模式下的 390×844 出现在各自模式的 Frame 尺寸/提示词视口字段：B2 模式 B「移动端 H5 默认尺寸 390×844」、模式 C「视口移动端 390×844」；本项目走模式 A HTML，未用到。）

---

## 9. 关键决策与理由摘要

| # | 决策 | 理由 |
|---|---|---|
| 1 | project_type = mobile；前端 React+TS+Vite+**Ant Design Mobile** | 用户明确手机端 H5；SDD 默认移动端 H5 组件库 |
| 2 | 本项目**无 AI 功能**，不写 AI 章节、无 LLM 依赖 | 四功能均为普通 CRUD + 聚合统计，且能规避外部密钥 |
| 3 | 融合视觉方向（鲨鱼清新绿 + 随手记记一笔路径 + Money Manager 数字呈现），低信息密度、圆润卡片 | 与「清新简单、适合手机浏览」诉求一致 |
| 4 | MVP 五页闭环：无趋势图、无搜索、无多账本；趋势图/搜索 V1.1，账号云同步 V2 | 保证 MVP「快速记账 + 月度回顾」核心闭环，图表库/同步复杂度与依赖延后 |
| 5 | **MVP 无账号体系**，设备 `clientId` 隔离数据 | 消除短信/三方登录等外部依赖与合规成本，MVP 可无密钥交付；V2 云同步时以 clientId 引导迁移 |
| 6 | 金额以**分（int）存储**，前端转元展示 | 规避浮点误差，利于聚合统计 |
| 7 | 统计聚合走后端 `GROUP BY`，MVP 用**自绘 SVG 环形图**而非 echarts | 控制依赖与体积，V2 再引图表库画趋势 |
| 8 | 数据契约（业务 + 统一响应格式）**完整设计、不随版本裁剪**；本项目不需要 `data-system.json` | A5 规则、精简产出原则 |
| 9 | 外部依赖草稿全部类别=「无」，显式列出并确认 | A5-3 完备性要求（无则写「无」），同时天然通过开发门禁第 7 条 |
| 10 | 原型走 B2 模式 A HTML，先 Junior Pass（缺竞品截图命中必做场景）再 Full Pass；`docs/prototypes/` 带 README 交接 | 忠实执行 phase-B2 门槛与 ui-design-standard 交接要求 |
| 11 | 临时产物两处、三个清理时点：ui-design-spec 于 B2 收尾删；visual-research 保留至 C 完成删（`.sdd/` 终态无草稿） | 精确落实 R2 / B2 / C 自检的清理规約 |

---

## 10. 完成语

```text
产品设计已完成。可以在当前对话中说「开始开发」，Router 将按开发门禁进入多 Agent 开发流程。
```

（以上全流程为文字模拟，未创建 `Projects_Repo/project-accounting-h5/` 下任何文件。）