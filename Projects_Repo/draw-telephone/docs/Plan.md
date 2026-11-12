# 开发计划

> 设计阶段与开发阶段的衔接文件。所有开发进度以本文件为准。
> 项目：画意接龙（draw-telephone）
> 最后更新：2026-08-19

## 一、功能清单总览

| 序号 | 功能名称 | 一句话描述 | 对应页面 | 优先级 | 状态 |
|------|---------|-----------|---------|--------|------|
| F01 | 广场作品流 | 展示公开已完成链作品卡片 | P01 | MVP | 待开发 |
| F02 | 创建链入口 | 登录用户发起新链 | P01/P02 | MVP | 待开发 |
| F03 | 加入链入口 | 房间码加入链 | P01/P03 | MVP | 待开发 |
| F04 | 链长参数设置 | 设链长/标题/公开性 | P02 | MVP | 待开发 |
| F05 | 起手题来源 | 手动写题或 AI 生成 | P02 | MVP | 待开发 |
| F06 | 房间码生成 | 创建后生成房间码+邀请链接 | P02 | MVP | 待开发 |
| F07 | 房间码校验 | 6 位码校验加入 | P03 | MVP | 待开发 |
| F08 | 邀请链接解析 | 带码链接直接加入 | P03 | MVP | 待开发 |
| F09 | 链状态展示 | 进度/当前节点/成员 | P04 | MVP | 待开发 |
| F10 | 实时围观 | WebSocket 推送作画笔迹 | P04/P05 | MVP | 待开发 |
| F11 | 轮到你入口 | 当前责任人进入接力 | P04 | MVP | 待开发 |
| F12 | 提交通知 | 节点提交通知下一位 | P04 | MVP | 待开发 |
| F13 | 链完成入口 | 链完成出现回放入口 | P04 | MVP | 待开发 |
| F14 | AI 补位倒计时 | 24h 未提交显示倒计时 | P04 | MVP | 待开发 |
| F15 | 上一节点展示 | 只看上一节点防剧透 | P05 | MVP | 待开发 |
| F16 | 画布涂鸦 | 笔刷/色/粗/擦/撤销作画 | P05 | MVP | 待开发 |
| F17 | 文字描述输入 | ≤30 字描述 | P05 | MVP | 待开发 |
| F18 | 提交接力 | 提交当前节点 | P05 | MVP | 待开发 |
| F19 | 整链只读展示 | 全链纵向+署名+AI续标注 | P06 | MVP | 待开发 |
| F20 | 分享链接 | 生成只读分享链接 | P06 | MVP | 待开发 |
| F21 | 回放入口 | 进回放页 | P06 | MVP | 待开发 |
| F22 | 逐节点渐显回放 | 动画 2s 间隔 | P07 | MVP | 待开发 |
| F23 | 投票 | 三维度各一票 | P07 | MVP | 待开发 |
| F24 | 投票结果展示 | 三维度统计 | P07 | MVP | 待开发 |
| F25 | 我的作品 | 参与/创建的链列表 | P08 | MVP | 待开发 |
| F26 | 账号注册 | 用户名+密码注册 | P09 | MVP | 待开发 |
| F27 | 账号登录 | 用户名+密码登录 | P09 | MVP | 待开发 |
| F28 | 游客浏览提示 | 先逛逛入口 | P09 | MVP | 待开发 |
| F29 | 通知铃铛 | 通知列表+未读红点 | 全局 | MVP | 待开发 |
| F30 | AI 起手 | AI 生成种子题（DeepSeek） | P02/后端 | MVP | 待开发 |
| F31 | AI 补位 | 24h 超时 AI 续链（通义万相） | 后端 | MVP | 待开发 |
| F32 | 图片上传 | 画作 PNG 上传 | P05/后端 | MVP | 待开发 |
| F33 | 广场筛选排序 | 最新/最跑偏/最多点赞 | P01 | V1.1 | 待开发 |
| F34 | 导出整链长图 | 拼接长图导出 | P06 | V1.1 | 待开发 |
| F35 | 游客点赞 | IP/设备去重点赞 | P06 | V1.2 | 待开发 |
| F36 | 回放控制 | 暂停/继续/重播 | P07 | V1.2 | 待开发 |
| F37 | 个人设置 | 昵称/头像 | P08 | V1.3 | 待开发 |
| F38 | 第三方登录 | 微信等登录 | P09 | V2 | 待开发 |

## 二、数据契约摘要

> 完整数据契约见 PRD.md「数据契约确认清单」章节；统一响应格式与接口契约见 [api-contracts.md](api-contracts.md)（唯一权威源，不在本文件重复列出）。

核心实体：用户（User）、链（Chain）、节点（Node）、投票（Vote）、通知（Notification）、作品（Work=已完成链的只读视图）。

## 二点五、外部服务与测试权限清单

> **开发硬门禁**：本清单是 PRD「A5-3 外部依赖与配置草稿」经用户确认后的落定版。真实 Key/Token/Secret 不写入本文档，只记录字段名、用途和配置状态；真实值只进 `.env`。

