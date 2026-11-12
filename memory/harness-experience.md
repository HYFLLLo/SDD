# SDD V7.1 — 系统级经验

> 记录跨项目可复用、能反哺 Harness 本体的经验。  
> 不记录具体项目的业务细节；项目细节写入 `Projects_Repo/<project-id>/.sdd/experience.md`。

---

## 2026-05-11｜移动端项目不得套用 Web 产品设计与 Web Rules

- **来源**：V5 → V6 架构升级讨论
- **经验**：当前 Harness 的产品设计 Skill 和 `dev-standards/frontend.mdc` 都偏 Web。移动端项目可以复用多 Agent 协同机制，但不能默认触发 Web 产品设计 Skill，也不能读取 Vue/Web 前端 rules。
- **规则**：
  - 移动端项目必须先警告用户当前缺少移动端规范
  - 用户确认继续后，要求用户自备 PRD / 原型 / API 契约 / Plan
  - 移动端客户端任务 `rules_files=[]`
  - 只有后端 API 任务才读取 backend rules

## 2026-05-11｜Bugfix 必须回查经验并反哺经验

- **来源**：V6 Bugfix 流程升级
- **经验**：Bugfix 不是单纯修代码，而是经验系统的入口。
- **规则**：
  - 修复前必须读取项目 `.sdd/experience.md`
  - 如果已有相关经验，必须分析为什么仍然犯错
  - 修复后必须写 bugfix 报告
  - 修复后必须更新项目经验

## 2026-05-12｜后端业务任务必须任务内完成前端真实联调

- **来源**：customer-service 自动化 Coding 复盘。项目所有任务显示 passed，但用户打开前端仍看到 Mock 数据。
- **经验**：前端 Mock 是产品交互和接口契约对齐阶段的工具；一旦进入后端业务任务，任务 Done Definition 必须包含“对应前端在 `VITE_USE_MOCK=false` 下调用真实后端”。否则后端只完成了 API，不代表用户功能完成。
- **规则**：
  - Planner 生成 Web 后端业务任务时，必须写入 `frontendIntegration.required=true`
  - 对应已有前端页面或 service 的后端任务，acceptanceCriteria 必须包含真实前端联调标准
  - Developer 完成后端业务功能时，必须同步修正对应前端 service / store / page，不能让默认验收路径继续走 Mock
  - Tester 不得只用 curl/API 判 PASS；必须验证 `VITE_USE_MOCK=false` 路径、真实后端请求和页面无 `[Mock]` 残留
  - 最终 E2E 只做全系统回归，不能替代单个后端业务任务内的首次真实联调

## 2026-05-12｜自动化开发前必须确认外部服务与 Tester 权限

- **来源**：SDD V7.1 自动化 Coding 复盘。缺少真实服务 Key 时，系统容易用 Mock/fallback 跑完任务并误判为完整联调。
- **经验**：外部服务配置不是后端任务中途才讨论的问题，而是进入多智能体自动化开发前的门禁。否则 Tester 没有完整权限，只能测 Mock/fallback，无法验证真实业务链路。
- **规则**：
  - `/sdd-start` 进入 Planner 前必须先确认外部服务清单
  - 清单必须包含服务名称、用途、配置字段、MVP 必需性、Tester 联调权限、缺失时策略
  - 必要 Key / 测试账号 / Base URL / 回调配置缺失时必须暂停索取
  - 用户明确选择不提供时，相关能力只能标记 Mock/fallback 降级验收
  - 真实 Key 不写入 PRD、Plan、tasks.json、测试报告或经验文件，只写入 `.env`

## 2026-05-21｜后端业务任务必须验证 Vite 开发代理配置

