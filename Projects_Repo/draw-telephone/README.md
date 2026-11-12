# 画意接龙（Draw Telephone）

> 异步绘画接龙游戏：A 画 → B 描述 → C 看描述画 → …… 回放整链看「跑偏」。
> 技术栈：前端 React 19 + TypeScript 6 + Vite 8 + Ant Design 6；后端 Python 3.11 + FastAPI + pycore 脚手架 + SQLite。

本项目由 SDD V7.1 管理。核心目录：

- `.sdd/`：项目状态、任务、经验、日志、测试报告
- `docs/`：PRD、API 契约、开发计划、原型、启动文档
- `AGENTS.md`：项目轻入口；核心规则仍在 Harness 根目录 `harness-core/`

---

## 一、环境要求

### 运行时版本

| 组件 | 版本 | 说明 |
|------|------|------|
| Node.js | v24+ | 前端构建/开发服务器 |
| npm | 11+ | 前端包管理 |
| Python | 3.11.9 | 后端运行时（项目根 `.venv` 已配置） |

### 后端依赖（已装在项目根 `.venv/`）

| 包 | 版本 | 用途 |
|----|------|------|
| fastapi | 0.141.1 | Web 框架 |
| uvicorn | — | ASGI 服务器 |
| sqlalchemy | 2.x | ORM（异步） |
| aiosqlite | — | SQLite 异步驱动 |
| pydantic / pydantic-settings | 2.x | 数据校验 + .env 配置 |
| httpx | — | 异步 HTTP 客户端（调 MaaS） |
| apscheduler | 3.11.3 | AI 补位定时任务 |
| bcrypt | — | 密码哈希 |
| python-jose | — | JWT |
| ruff | 0.16.3 | Linter（dev） |
| mypy | 2.3.1 | 类型检查（dev） |
| pytest | — | 测试（dev） |

> **注意**：后端依赖装在**项目根** `.venv/`（`draw-telephone/.venv/Scripts/python.exe`），不是 `backend/.venv/`。pycore 通过 `PYTHONPATH=..` 导入，不走 pip 安装。

### 前端依赖

见 [frontend/package.json](frontend/package.json)：React 19.2 / Ant Design 6.6 / react-router 7.18 / Zustand 5.0 / Axios 1.19 / framer-motion 13.1。

### 外部服务

| 服务 | 用途 | 配置 | 是否必需 |
|------|------|------|----------|
| 公司内网 MaaS / 海康（DeepSeek-V4-Flash-0731） | AI 起手题词生成（T-015） | `DEEPSEEK_*` | 可降级（Key 缺失返回 503 + 本地题词池） |
| 公司内网 MaaS / 海康（Qwen-Image） | AI 补位画节点文生图 + 接力页 AI 辅助（T-024） | `IMAGE_*` | 可降级（补位失败跳过，下次扫描重试） |
| 公司内网 MaaS / 海康（Qwen3.6-35B-A3B-FP8） | AI 补位述节点看图 + 接力页 AI 辅助（T-024） | `VLM_*` | 可降级（看图失败降级纯文本续写） |
| SQLite | 业务库 | `DATABASE_PATH` | 必需（本地文件，自动创建） |
| WebSocket | 实时围观笔迹 + 通知推送（T-019） | FastAPI 内置 | 必需 |

> MaaS Key 已配置在 `backend/.env`。三个 AI 服务共用同一 Key，均走 `https://maas.hikvision.com.cn/v1`。

---

## 二、默认配置

### 后端 `backend/.env`

从 [backend/.env.example](backend/.env.example) 复制为 `.env` 并填值。关键字段：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | 127.0.0.1 | 后端监听地址 |
| `PORT` | 8099 | 后端端口 |
| `DEBUG` | true | 调试模式（日志 DEBUG 级） |
| `CORS_ORIGINS` | localhost/127.0.0.1:5199 + :5175 | 跨域白名单 |
| `DATABASE_PATH` | backend/data/draw_telephone.db | SQLite 路径（相对项目根） |
| `JWT_SECRET` | （需填长随机串） | JWT 签名密钥 |
| `JWT_ALGORITHM` | HS256 | — |
| `JWT_EXPIRE_HOURS` | 168（7 天） | Token 有效期 |
| `DEEPSEEK_API_KEY` | （MaaS Key） | 起手题词 |
| `IMAGE_API_KEY` | （MaaS Key） | 文生图 |
| `VLM_API_KEY` | （MaaS Key） | 看图描述 |
| `AI_FILL_TIMEOUT_HOURS` | 24 | 节点超时补位阈值 |
| `CHAIN_EXPIRE_DAYS` | 7 | 链过期天数 |
| `UPLOAD_DIR` | uploads | 上传目录（相对 backend/） |
| `UPLOAD_URL_PREFIX` | /uploads | 上传 URL 前缀 |