| 服务 | 用途 | 配置项字段 | MVP 必需 | Tester 完整联调权限 | 缺失时策略 | 状态 |
|------|------|------------|----------|--------------------|------------|------|
| DeepSeek（LLM 文本） | AI 起手题词生成 | `DEEPSEEK_API_KEY` `DEEPSEEK_BASE_URL` `DEEPSEEK_MODEL` | 是 | 用户提供测试 Key + 可调用额度 | Mock 降级（返回固定题词） | ✅ 已确认，用户提供 Key |
| 通义万相（图像生成） | AI 补位画节点续画 | `DASHSCOPE_API_KEY` `WANX_MODEL` | 是 | 用户提供测试 Key + 可调用额度 | Mock 占位图 | ✅ 已确认，用户提供 Key |
| 通义万相/qwen-vl（多模态） | AI 补位述节点看图生成描述 | 复用 `DASHSCOPE_API_KEY` `QWEN_VL_MODEL` | 是 | 用户提供测试 Key + 可调用额度 | Mock 降级（返回固定描述） | ✅ 已确认，同百炼 Key |
| 对象存储 | 存画作 PNG | 本地文件存储（MVP） | 是 | 无需 Key | 本地存储兜底 | ✅ 已确认，默认本地，V2 上 OSS |
| 数据库 | 持久化用户/链/节点/投票 | `DATABASE_URL`（SQLite，MVP） | 是 | 无需 Key | SQLite 兜底 | ✅ 已确认，默认 SQLite，V2 迁移 |
| WebSocket | 实时围观笔迹推送 | FastAPI WebSocket（无外部依赖） | 是 | 无需 Key | 无 | ✅ 已确认 |
| 第三方登录 | 微信等登录 | AppID/Secret、回调地址 | 否 | — | V2，MVP 用户名密码 | ✅ 已确认延后 |

**进开发前待办**：
- [ ] 用户提供 DeepSeek API Key，写入 backend/.env
- [ ] 用户提供百炼 API Key（通义万相），写入 backend/.env
- [ ] 确认 DeepSeek base_url / model 名称
- [ ] 确认通义万相 model 名称（文生图 + 多模态）

## 三、前端开发清单

### 前端技术选型

| 层级 | 选择 | 说明 |
|------|------|------|
| 框架 | React | 业务型 Web App |
| 语言 | TypeScript | 所有组件/service/DTO 类型化 |
| 构建工具 | Vite | 本地开发、代理、构建 |
| 路由 | react-router | 页面路由与鉴权守卫 |
| 状态管理 | Zustand | 登录态、全局 UI 状态 |
| 请求库 | Axios | 统一 API 实例、拦截器、错误处理 |
| 桌面 Web 组件库 | Ant Design | PC Web |
| 画布 | canvas 2D | 涂鸦画布 + pointer 事件 + 笔迹序列化 |
| 实时通信 | 原生 WebSocket | 实时围观笔迹推送 |
| 动画 | framer-motion | 逐节点渐显回放 |
| 工程化 | ESLint + Prettier + type-check + build | 自动验收必须覆盖 |

### 前端页面清单

| 序号 | 页面名称 | 涉及功能 | Mock 数据来源 | 状态 |
|------|---------|---------|--------------|------|
| P01 | 首页/广场 | F01,F02,F03,F29 | api-contracts GET /api/works | 待开发 |
| P02 | 创建链页 | F04,F05,F06,F30 | api-contracts POST /api/chains, POST /api/ai/prompt | 待开发 |
| P03 | 加入链页 | F07,F08 | api-contracts GET /api/chains/{code}, POST /api/chains/{id}/join | 待开发 |
| P04 | 链大厅 | F09,F10,F11,F12,F13,F14 | api-contracts GET /api/chains/{id}, WS /ws/room/{id} | 待开发 |
| P05 | 接力作画/描述页 | F15,F16,F17,F18,F10 | api-contracts GET /api/nodes/{id}/previous, POST /api/nodes/{id}/submit, WS | 待开发 |
| P06 | 作品详情页 | F19,F20,F21 | api-contracts GET /api/works/{id} | 待开发 |
| P07 | 整链回放页 | F22,F23,F24 | api-contracts POST /api/chains/{id}/votes, GET /api/chains/{id}/votes/result | 待开发 |
| P08 | 个人主页 | F25 | api-contracts GET /api/users/me/works | 待开发 |
| P09 | 登录/注册页 | F26,F27,F28 | api-contracts POST /api/auth/register, POST /api/auth/login | 待开发 |

### 前端自动验收标准
- [ ] 所有页面 UI 与原型（draw-telephone.pen）一致
- [ ] 所有页面使用 Mock 数据可正常交互
- [ ] Mock 数据格式与 api-contracts.md 完全一致
- [ ] Agent/Tester 自动验收通过

> 前端 Mock 页面完成后触发用户门禁，由用户验收 UI/UX 效果；用户确认后进入后端基础设施开发。
> 后端业务任务完成时，必须把对应前端 service/page 切到 `VITE_USE_MOCK=false` 的真实后端联调路径。