- **来源**：smart-customer-service T-010 用户登录闭环。后端登录接口开发完成，但前端请求始终失败，排查后发现 `vite.config.ts` 未配置 `/api` 开发代理，导致浏览器把请求识别为跨域，OPTIONS 预检异常。
- **经验**：Vite 代理是前后端本地联调的基础设施，不是"有报错才配"的补救措施。Developer 完成后端业务任务时，如果只改了前端 service 但没检查代理配置，Tester 的真实联调会莫名其妙失败，浪费大量时间排查 CORS/端口/中间件等错误方向。
- **规则**：
  - `frontend/vite.config.ts` 必须配置 `server.proxy['/api']` 指向后端端口（默认 `http://localhost:8000`）
  - `frontend/.env` 中 `VITE_API_BASE_URL` 必须使用相对路径 `/api`，禁止写完整 URL（如 `http://localhost:8000/api`）触发 CORS
  - WebSocket 路径 `/ws` 必须单独配置 `ws: true` 代理，前端代码禁止硬编码 `ws://localhost:8000`
  - Developer 输出前必查清单中增加 Vite 代理检查项；Tester 真实联调验证中增加代理配置检查
  - 修改 `vite.config.ts` 或 `.env` 后必须重启 Vite 开发服务器

## 2026-05-22｜固定高度容器的设计必须预留 20% 缓冲空间

- **来源**：customer-service T-003 员工端 Mock 实现。TicketCard 组件使用 `h-20`（80px）固定高度容纳三行文本，经过 5 次 Bugfix（空格、truncate 宽度、leading-tight、仍不够）才发现根本问题是**容器尺寸本身不合理**，最终增加到 `h-24`（96px）解决。
- **经验**：前端固定高度容器（`h-[固定值]`）容纳多行文本时，不能"刚好够用"，必须预留缓冲空间。浏览器实际渲染高度受字体、字重、抗锯齿、line-height 影响，原型工具中的尺寸往往比实际偏小。如果容器高度 = 内容理论高度，实际渲染时极易溢出截断。
- **规则**：
  - **固定高度容器设计公式**：`容器高度 ≥ 内容理论高度 × 1.2`（预留 20% 缓冲）
  - **内容理论高度计算**：`Σ(font-size × line-height × 行数) + Σ(gap) + padding（上下）`
  - **卡片高度经验值**（基于 `text-sm` 14px + `leading-tight` 1.25）：
    - 单行内容：最小 `h-12`（48px）
    - 两行内容：最小 `h-20`（80px）
    - 三行内容：最小 `h-24`（96px）
    - 四行内容：最小 `h-28`（112px）
  - **原型 vs 实际渲染**：Figma/Sketch 原型中的文字高度 ≠ 浏览器渲染高度，必须在真实浏览器中验证
  - **优先使用 `justify-between`**：固定行数（如 3 行）时，用 `justify-between` 替代固定 `gap`，让内容自动均匀分布更可靠
  - **Developer 输出前必查**：固定高度容器必须在浏览器中实际验证文字是否完整显示（上下不被截断）
  - **Tester 验证标准**：使用浏览器开发工具检查元素计算后的 `height`，确认内容高度 < 容器高度 × 0.85
  - **Bugfix 诊断清单**：文字被垂直截断（只显示上半部分）→ 不只是调整 `line-height`，还要评估**容器高度是否合理**

## 2026-08-19｜后端 get_db 必须 commit，且 pytest 全绿不能证明持久化