### 前端 `frontend/.env`

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE_URL` | /api | API 基址（相对路径，走 Vite 代理） |
| `VITE_USE_MOCK` | true | Mock 开关（联调改 false） |
| `VITE_BACKEND_PROXY_TARGET` | http://localhost:8099 | 后端代理目标 |

> **真实联调**：把 `VITE_USE_MOCK` 改为 `false`，前端请求走 Vite 代理命中真实后端。

---

## 三、端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 5199 | 前端 Vite 开发服务器 | 浏览器访问 http://localhost:5199 |
| 8099 | 后端 FastAPI（uvicorn） | /api、/ws、/uploads、/health |
| 5175 | （备用）用户门禁验证端口 | CORS 已放行 |

Vite 代理配置（[frontend/vite.config.ts](frontend/vite.config.ts)）：

- `/api` → 后端 8099（HTTP）
- `/uploads` → 后端 8099（静态图片）
- `/ws` → 后端 8099（WebSocket，`ws: true`）

---

## 四、启动方法

需要起两个服务（后端 + 前端），分两个终端窗口运行。

### 1. 后端（端口 8099）

```bash
cd backend
PYTHONPATH=.. ../.venv/Scripts/python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8099
```

> - `PYTHONPATH=..` 让 `import pycore` 和 `import src` 生效（pycore 在项目根，src 在 backend/）。
> - 首次启动自动建表（`init_db` on_startup）+ 启动 AI 补位定时任务（`init_scheduler` on_startup，每小时扫描）。
> - 健康检查：访问 http://localhost:8099/health 应返回 200。

### 2. 前端（端口 5199）

```bash
cd frontend
npm install        # 首次
npm run dev        # 开发服务器，http://localhost:5199
```

> 真实联调前确认 `frontend/.env` 的 `VITE_USE_MOCK=false`。

### 3. 数据库初始化（可选，手动 seed）

```bash
cd backend
PYTHONPATH=.. ../.venv/Scripts/python.exe scripts/init_db.py
```

> 初始化 SQLite + 建表 + seed（3 用户 / 1 链 / 6 节点 / 3 通知）。uvicorn 启动时也会自动建表，此脚本用于重置/seed。

### 4. 演示账号

| 账号 | 密码 | 说明 |
|------|------|------|
| demo | 123456 | 已创建的演示用户 |

### 5. 关闭项目

查找占用端口的进程并强制结束：

```bash
# 查找占用 5199 / 8099 的进程 PID
netstat -ano | grep -E ':5199|:8099' | grep LISTEN

# 强制结束（替换 <PID> 为上一步查到的值）
taskkill //F //PID <前端PID>
taskkill //F //PID <后端PID>
```

> Windows 下 `kill` 命令对本地进程无效，必须用 `taskkill //F //PID`。

---

## 五、质量门禁命令

### 后端

```bash
cd backend
PYTHONPATH=.. ../.venv/Scripts/python.exe -m ruff check src tests          # Lint
PYTHONPATH=.. ../.venv/Scripts/python.exe -m mypy src                       # 类型检查
PYTHONPATH=.. ../.venv/Scripts/python.exe -m pytest tests -q                # 测试（113 passed）
```

### 前端

```bash
cd frontend
npm run type-check    # tsc -b --noEmit
npm run lint          # oxlint
npm run build         # 生产构建
```

---

## 六、E2E 全流程

完整用户旅程（`VITE_USE_MOCK=false` 走真实后端）：