## 四、后端开发清单

| 序号 | 功能名称 | 依赖 | 对应接口 | 状态 |
|------|---------|------|---------|------|
| B00 | 基础设施（pycore 脚手架） | 无 | GET /health | 待开发 |
| B01 | 用户认证（注册/登录/JWT） | B00 | POST /api/auth/register, POST /api/auth/login | 待开发 |
| B02 | 链创建（含房间码生成） | B00,B01 | POST /api/chains | 待开发 |
| B03 | AI 起手题生成 | B00 | POST /api/ai/prompt（DeepSeek） | 待开发 |
| B04 | 链查询/加入 | B02 | GET /api/chains/{code}, POST /api/chains/{id}/join, GET /api/chains/{id} | 待开发 |
| B05 | 节点接力（上一节点/提交） | B04 | GET /api/nodes/{id}/previous, POST /api/nodes/{id}/submit | 待开发 |
| B06 | 图片上传 | B00 | POST /api/upload/image（本地存储） | 待开发 |
| B07 | WebSocket 实时围观 | B04 | WS /ws/room/{id} | 待开发 |
| B08 | 作品详情（只读全链） | B04 | GET /api/works, GET /api/works/{id} | 待开发 |
| B09 | 投票 | B04 | POST /api/chains/{id}/votes, GET /api/chains/{id}/votes/result | 待开发 |
| B10 | 通知 | B00,B01 | GET /api/notifications, POST /api/notifications/read | 待开发 |
| B11 | 个人资料/我的作品 | B01 | GET /api/users/me, GET /api/users/me/works | 待开发 |
| B12 | AI 补位定时任务 | B03,B05 | 后台任务（通义万相 + qwen-vl） | 待开发 |

### 后端任务验收规则

- **基础设施任务基于 pycore 框架**：禁止自己重写 config.py、server.py、logger.py；配置管理使用 `pycore.core.ConfigManager`，服务器使用 `pycore.api.APIServer`，数据库骨架从 `pycore/integrations/db/` 复制模板
- 基础设施任务由 Agent 自动连续执行，不触发用户门禁；验收标准：ruff/mypy 通过、单元测试通过、`GET /health` 返回 200
- 对应前端页面或 service 的业务任务：必须在任务内完成真实联调验收，每个功能是一个完整闭环（后端 API + 前端 Mock 切真实）
- 真实联调验收至少包含：
  - `VITE_USE_MOCK=false` 时前端调用真实后端 API
  - 对应页面核心操作可用
  - 页面不得展示该功能相关 `[Mock]` 数据、Mock 账号提示或 Mock-only 文案
  - Tester 能证明请求命中真实后端，而不是 `frontend/src/mocks/*`
- 最终 E2E / 回归阶段只做全系统复查，不承担第一次前后端联调
- 涉及外部服务的后端任务（B03 AI 起手、B12 AI 补位），必须引用「外部服务与测试权限清单」；如果必要 Key/权限缺失，只能标记 Mock/fallback 验收，不得宣称真实外部服务联调通过

## 五、功能详情（开发时逐个展开）

> 以下详情在开发阶段由 Developer 和 Tester 逐个展开和验收。关键实现思路见 PRD.md「复杂功能业务链路」章节：
> - 实时围观（WebSocket 笔迹事件流）
> - AI 起手（DeepSeek 题词生成）
> - AI 补位（通义万相文生图 + qwen-vl 多模态看图，24h 超时扫描）
> - 整链回放（framer-motion 逐节点渐显）

## 六、开发顺序建议

> 以下顺序是默认推荐节奏，实际开发以 Planner 产出的 tasks.json 为准。

**阶段1：前端 MVP（Mock，用户先验收 UI/UX）**
1. 所有前端页面（P09 → P01 → P02 → P03 → P04 → P05 → P06 → P07 → P08）使用 Mock 数据完成
2. 验收（用户门禁）：用户打开页面，确认布局、配色、交互与原型 draw-telephone.pen 一致

**阶段2：后端基础设施（自动连续执行，不触发用户门禁）**
1. 基于 pycore 脚手架初始化项目结构、配置、数据库、中间件
2. 验收（Agent 自动）：ruff/mypy 通过、单元测试通过、`GET /health` 返回 200

**阶段3：逐功能闭环开发（每个功能完成后触发用户门禁）**
1. 按业务依赖逐个推进：认证(B01) → 链创建(B02) → AI起手(B03) → 链查询加入(B04) → 节点接力(B05) → 图片上传(B06) → WebSocket围观(B07) → 作品详情(B08) → 投票(B09) → 通知(B10) → 个人(B11) → AI补位(B12)
2. 每个功能 = 后端真实 API + 前端 Mock 切真实 + 联调验收
3. 验收（用户门禁）：用户从前端页面操作验证功能可用

**阶段4：E2E 回归测试**
1. 完整流程走通（注册→创建链→邀请→接力→AI补位→回放→投票→分享）
2. 验收（用户门禁）：全流程通过，无阻塞性 Bug