- **来源**：draw-telephone T-013 用户认证功能闭环。后端注册/登录接口 pytest 9 passed 全绿，但真实 uvicorn + SQLite 联调时暴露：注册返回 200 但重复注册也返回 200（应 400）、登录返回 401（用户不存在）。
- **根因**：`src/db/session.py` 的 `get_db()` 只 `yield session; await session.close()`，**没有 commit**。路由层 `db.add()` + `flush()` 的数据在 session close 时被回滚，从未持久化到 SQLite 文件。只有 `scripts/init_db.py` 直接 `session.commit()` 的 seed 数据能查到。
- **为何 pytest 全绿掩盖了 Bug**：测试用 `app.dependency_overrides[get_db]` 注入自定义 `_get_test_db`（也只 yield 无 commit），测试在同一 session 内 add 后立即查询能查到（session 未 close，对象在 identity map 中），所以测试通过。但真实请求中 get_db 在请求结束时 close session，未 commit 的数据被回滚。
- **经验**：FastAPI 的 `get_db` 依赖必须 `yield session; await session.commit()`（成功提交）+ `except: await session.rollback()`（异常回滚），这是 backend-layers.md 模板的标准写法，不能省略 commit。
- **规则**：
  - `get_db()` 必须 `yield session; await session.commit()` + `except: rollback`，禁止只 yield+close
  - 测试的 `dependency_overrides` 注入 session 行为必须与真实 get_db 一致（含 commit/rollback），否则会掩盖 commit 缺陷
  - 后端涉及写操作（注册/创建/提交）的任务，**必须用真实 uvicorn + 真实 SQLite 文件验证数据持久化**，不能只靠 pytest（pytest 的内存库 + 自定义 session 会掩盖 commit 缺失）
  - 验证持久化的方法：真实请求后，用独立脚本查运行时 DB 文件，确认数据落盘且 seed 数据仍 intact
  - pytest 全绿 ≠ 真实联调通过；pytest 验证逻辑正确性，真实联调验证持久化+集成

## 2026-08-31｜沉浸式页面移出共享布局 + SPA query 变化需 key 化重挂载

- **来源**：novel-hub F05 正文阅读页 Mkock 实现。F00 脚手架把 /reader 放在 SharedLayout（AntD 顶部 Header / 移动端 TabBar）下，正文会被应用级导航「污染」，且 URL query 变化（？url=章节）不会触发路由重挂载，导致 react-hooks/set-state-in-effect lint 强制禁止的「在 effect 内同步 setState 重置」反复踩坑。
- **经验**：
  - **沉浸式页面（阅读/播放/全屏）应移出共享布局路由**，页面自带浮层，不继承应用的 Header/TabBar（否则正文/内容被导航污染）。
  - **React Router 中 query 参数变化不会重挂载组件**（同一 path 复用组件实例）；需要「切换即重置整页状态」时，用 key 化包装组件（如 `<ReaderRoute>` 内 `key={bookUrl|chapterUrl}`），天然重置，不必在 effect 里同步 setState（lint 禁）。
  - **Mock 层对「同一 endpoint 需返回不同数据」**：统一为 `mockGet(path, params)` 按参数字段解析（/catalog 按 url、/chapter 按 url），service 透传真实调用同构，切真实时改动最小。
- **规则**：
  - 路由设计时先问「该页面是否沉浸式」：是则移出 SharedLayout，自带过渡/浮层
  - 依赖 URL query 的「内容切换」用 key 化重挂载而不是 effect 内同步 setState
  - Developer 需在输出前自查：沉浸式页面是否仍挂在共享布局下；Tester 验收需验证页面正文无应用级导航残留

## 2026-08-31｜pycore 后端脚手架三连陷阱：.env 的 Path.suffix、APIServer 默认 /health、pytest pythonpath