1. **注册/登录**（P09）：注册用户 A → 自动登录 → 广场页（P01）
2. **创建链**（P02）：设置链长 4-10 / 标题 / 公开性 / 起手题（手动或 AI 生成）→ 提交 → 跳链大厅（P04），显示真实房间码
3. **邀请加入**（P03）：用户 B 输入房间码 → 校验 → 加入 → 链大厅
4. **接力**（P05）：当前责任人看上一节点 → 作画（canvas 涂鸦）/ 描述（≤30 字）→ 提交（画节点上传 PNG）→ 返回链大厅，进度推进，下一位收 your_turn 通知
5. **实时围观**（P04）：WS 推送笔迹，在线成员实时看到作画过程
6. **AI 辅助**（接力页）：画节点点「AI 帮我画」→ Qwen-Image 文生图贴到画布；述节点点「AI 帮我写」→ Qwen3.6 VLM 看图生成描述填入输入框（真人署名，非 AI 补位）
7. **AI 补位**（T-024）：节点 24h 未提交 → APScheduler 每小时扫描 → AI 补位（draw 调 Qwen-Image / describe 调 Qwen3.6 VLM）→ is_ai=true + 推进 + 通知下一位；链 7 天未完成 → 标记 expired + 通知成员
8. **链完成**：所有节点提交 → status=completed → 成员收 chain_done 通知
9. **作品详情**（P06）：只读全链纵向展示，AI 节点带「AI 续」冷灰蓝标签
10. **回放 + 投票**（P07）：逐节点渐显回放 → 三维度投票（最跑偏/最佳画/最佳描述）→ 看结果统计
11. **分享**：作品详情页生成只读链接，游客可浏览
12. **个人主页**（P08）：看个人资料 + 参与链数/创建链数 + 我的作品列表

---

## 七、项目结构

```
draw-telephone/
├── backend/
│   ├── src/
│   │   ├── api/routes/      # 路由层（auth/chains/nodes/notifications/users/works/votes/ai/upload）
│   │   ├── api/ws.py        # WebSocket ConnectionManager
│   │   ├── core/config.py   # pydantic-settings 读 .env
│   │   ├── core/security.py # bcrypt + JWT
│   │   ├── db/              # models.py(ORM) + session.py(async session)
│   │   ├── models/          # Pydantic 请求/响应模型
│   │   ├── repositories/    # 数据访问层
│   │   ├── services/        # 业务逻辑层（ai/ai_fill/chain/node/...）
│   │   ├── scheduler.py     # APScheduler AI 补位定时任务
│   │   └── main.py          # FastAPI 入口（pycore APIServer）
│   ├── tests/              # 113 测试（T-001~T-024）
│   ├── data/               # SQLite 文件
│   ├── uploads/            # 上传图片
│   ├── .env / .env.example
│   └── scripts/init_db.py
├── frontend/
│   ├── src/
│   │   ├── pages/          # P01-P09 页面
│   │   ├── services/       # API 调用（auth/chains/nodes/...）
│   │   ├── stores/         # Zustand 状态
│   │   ├── components/     # 通用组件
│   │   └── types/          # TS 类型
│   ├── mocks/              # Mock 响应（VITE_USE_MOCK=true）
│   └── vite.config.ts
├── pycore/                 # 公司脚手架（PYTHONPATH=.. 导入，不 pip）
├── docs/
│   ├── PRD.md
│   ├── Plan.md
│   ├── api-contracts.md
│   └── startup.md
└── .sdd/                   # SDD Harness 任务/状态/报告
```

---

## 八、后端分层架构

```
models/(Pydantic) → db/models.py(ORM) → repositories/ → services/ → api/deps.py → api/routes/
```

每层只依赖下层：

- **models/**：Pydantic 请求/响应模型（校验 + 序列化）
- **db/models.py**：SQLAlchemy ORM 模型（User/Chain/ChainMember/Node/Vote/Notification）
- **repositories/**：数据访问（纯 CRUD，不含业务逻辑）
- **services/**：业务逻辑（编排 repository + 外部调用）
- **api/routes/**：HTTP 路由（鉴权 + 调 service + 契约响应）
- **api/deps.py**：依赖注入（get_db / get_current_user）

### 错误响应契约

所有错误响应统一格式（[docs/api-contracts.md](docs/api-contracts.md)）：

```json
{"code": 404, "message": "链不存在", "data": null}
```

`main.py` 注册全局异常处理器：`HTTPException` → 契约格式；`RequestValidationError` → 422 转 400。

### 数据库会话

- **请求级**：`get_db` 依赖注入，`yield session` 后自动 `commit`（成功）/ `rollback`（异常）。路由层只需 `add/flush`，不需显式 commit。
- **非请求级**（WS 循环 / 定时任务）：`async_session_maker()` 独立 session，自行 commit/rollback。

---

## 九、AI 能力

### AI 辅助（接力页手动触发）

接力页提供「AI 帮我画 / AI 帮我写」按钮，用户主动触发：

- **画节点**：调 Qwen-Image 文生图，把 AI 生成的图贴到画布（用户可继续涂鸦或直接提交）
- **述节点**：调 Qwen3.6 VLM 看上一节点画作，生成描述填入输入框（用户可编辑后提交）

> AI 辅助是**真人署名**（`is_ai=false`），区别于下方的 AI 补位。

### AI 补位定时任务（T-024，自动）

- **触发**：APScheduler `AsyncIOScheduler`，每小时执行 `_ai_fill_job`
- **扫描**：`AiFillService.scan_and_fill()` 查所有 `in_progress` 链
  - 24h 超时：pending 节点 `created_at + 24h < now` → AI 补位
  - 7 天过期：链 `created_at + 7d < now` 且未完成 → `status=expired` + 通知成员
- **补位**：
  - draw 节点（seq 偶数）：调 Qwen-Image 文生图，输入=上一节点 content_text（seq=0 用 chain.prompt_text）
  - describe 节点（seq 奇数）：调 Qwen3.6 VLM 看图，输入=上一节点 content_url（本地 base64 优先，远程 URL 下载失败降级纯文本续写）
- **补位后**：`is_ai=true` + `status=ai_filled` → 推进链 → 建下一节点（轮转下一位）→ 通知（your_turn 给下一位 + node_submitted 给成员；链完成则 chain_done 给所有成员）
- **容错**：单节点补位失败记日志跳过，下次扫描重试，不中断整批

### MaaS 限流

MaaS 有 qpm（每分钟请求数）限制，超限时返回 403。后端已处理：403 转为 503 + 友好提示「图像生成/理解服务繁忙（频率受限），请稍后重试」，冷却约 30s 后恢复。

---

## 十、测试覆盖

| 任务 | 测试文件 | 测试数 | 覆盖 |
|------|----------|--------|------|
| T-012 | test_t012_db.py | 3 | DB 骨架 + 认证依赖 |
| T-013 | test_t013_auth.py | 9 | 注册/登录/JWT |
| T-014 | test_t014_chain_create.py | 6 | 链创建 + 房间码 |
| T-015 | test_t015_ai_prompt.py | 6 | AI 起手题 + 降级 |
| T-016 | test_t016_chain_query.py | 11 | 链查询/加入/详情 |
| T-017 | test_t017_node_relay.py | 14 | 节点接力 + 防剧透 |
| T-018 | test_t018_upload.py | 5 | 图片上传 |
| T-019 | test_t019_ws.py | 8 | WebSocket |
| T-020 | test_t020_works.py | 11 | 作品详情/广场 |
| T-021 | test_t021_votes.py | 10 | 投票 |
| T-022 | test_t022_notifications.py | 10 | 通知 |
| T-023 | test_t023_users.py | 11 | 个人资料/作品 |
| T-024 | test_t024_ai_fill.py | 10 | AI 补位 |
| **合计** | | **113** | 全量通过 |

测试隔离：每个测试用内存 SQLite（`:memory:`）+ `app.dependency_overrides[get_db]` 注入，与运行时业务库物理隔离。

---

## 十一、常见问题

**Q: 后端启动报 `ModuleNotFoundError: No module named 'pycore'`？**
A: 必须在 `backend/` 目录下启动且带 `PYTHONPATH=..`（pycore 在项目根）。

**Q: 前端请求 404 / 连不上后端？**
A: 确认后端在 8099 运行；确认 `frontend/.env` 的 `VITE_USE_MOCK=false`；确认 `VITE_BACKEND_PROXY_TARGET=http://localhost:8099`。

**Q: WebSocket 连不上？**
A: Vite 代理 `/ws` 已配 `ws: true`；浏览器用相对路径 `ws://localhost:5199/ws/room/{chain_id}?token=JWT`，不要硬编码 8099。

**Q: AI 起手题/补位/辅助失败？**
A: 检查 `backend/.env` 的 `DEEPSEEK_API_KEY`/`IMAGE_API_KEY`/`VLM_API_KEY` 是否填了 MaaS Key；Key 缺失会返回 503 + 降级（起手题用本地题词池，补位跳过下次重试）。若提示「频率受限」，是 MaaS qpm 限流，冷却 30s 后重试。

**Q: 数据库想重置？**
A: 删 `backend/data/draw_telephone.db` 后重启 uvicorn（自动建表），或跑 `scripts/init_db.py` 重新 seed。

**Q: 怎么关闭项目？**
A: 见上文「四、启动方法 → 5. 关闭项目」，用 `taskkill //F //PID` 强制结束占用 5199/8099 的进程。