- **来源**：novel-hub B00 后端基础设施。
- **陷阱 1：`Path(".env").suffix` 是空串**。pycore `ConfigLoader.supports(path)` 若用 `path.suffix.lower() == ".env"` 永远 False，`ConfigManager.load()` 报 `No loader available for file type:`。点前缀文件没有 suffix，必须用 `path.name.lower() == ".env"`（或用 `path.suffix in ("", ".env")`）。凡自定义 loader 判断 `.env`/`.gitignore` 等点文件必踩。
- **陷阱 2：pycore `APIServer` 内建 `/health` 抢占**。`APIServer._create_app()` 硬编码 `@app.get("/health")` 返回 pycore 形状（`status=healthy` + `request_id` 字段）。业务方再用 `include_router(routers)` 注册自己的 `/health` 会因 FastAPI「先注册优先」被忽略 —— 自己写的 health 永远不命中。若业务契约要求不同形状（如 `status: ok`、无 `request_id`），做法：`app = server.app; app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/health"]` 移除内建，再 include 自己的 router。**不要**为此改 pycore 源码。
- **陷阱 3：pytest `pythonpath` 相对 rootdir**。pyproject `[tool.pytest.ini_options] pythonpath = ["backend/src"]` 时，它把 `backend/src` 加进 `sys.path`，于是 `import src` 找的是 `backend/src/src` —— 不对。包 `src` 的父目录是 `backend`，应写 `pythonpath = ["backend"]`。
- **陷阱 4：ruff 的 `-c` 是值选项**。`ruff check backend/src backend/tests -c pyproject.toml` 会把 `-c` 解析成 ruff 自己的 config 参数而非传给命令行后的值，报 `tip: to pass '-c' as a value, use '-- -c'`。ruff 本来就自动读 root `pyproject.toml`，直接 `ruff check <paths>` 即可，不要传 `-c`。（mypy 用 `--config-file` 不冲突，pytest 用 `-c` 正常。）
- **陷阱 5：测试文件重复函数定义覆盖**。编辑测试时若插入新实现又保留旧函数定义（同名 `_sites_path()` 一份 `get_sites_path()` 一份 `Path(__file__).parents[2]` 老写法），后定义覆盖前者导致看似不可能的错误（同进程同一模块依赖正确却能算出错误路径）。诊断「同调用不同结果」时先查是否有同名重复定义。
- **经验**：
  - pycore 后端项目的 loader `supports()` 判 `.env` 用 `path.name`，不用 `suffix`。
  - 业务契约与 pycore 框架内建形状冲突时，在应用层移除内建路由再挂载自己的，而不是改框架。
  - 包根布局 `backend/src/main.py`（包 `src`）时，pytest pythonpath 指 `backend`（包父目录），不是 `backend/src`。
  - ruff/mypy/pytest 各自读配置文件的方式不同；给 ruff 加 `-c` 是已知反模式。
- **规则**：
  - 后端任务真实启动用 `cd backend && PYTHONPATH=.. $PY -m uvicorn src.main:app`（pycore 在项目根，backing/ 启动需把项目根加进 PYTHONPATH）
  - `Path(__file__).resolve().parents[2]` 这类基于文件位置的路径，在 `backend/src/core/config.py` 上是 `backend/`；但测试若也用同公式会因测试文件层级不同指错，应改用 config 暴露的 `get_sites_path()` 之类 API，不要在各处重复推导

## 2026-09-01｜多源聚合抓取：单源异常绝不外抛 + 环境屏蔽时降级验收（MockTransport + fixture + BLOCKED-env）

- **来源**：novel-hub B02 聚合搜索（5 个小说站点全部被企业网络海康 URL 过滤屏蔽）。
- **陷阱 1：Python 3.11 异步上下文管理器的类型来源**。`collections.abc` 在 3.11 没有 `AbstractAsyncContextManager`（3.12 才加）；`typing.AsyncContextManager` 被 ruff UP035 判废弃。正确来源是 `contextlib.AbstractAsyncContextManager`。凡 3.11 项目里标注「返回 async 上下文管理器」的 Callable，统一引 `contextlib`。
- **陷阱 2：属性只有一层转发**。`build_search_url()` 定义在 `SiteConfig`，适配器实例调的却是自己，直接 `self.build_search_url()` 抛 AttributeError。基类要是只代理静态配置属性、没代理动态方法，子类调基类 config 上才有的方法会漏。给 `SiteAdapter` 补 `build_search_url` 方法代理到 `self.config`。凡「配置对象 + 适配器对象」双类结构，动态方法也要代理。
- **陷阱 3：mypy 双重模块名**。`tests/conftest.py` 在 `tests/` 无 `__init__.py` 时同时被解析为顶层 `conftest` 和 `tests.conftest`，mypy 报 `Source file found twice`。测试目录加 `__init__.py` 即可。pytest 不需要它，但 mypy 需要。
- **陷阱 4：鸭子类型注入与强类型构造签名冲突**。`SearchService.__init__(registry: SitesRegistry | None = None)` 测试想注入只带 `enabled_sites/all_sites` 的 fake registry，mypy 报 arg-type。若 registry 依赖是鸭子契约，要么把构造参数类型放宽为 Protocol，要么测试里 `cast(...)`。至少别强行改生产签名迁就测试单独引用的类型。
- **经验**：
  - 多源聚合抓取，单源异常**绝不外抛**：每站 `asyncio.wait_for(adapter.search(), timeout)` 包 try/except，`TimeoutError`/`httpx.TimeoutException` → 该源 `timeout`，其它 `Exception` → `error`，聚合结果恒 200（「整体可用、单源降级」）。前端只认 200 响应 + 每源 status 字段。
  - **外部站点被网络屏蔽的降级验收模式**（可复用）：① 解析逻辑用本地 fixture + `httpx.MockTransport` 单测；② 真实起 uvicorn curl 验证「全 error/timeout、items 空、无 500」退化契约；③ AC 里真实抓取项标 **BLOCKED(env)**（附拦截页 curl 证据）而非 FAIL；④ `tasks.json` 置 `passed` + notes 写环境阻塞，不写 bug-logs、不 bump retry_count；⑤ 真实联调留待网络恢复。这符合 PRD A5-3「外部依赖不可得时 Mock/降级开发」的已确认语义。
  - 拦截页识别只在「0 结果 + 命中拦截词（URL过滤/访问受限/已被拦截/blocked/access denied）」时判该源 error，避免把正常无搜索结果误报成 error。
  - 单条坏数据（缺字段/空标题）在解析层跳过，或在 `BookRead(**item)` 构造处捕获 `ValidationError`，绝不拖垮整源。
- **规则**：
  - 后端逻辑中与外部站点/网络相关的验收，当环境物理不可达时用「fixture 单测 + 退化契约 curl + BLOCKED(env)」，这是合格后退，不是打折扣。
  - 测试目录新增文件若 mypy 参与检查，先确认 `tests/__init__.py` 存在。

## 2026-09-01｜真实启动契约验证前必须先确认端口监听进程是当前代码

- **来源**：novel-hub B03 章节目录。所有 B03 代码落地、门禁全绿后，`curl /api/catalog` 却持续返回 B02 阶段的旧占位 404（「章节目录将在 B03 实现」），浪费多轮排查。
- **根因**：8099 上躺着一个**陈旧 uvicorn 进程**（B02 验证时留下）。新起 uvicorn 因端口被占而绑定失败（未报错、静默换端口或退出），curl 实际打到的仍是旧进程——旧进程加载的是旧代码，自然返回旧占位路由。`netstat -ano | grep :8099` 定位到 PID 后，新旧进程恰好同命令行（同 uvicorn src.main:app --port 8099），仅靠「同命令」判断进程新旧会误导。
- **经验**：
  - 真实启动契约验证前，先确认监听端口上的进程确实执行当前代码：`netstat -ano | grep :PORT` 拿 PID，必要时 `taskkill //F //PID <pid>` 后干净重启，再 curl 断言。**「端口 200 能返回」≠「在验证当前代码」**。
  - HTTP 响应里出现「该阶段不可能存在的旧文案」（占位提示等）是强信号：先查端口进程，别怀疑自己的新代码。
  - Vite 被旧进程占端口时静默 fallback 到 +1（5199→5200），用 `--strictPort` 让占用直接失败暴露，再统一清理。
  - Agent/Tester 会话内 `&` 启动的 dev server 会随主命令退出被回收，需要跨会话长活的后台服务用 Claude Code 的 `run_in_background`（Bash run_in_background）。
  - 前端 `.env` 的 `VITE_USE_MOCK=true`/代理端口通常是「用户门禁验收」演示配置，改环境变量不要动它，用 gitignore 掉的 `.env.development.local` 临时覆盖（`VITE_USE_MOCK=false` + `VITE_BACKEND_PROXY_TARGET=<测试端口>`）。
