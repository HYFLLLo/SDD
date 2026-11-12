# 项目经验

> 当前项目长期有效的经验。  
> Developer / Tester / Bugfix 在任务完成后维护本文件。

---

## Harness 系统经验摘要

新项目开始时，Developer / Tester / Bugfix 需要同时参考：

- 当前项目经验：`.sdd/experience.md`
- 系统级经验：`<Harness 根目录>/memory/harness-experience.md`

---

（项目经验将在开发过程中追加）

---

## 登录态一致性修复：401 拦截器 + store 同步（2026-08-26）

**背景**：用户反馈「点我的主页进不去」。排查发现页面其实已开发（ProfilePage + GET /api/users/me + /me/works 均 200），根因是登录态管理缺陷导致的误导性跳转。

**根因与修复**：

1. **401 拦截器只删 token 不删 user → 状态残留**：原 `api.ts` 401 时仅 `localStorage.removeItem('token')`，没删 `user`，导致 `useAuthStore` 内存态与 localStorage 不一致（头像还在但 token 已失效）。**修复**：401 统一 `removeItem('token') + removeItem('user')`。**How to apply**：任何「清登录态」的动作（登出/401/过期）必须 token 和 user 一起清，保持单一事实源。

2. **401 用 `window.location.href='/login'` 整页刷新 → 丢 SPA 状态**：整页跳转导致路由上下文丢失、白屏闪烁，观感像「点了没反应」。**修复**：401 改为回调注入（`setUnauthorizedHandler`），main.tsx 注入「store.logout() + message.warning('登录已过期')」，跳转交给 `ProtectedRoute` 订阅 store.token 响应式完成（zustand 触发重渲染 → `<Navigate>`）。**How to apply**：SPA 内的鉴权跳转不要用 `window.location.href`（整页刷新），用「清 store 状态 + 路由守卫订阅该状态响应式跳转」；拦截器与 UI 解耦靠回调注入，不在拦截器里直接 import store（避免循环依赖）。

3. **登录/注册接口的 401 ≠ 登录过期**：登录失败（密码错误）后端也返回 401，若拦截器把它当「登录过期」处理会把正在登录的用户踢去登录页。**修复**：拦截器排除 `url.startsWith('/auth/')` 的 401。**How to apply**：401 拦截要区分「业务凭据错误」（auth 接口，交给页面提示）与「会话过期」（受保护接口，清态跳转），用 URL 前缀区分。

4. **ProtectedRoute 从 localStorage 读 token 不响应式**：原 `localStorage.getItem('token')` 只在渲染时读一次，401 清态后不会自动重渲染跳转。**修复**：改 `useAuthStore((s) => s.token)` 订阅。**How to apply**：路由守卫的登录态判断要订阅响应式 store，不要直接读 localStorage（非响应式，状态变了不触发重渲染）。

**验证**：type-check / lint / build 通过；后端无 token 访问 /api/users/me 返回 401 契约格式；前端 /profile 200、后端 /health 200。

---

## T-001 前端工程初始化 + 全局布局 + Mock 基建（2026-08-19）

**结果**：type-check / lint / build 三项通过，dev server 335ms 启动于 :5199，HTTP 200。

**踩坑与经验**：

1. **类型跨文件引用必须显式 import**：`src/types/chains.ts` 和 `src/types/votes.ts` 引用了 `works.ts` 中定义的 `WorkAuthor`，但未 `import type { WorkAuthor } from './works'`，导致 TS2304。barrel 文件 `types/index.ts` 的 `export *` 只对外部消费者生效，模块文件内部仍需显式导入。**How to apply**：任何在独立 type 文件中引用其他文件导出类型的，都要加 `import type`。

2. **axios-mock-adapter 未使用的导入会被 TS6133 + oxlint 双报**：`handler.ts` 导入了 `workNotFoundResponse` 但未在路由中使用。Mock 路由若不返回 404 分支，就别导入 notFound 响应。**How to apply**：Mock handler 只导入实际用到的响应构造器。

3. **Vite 8 + React 19 + TS 6 工具链在 npmmirror 下安装顺畅**：`@vitejs/plugin-react`、`antd@6`、`react-router-dom@7`、`zustand@5` 均无 peer dep 冲突。**How to apply**：后续前端任务可直接复用此依赖组合，无需降级。

---

## T-002 P09 登录/注册页 Mock（2026-08-19）

**结果**：type-check / lint / build 通过，dev server :5199/login HTTP 200。

**踩坑与经验**：

1. **Ant Design 6 组件样式覆盖需用 CSS 类选择器**：直接覆盖 `.ant-input`、`.ant-tabs-tab` 等类名即可生效，无需 ConfigProvider theme。**How to apply**：后续页面用 antd 组件时，写配套 `.css` 文件覆盖 antd 类名实现手账涂鸦本风格。

2. **dev server 端口残留**：上轮 dev server 未关闭会占用 5199，导致下轮 vite 自动切到 5200。验证前需先 `taskkill` 清理残留进程。**How to apply**：每次 dev server 验证前先检查端口占用。

3. **build chunk size 警告非阻塞**：引入 antd 后主 chunk 达 792KB（gzip 261KB），vite 会警告 >500KB。这是 antd 全量引入所致，MVP 阶段可接受，后续可按需引入优化。**How to apply**：不要因 chunk size 警告判 FAIL。

---

## T-009 P07 整链回放页 Mock（含投票）（2026-08-19）

**结果**：type-check / lint / build 通过，dev server :5199/work/work-0001/replay HTTP 200。

**踩坑与经验**：

1. **oxlint react/set-state-in-effect 规则禁止 effect 内同步 setState**：最初用 `playing` 布尔中间态 + effect 内 `setPlaying(false)` 控制回放停止，触发 `react(set-state-in-effect)` 警告。**修复**：移除 `playing` 中间态，回放完成态 `replayDone` 直接由 `revealed >= nodeCount` 派生（render 期计算），effect 只负责 setTimeout 递增 revealed，不再同步 setState 切换标志。**How to apply**：能从已有 state 派生的派生值不要存进 state；effect 只做副作用（定时器/订阅），停止条件用 render 期派生判断，避免 effect 内同步 setState 引发级联渲染。

2. **framer-motion 13 首次使用无障碍**：`package.json` 已声明 `framer-motion ^13.1.0` 但 T-001~T-008 未实际 import。T-009 首次 `import { motion } from 'framer-motion'`，`motion.div` 的 `initial/animate/transition` API 与 v13 文档一致，build 直接通过（943KB chunk 含 framer-motion）。**How to apply**：后续需要动画的页面直接用 framer-motion，无需额外配置。

3. **逐节点渐显的「间隔」用 setTimeout 递增计数实现**：不用 framer-motion 的 staggerChildren（那是同批并行延迟），而是用 `revealed` 计数 + `setTimeout(NODE_INTERVAL)` 逐个 mount 节点，每节点各自 framer-motion 渐显。这样「跳过动画」只需 `setRevealed(nodeCount)` 一次性展开全部。**How to apply**：序列渐显用计数+定时器，跳过/重放操作计数即可。

---

## T-010 P08 个人主页 Mock + 通知铃铛 Mock（2026-08-19）

**结果**：type-check / lint / build 通过，dev server :5199/profile HTTP 200。

**踩坑与经验**：

1. **全局通知铃铛下拉的点击外部关闭用 mousedown 监听 + ref.contains**：在 AppHeader 用 `useRef` 持有下拉容器 ref，`useEffect` 在 open=true 时注册 `document.addEventListener('mousedown', handler)`，handler 判断 `!ref.current.contains(e.target)` 则 setOpen(false)，cleanup 移除监听。**How to apply**：任何「点击外部关闭」的下拉/弹层都用此模式，注意只在 open 时注册监听（避免空跑），cleanup 必须移除。

2. **ProtectedRoute 页面的 dev server 探测仍返回 200**：Vite SPA 对所有路由返回 index.html（200），ProtectedRoute 的鉴权重定向在客户端运行，curl 探测不到重定向。**How to apply**：dev server HTTP 200 只证明路由可达 + 无构建错误，登录态/鉴权需浏览器实际验证，不能仅靠 curl 判 PASS。

3. **Mock 通知已读用本地 state 同步**：readNotifications 成功后直接 `setNotifs(prev => prev.map(...))` 本地标记 read:true，不重新拉列表（Mock 阶段无服务端持久化）。真实联调阶段（T-022）需改为重新拉 GET /api/notifications 或依赖服务端返回。**How to apply**：Mock 阶段乐观更新本地 state，联调阶段按服务端真实语义调整。

---

## T-012 后端基础设施：数据库骨架 + 依赖注入 + 健康检查（2026-08-19）

**结果**：ruff/mypy 通过（16 source files），pytest 3 passed，init_db seed 落盘，uvicorn 启动 /health 200。

**踩坑与经验**：

1. **测试库与运行时业务库必须物理隔离**：测试用 `sqlite+aiosqlite:///:memory:` 独立 engine + `app.dependency_overrides[get_db]` 注入测试 session，每函数建表/销毁。这样 pytest 的 drop_all 不会清空运行时 backend/data/draw_telephone.db 的 seed 数据。**How to apply**：后端测试一律用内存 SQLite + dependency_overrides，禁止复用运行时 engine/session_maker。

2. **FastAPI Depends() 作为参数默认值触发 ruff B008**：`get_current_user(credentials=Depends(security), db=Depends(get_db))` 是 FastAPI 标准模式，但 ruff B008（function-call-in-default-argument）误报。**修复**：pyproject.toml `[tool.ruff.lint.per-file-ignores] "backend/src/api/**/*.py" = ["B008"]`。**How to apply**：所有 FastAPI 路由/依赖文件用 Depends/Query/Header 作默认值的，靠 per-file-ignores 排除 B008，不要改写代码。

3. **mypy 跟踪 import 进入 pycore 报 85 errors**：pycore 内部无类型注解，mypy 默认 follow_imports 会深入检查。**修复**：`[[tool.mypy.overrides]] module=["pycore.*"] follow_imports="skip" ignore_errors=true`。**How to apply**：任何外部框架依赖（非项目业务代码）用 mypy overrides 排除，不纳入项目质量门禁。

4. **JWT exp 用 datetime.datetime.now(datetime.UTC) + timedelta**：Python 3.11 的 `datetime.UTC` 时区常量（3.11+ 新增），比 `datetime.timezone.utc` 更简洁。pyjwt 2.x 的 `jwt.decode` 默认验证 exp。**How to apply**：后端 JWT 签发用 `datetime.datetime.now(datetime.UTC)`，不要用已弃用的 `datetime.utcnow()`。

5. **init_db.py seed 数据与前端 Mock 对齐**：seed 的 chain-0001「戴帽子的猫」6 节点（draw/describe 交替，node-0005 is_ai=True）与前端 Mock works.ts 数据一致，后续联调阶段前端切真实后端时数据形态无缝衔接。**How to apply**：后端 seed 数据要参照前端 Mock 数据结构，保证联调切换时无形态差异。

---

## T-013 用户认证功能闭环（注册/登录/JWT）（2026-08-19）

**结果**：ruff/mypy 通过（22 source files），pytest 9 passed，Vite proxy 真实联通全过，前端 type-check/lint/build 通过。

**踩坑与经验**：

1. **get_db 未提交是隐蔽 Bug——pytest 全绿但真实联调才暴露**：T-012 的 get_db 只 `yield session; await session.close()`，没有 commit。路由层 `db.add()` + `flush()` 的数据在 session close 时被回滚，从未持久化。导致：重复注册返回 200（应 400，因 DB 无用户无 IntegrityError）、登录返回 401（用户不存在）。但 pytest 用 `app.dependency_overrides[get_db]` 注入自定义 `_get_test_db`（也只 yield 无 commit），测试在同一 session 内 add 后立即查询能查到（未 close），所以 pytest 全绿。**修复**：get_db 改为 `yield session; await session.commit()` + `except: rollback`，符合 backend-layers.md 模板。**How to apply**：后端写测试时，dependency_overrides 注入的测试 session 行为必须与真实 get_db 一致（含 commit/rollback）；且必须用真实 uvicorn + 真实 SQLite 文件做联调验证持久化，不能只靠 pytest。这是 T-012 经验「测试库与运行时库物理隔离」的补充——隔离是对的，但隔离也掩盖了 get_db 的 commit 缺陷。

2. **FastAPI HTTPException 返回 {"detail":"..."} 与 api-contracts 的 {"code":N,"message":"...","data":null} 不符**：api-contracts.md 要求错误响应有 code/message/data 三字段，但 FastAPI 默认 HTTPException 序列化为 `{"detail":"..."}`。pycore 的 ErrorHandlerMiddleware 只捕获通用 Exception(500)，不格式化 HTTPException。**解决方案**：路由错误分支不用 HTTPException，改用 `JSONResponse(status_code=N, content={"code":N,"message":"...","data":None})` 显式构造契约体；成功分支用 pycore `success_response`。**How to apply**：所有需要返回 api-contracts 错误格式的路由，错误分支用 JSONResponse 显式构造，不要依赖 HTTPException 的默认序列化。

3. **Service 层用两种异常类型区分 HTTP 状态码**：注册重复(ValueError→400)和登录错误(PermissionError→401)都是业务校验失败，但 HTTP 状态码不同。若用单一 @handle_errors（ValueError→400），登录错误也会变 400。**解决方案**：Service 层 register 抛 ValueError、login 抛 PermissionError，路由层分别 try/except 捕获映射不同状态码。**How to apply**：当同一 Service 的不同方法需要映射不同 HTTP 状态码时，用不同异常类型区分，路由层显式捕获，不用统一 @handle_errors。

4. **登录不区分「用户不存在」与「密码错误」避免用户名枚举**：UserService.login 对用户不存在和密码错误都抛相同的 PermissionError("用户名或密码错误")，不泄露用户名是否注册。**How to apply**：认证接口的错误消息对用户不存在和密码错误保持一致，避免攻击者通过错误消息枚举有效用户名。

5. **JWT 原语放 core/security.py 而非 api/deps.py**：T-012 把 create_access_token/decode_token 放在 api/deps.py（HTTP 层），但 Service 层（非 HTTP）也需要签发 token。若 Service 依赖 api/deps.py 会反向依赖（Service→API）。**重构**：JWT 原语移至 src/core/security.py（纯函数，不引入 HTTP 语义），deps.py 从 security.py 导入，Service 层也可导入。**How to apply**：跨层复用的原语（密码哈希、JWT 签发/解码）放 core/ 层，保持无 HTTP 依赖，API 和 Service 都可导入。

---

## T-014 链创建功能闭环（含房间码生成）（2026-08-19）

**结果**：ruff/mypy 通过（27 source files），pytest 15 passed，Vite proxy 真实联通全过，前端 type-check/lint/build 通过。

**踩坑与经验**：

1. **全局异常处理器统一错误格式——比每路由 JSONResponse 更彻底**：T-013 的解法是路由层错误分支用 JSONResponse 显式构造契约体 `{"code":N,"message":"...","data":null}`。但这覆盖不到 deps.py 的 get_current_user 抛的 401/403（HTTPException）和 Pydantic 请求体校验失败的 422（RequestValidationError）。T-014 在 main.py 注册两个 app 级 `@app.exception_handler`：HTTPException → 契约格式，RequestValidationError → 400。这样所有路由的 HTTPException 和 Pydantic 校验错误都自动转契约格式，无需每个路由单独处理。**How to apply**：当项目要求统一的错误响应格式时，优先用 app 级异常处理器一次性兜底，而不是在每个路由里重复写 JSONResponse 错误分支。注意不重写 pycore 的中间件，只在 app 上注册 exception_handler。

2. **房间码生成排除易混淆字符 + unique 约束 + 冲突重试**：6 位房间码用 `string.ascii_uppercase + string.digits` 后剔除 O/0/I/1/L（易混淆），生成后靠 DB 的 unique 约束检测冲突，IntegrityError 时 rollback 重试最多 10 次。random.choices 标注 `# noqa: S311`（安全场景的随机非密码学用途）。**How to apply**：用户可见的短码（房间码/邀请码）必须排除易混淆字符，靠 DB unique 约束 + 重试保证唯一，不要在应用层先查再插（有竞态）。

3. **Pydantic 请求体校验失败经全局 handler 转 400 而非 422**：FastAPI 默认 Pydantic 校验失败返回 422 + `{"detail":[...]}`，但 api-contracts.md 用 400 表示参数错误。全局 `@app.exception_handler(RequestValidationError)` 把 422 转为 400 + `{"code":400,"message":"参数错误","data":null}`。测试 test_create_chain_invalid_length 预期从 422 改为 400。**How to apply**：当 API 契约规定的参数错误状态码与框架默认不同时（如 400 vs 422），用全局异常处理器统一转换，测试预期要对齐契约码。

4. **datetime 字段序列化为 ISO 字符串**：Chain ORM 模型的 created_at/expires_at 是 DateTime 列，但 ChainRead Pydantic 响应期望字符串。路由层 `_chain_to_read` 用 `chain.created_at.isoformat() if chain.created_at else ""` 转换，而非依赖 Pydantic 的 from_attributes 自动序列化（DateTime→str 不自动）。**How to apply**：ORM DateTime 字段转 API 响应时，显式 `.isoformat()` 转字符串，不要假设 Pydantic from_attributes 会自动处理 datetime→str。

5. **Service 层 prompt_text 的 None 收敛用 assert**：CreateChainRequest 的 prompt_text 是 `str | None`（manual 时必填，ai 时可空）。Service 层 create_chain 对 manual 分支校验非空后赋值，对 ai 分支置空字符串，最后 `assert prompt_text is not None` 让 mypy 收敛类型为 str，再传给期望 str 的 repository。**How to apply**：当 Pydantic 模型字段可空但业务逻辑在某分支后必非空时，用 assert 收敛 mypy 类型，比 `# type: ignore` 更安全（运行时也会校验）。

---

## T-015 AI 起手题生成功能闭环（DeepSeek，fallback 降级）（2026-08-20）

**结果**：ruff/mypy 通过（31 source files），pytest 21 passed，Vite proxy 真实联通全过，前端 type-check/lint/build 通过。真实 DeepSeek 未验收（用户暂未提供 Key）。

**踩坑与经验**：

1. **外部服务 Key 缺失的两种降级语义要区分**：Key 缺失是配置问题（应 503 告知用户，不静默吞错），调用失败是网络/服务问题（应降级到本地 fallback 但仍可用，记日志）。AiService.generate_prompts：Key 缺失 `raise RuntimeError` → 路由层 503；调用失败 `except httpx.HTTPError` → 记日志 + 降级到 FALLBACK_PROMPTS → 200。**How to apply**：外部服务降级时区分「配置缺失」与「调用失败」两种语义，前者返回错误码告知用户，后者降级但保持可用，不要把两者混为一谈。

2. **httpx.AsyncClient 必须 trust_env=False**：development-rules.md 明确要求外部 HTTP 客户端不继承环境变量/代理/证书。`httpx.AsyncClient(trust_env=False, timeout=30.0)` 显式禁用。测试 test_ai_prompt_trust_env_false 用 `inspect.getsource(AiService._call_deepseek)` 断言源码含 `trust_env=False`，这是静态规则校验（无法靠运行时行为验证）。**How to apply**：所有外部 HTTP 调用（DeepSeek/百炼等）用 `httpx.AsyncClient(trust_env=False)`，并用 inspect 源码断言写测试守住这条规则。

3. **patch 实例属性要 patch settings 而非类属性**：AiService 的 `api_key` 在 `__init__` 中从 `settings.deepseek_api_key` 读取赋值为实例属性。测试时 `patch.object(AiService, "api_key")` 失败（实例属性非类属性，AttributeError）。正确做法是 `patch("src.services.ai.settings")` patch 模块级 settings 单例，再设 `mock_settings.deepseek_api_key = "fake-key"`，AiService 构造时读到 mock 值。**How to apply**：当 Service 在 `__init__` 从全局 settings 读配置赋值为实例属性时，测试 mock 要 patch settings 单例而非实例属性。

4. **mock httpx 调用测试不依赖真实 Key**：DeepSeek 调用路径无法用真实 Key 验证（用户未提供），但可用 `patch.object(AiService, "_call_deepseek", new_callable=AsyncMock, return_value=[...])` mock 整个调用方法，验证路由层对返回值的序列化。调用失败降级用 `side_effect=httpx.HTTPError(...)` mock 抛错。这样不依赖真实外部服务也能验证代码路径正确性。**How to apply**：外部服务调用路径用 mock 测试方法本身（而非 mock httpx 网络层），验证业务逻辑对成功/失败返回值的处理；真实联调留到用户提供 Key 后补充。

5. **ruff SIM117 要求合并嵌套 with**：多个 `patch.object` 嵌套 with 触发 SIM117（Use a single with statement）。Python 3.10+ 支持括号多上下文 `with (patch(...), patch(...)):`。**How to apply**：多个 mock patch 用括号合并到一个 with，避免 SIM117，也避免缩进过深。

6. **外部服务配置变更要同步四处**：用户把图像生成从百炼/通义万相换成公司内网海康 MaaS，需同步更新：①`.env`（真实 Key+URL+模型）②`.env.example`（字段名+占位，不写真实值）③`config.py`（Settings 类字段名+默认值）④`tasks.json`（external_services 清单+T-024 description/technicalChecks/notes）。旧字段名 `DASHSCOPE_API_KEY`/`WANX_MODEL`/`QWEN_VL_MODEL` 语义不清（一个 Key 配两个模型），改为清晰的 `IMAGE_*`（文生图）和 `VLM_*`（多模态看图）三组独立配置。**How to apply**：外部服务变更时，.env/.env.example/config.py/tasks.json 四处必须同步，字段名要语义清晰（按用途分组，不要一个 Key 配多模型）。

7. **测试不能依赖 .env 真实配置**：T-015 的 test_ai_prompt_key_missing_returns_503 原本直接调接口验证 503，但用户填了真实 Key 后 .env 的 DEEPSEEK_API_KEY 非空，AiService 不再走 503 分支，测试失败。修复：测试用 `patch("src.services.ai.settings")` mock settings.deepseek_api_key=''，独立验证 Key 缺失分支，不依赖 .env 真实值。**How to apply**：测试外部服务的「配置缺失」分支时，必须 mock 配置为空，不能依赖 .env 真实值（.env 可能随时被填入真实 Key）。

8. **海康 MaaS 兼容 OpenAI /chat/completions 格式**：公司内网 MaaS（maas.hikvision.com.cn/v1）的文本生成接口兼容 OpenAI chat completions 格式（`/chat/completions` + `messages` + `model` + `max_tokens` + `temperature`），响应结构 `choices[0].message.content`。DeepSeek-V4-Flash-0731 模型可做文本题词生成，返回具象但开放的短题词（如「隔岸花灯」「伞下余光」「断线纸鸢」），符合画意接龙漂移设计。**How to apply**：海康 MaaS 文本生成用 OpenAI 兼容格式调用，无需特殊 SDK，httpx 直调即可。

---

## T-016 链查询/加入功能闭环（房间码查询/加入/链大厅详情）（2026-08-20）

**结果**：ruff/mypy 通过（32 source files），pytest 32 passed（T-016 11 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 10 项端点全过。

**踩坑与经验**：

1. **FastAPI 同前缀路径参数路由冲突**：GET /api/chains/{room_code}（6位房间码查询）和 GET /api/chains/{id}（UUID链ID详情）的路径模式都是 `/{param}` 单段，FastAPI 按注册顺序匹配，先注册的先命中，导致后者永远命中前者。解决：给详情加后缀 GET /api/chains/{chain_id}/detail，变成两段路径，与单段的 /{room_code} 模式不同，无冲突。**How to apply**：当两个 GET 端点路径前缀相同、参数都是单段路径参数时，用后缀（如 /detail）区分，不要试图靠参数格式（6位码 vs UUID）让框架自动区分——FastAPI 不做格式推断，只按模式匹配。

2. **SQLite datetime 时区丢失导致比较报错**：models.py 列定义 `DateTime(timezone=True)`，但 SQLite + aiosqlite 读回的 datetime 可能丢失时区信息（offset-naive），而 `datetime.datetime.now(datetime.UTC)` 是 offset-aware，直接比较报 `TypeError: can't compare offset-naive and offset-aware datetimes`。修复：_is_expired 比较前检查 `expires_at.tzinfo is None`，naive 则 `replace(tzinfo=datetime.UTC)` 统一为 aware 再比较。**How to apply**：SQLite 存取 datetime 时不要假设时区信息保留，比较前做防御性时区归一化（naive→attach UTC），避免 naive vs aware 比较报错。这条对 T-017+ 的过期/倒计时逻辑都适用。

3. **进度节点链推导：已建从 DB 取 + 未建按 seq 推导占位**：链创建后只有 seq=0 节点存在，但链大厅页要显示完整 chain_length 个节点的进度链。_build_node_list 遍历 seq 0..chain_length-1，已建节点（node_map.get(seq) 存在）取真实 author，未建节点按 seq 推导 type（_node_type：偶数 draw 奇数 describe）+ author={id:"", nickname:"待接"} 占位。这样前端无需关心哪些节点已建，直接渲染完整进度链。**How to apply**：进度展示类数据，后端推导完整链（已建真实+未建占位）返回，前端只管渲染，不自己补占位逻辑。

4. **Service 层跨表查询用 self.repo.db.execute + select**：_get_member_users 需查 User 表（ChainService 只持有 ChainRepository，无 UserRepository）。不引入 UserRepository 依赖，直接用 `self.repo.db.execute(select(User).where(User.id.in_(user_ids)))` 复用 repo 的 session。注意 import select（ruff F821 未定义名 select）。**How to apply**：Service 层需跨表查询但不想引入新 Repository 时，可复用已有 repo 的 db session 直接写 select 查询，但记得 import select。

5. **错误码语义分层：LookupError→404 / ValueError→403 / PermissionError→403**：join_chain 链不存在抛 LookupError（→404 资源不存在），已满/过期/重复抛 ValueError（→403 禁止操作）；get_chain_detail 链不存在 LookupError（→404），非成员 PermissionError（→403 无权限）。路由层 try/except 按异常类型映射 HTTP 码，语义清晰。**How to apply**：Service 层用不同异常类型区分错误语义（资源不存在 vs 禁止操作 vs 无权限），路由层按异常类型映射 HTTP 码，不要用同一个 ValueError + 字符串判断。

6. **真实联调脚本用 PID 做用户名后缀避免重复运行冲突**：联调脚本重复运行时，注册接口因用户名已存在返回 400（DB 持久化）。用 `SUF = str(os.getpid())` 做用户名后缀（t016creator{SUF}），每次运行 PID 不同保证唯一。注意不能用 random/Date.now（测试环境禁用），PID 是稳定的唯一性来源。**How to apply**：联调脚本注册用户用 PID 或其他稳定唯一后缀，避免重复运行时用户名冲突；这同时验证了 DB 持久化（重复运行报「已存在」证明数据落盘）。

---

## T-017 节点接力功能闭环（防剧透/提交/成员轮转）（2026-08-20）

**结果**：ruff/mypy 通过（37 source files），pytest 46 passed（T-017 14 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 11 项端点全过。

**踩坑与经验**：

1. **路径参数 {id} 语义与前端路由对齐**：api-contracts.md 路径 /api/nodes/{id}/previous 的 {id} 语义上像节点 ID，但前端 RelayPage 从路由 /chain/:id/relay 取的是链 ID，调 getNodePrevious(id)。后端必须接收链 ID（按链 ID 查 current_seq 对应当前节点），而非节点 ID。路由参数命名 {chain_id} 明确语义，路径保持 /api/nodes/{chain_id}/previous 与前端一致。**How to apply**：路径参数语义以前端实际传入为准（看前端路由 + service 调用），不照搬契约字面；后端参数名用语义明确的名（chain_id 而非 id）。

2. **seq=0 起手节点的"上一节点"是起手题**：seq=0 是起手 draw 节点，无 seq=-1 节点。get_previous 在 seq=0 时返回虚拟节点 {node_id:"",seq:-1,type:"describe",content_type:"text",content_text:chain.prompt_text}。前端 isDrawMode=content_type==='text' 为 true（看文字画图），展示起手题。语义一致：起手题是"上一棒"的文字，画师照题画图。**How to apply**：边界节点（seq=0）的"上一节点"用虚拟节点填充（起手题文字），保持前端 isDrawMode 逻辑统一，不特殊处理 seq=0。

3. **成员轮转指派下一位**：提交后创建下一节点时，下一位按成员加入顺序轮转 idx=next_seq%member_count（members 按 joined_at 排序）。成员不足时 author=None（待接，T-024 AI 补位）。PRD 没明确下一位规则，按"成员加入顺序轮转"最符合接力直觉。**How to apply**：接力游戏的"下一位"按成员加入顺序轮转（next_seq % member_count），成员不足时留空待接（AI 补位任务填充）。

4. **Discriminated Union 请求体的 type guard**：submit 路由请求体 SubmitNodeImageRequest|SubmitNodeTextRequest（按 content_type 区分），直接访问 body.content_url 报 mypy union-attr（只有 ImageRequest 有 content_url）。用 isinstance(body, SubmitNodeImageRequest) type guard 分流，mypy 在分支内收敛类型。**How to apply**：Pydantic discriminated union 请求体，路由层用 isinstance type guard 分流字段，不要用 `body.content_type == 'image'` 字符串判断（mypy 不收敛类型）。

5. **测试辅助函数避免重复创建实体**：_create_chain 已创建 seq=0 节点，测试手动 add 第二个 seq=0 导致 get_current_node 的 scalar_one_or_none 报 MultipleResultsFound。加 _mark_seq0_submitted 辅助函数更新已有 seq=0 节点（查询+更新字段）而非新建。**How to apply**：测试构造场景时，若 fixture/辅助函数已创建某实体，用"查询+更新"而非"新建"避免唯一约束/多结果冲突。

6. **测试环境 joined_at 排序稳定性**：测试同事务快速执行，创建者与加入者 ChainMember 的 server_default=func.now() 时间戳可能相同，sort(joined_at) 不稳定，导致成员轮转指派错误。_add_member 显式设 joined_at=utcnow()+1s 保证创建者在前。运行时有真实时间差不会出此问题。**How to apply**：测试涉及按时间排序的轮转逻辑时，显式设置时间戳顺序（+1s），不依赖 DB server_default 的精度（同事务可能相同）。

7. **接力推进的事务原子性**：submit_node 在一个事务内完成：更新当前节点内容+status=submitted → 推进链 current_seq+1（完成时 status=completed+completed_at）→ 创建下一 pending 节点。任一步失败整个回滚，避免链状态不一致（如节点提交了但 current_seq 没推进）。**How to apply**：多步状态变更（提交+推进+创建下一位）在同一 service 方法内，靠 session flush 顺序保证原子性，不手动 commit（依赖 get_db 的事务边界）。

---

## T-018 图片上传功能闭环（PNG 校验/本地存储/静态服务）（2026-08-20）

**结果**：ruff/mypy 通过（41 source files），pytest 52 passed（T-018 6 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 6 项验证全过（上传→访问闭环）。

**踩坑与经验**：

1. **文件上传校验以文件头魔数为准，不信任 content_type**：初版 PNG 校验用「content_type 或魔数任一通过」，空文件 content_type=image/png 误判合法（test_upload_empty_file_400 失败）。改为必须以魔数 `b"\x89PNG\r\n\x1a\n"` 开头，不信任客户端 content_type。原因：content_type 可伪造（image/png 声明但实际 JPEG），空文件/损坏/伪装均能绕过 content_type 校验。魔数校验确保数据确实是 PNG。**How to apply**：文件上传校验用文件头魔数（magic bytes）而非 content_type，content_type 仅记日志排查；空文件/损坏文件用魔数校验天然拒绝。

2. **FastAPI UploadFile 需要 python-multipart 依赖**：测试首次运行报 `RuntimeError: Form data requires "python-multipart"`。FastAPI 处理 multipart/form-data（UploadFile）需要 python-multipart，但 FastAPI 不强制安装（运行时才报错）。pyproject.toml dependencies 需显式声明。**How to apply**：后端用 UploadFile（multipart/form-data）时，pyproject.toml dependencies 加 python-multipart，否则运行时才报错（测试收集阶段就崩）。

3. **UUID 文件名不保留原始文件名**：存储文件名 = uuid4().hex + ".png"，不保留原始 filename。原因：原始文件名可能含中文/特殊字符/路径穿越（../），UUID 防冲突+防猜测+防路径穿越。url 返回 /uploads/{uuid}.png，前端 img src 直接用。**How to apply**：用户上传文件用 UUID 重命名存储，不保留原始文件名（安全：防路径穿越/防冲突/防猜测），原始文件名仅记日志。

4. **静态文件服务 + Vite proxy 双层配置**：后端 app.mount("/uploads", StaticFiles(directory=upload_path)) 提供 /uploads/* 静态访问；前端 Vite proxy 新增 /uploads → 8099，使开发环境 img src="/uploads/xxx.png" 经 Vite 代理命中后端。生产环境前端直接访问后端 /uploads。**How to apply**：上传文件访问用 StaticFiles 挂载 + Vite proxy 代理（开发环境），前端用相对路径 /uploads/xxx.png（不写后端 host:port），开发/生产环境统一。

5. **测试用 monkeypatch 临时上传目录避免污染**：测试上传文件会写入真实 uploads/ 目录污染。用 monkeypatch.setattr(settings, "upload_dir", str(tmp_path/uploads)) 指向临时目录，测试结束自动清理。settings.upload_path 属性基于 upload_dir 解析，monkeypatch 后自动指向临时目录。**How to apply**：涉及文件写入的测试，用 monkeypatch + tmp_path 指向临时目录，不污染真实文件系统；配置属性（如 upload_path）基于可变字段（upload_dir）解析时，monkeypatch 该字段即可。

6. **联调脚本生成最小合法 PNG**：真实联调需要上传真实 PNG 文件。用 struct + zlib 生成最小合法 PNG（2x2 像素，IHDR+IDAT+IEND 三段 + CRC），不依赖外部图片文件。上传后断言下载内容 == 上传内容，验证上传→访问闭环。**How to apply**：联调脚本需要二进制文件（图片等）时，用代码生成最小合法文件（struct+zlib 拼 PNG），不依赖外部文件；上传后断言下载内容一致验证闭环。

---

## T-019 WebSocket 实时围观功能闭环（WS 鉴权/连接管理/广播/notify）（2026-08-20）

**结果**：ruff/mypy 通过（43 source files），pytest 62 passed（T-019 10 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 8 项验证全过（WS 全链路）。

**踩坑与经验**：

1. **WebSocket 鉴权用 query param token（浏览器 WS 不能设 header）**：`get_current_user` 用 HTTPBearer 从 Authorization header 取 token，但浏览器 WebSocket API 不能设自定义 header。WS 端点用 `?token=JWT` query param + `decode_token` 复用（src.core.security）。无效/缺失 → accept + send error 事件 + close(4401)。前端 ws.ts 从 useAuthStore 取 token 拼 URL。**How to apply**：WebSocket 鉴权用 query param token（不用 header），复用 decode_token 验签；鉴权失败先 accept 再 send error + close（客户端能收到 error 消息再感知关闭）。

2. **Notify 广播路由层触发（service 不感知 WS，分层约束）**：submit 后需触发 WS notify 广播，但 service 层只应依赖 repository（不依赖 WS）。方案：submit 路由调完 service.submit_node 成功后，路由层据返回值 chain_status/next_seq 触发 ws_manager.broadcast_notify。ws_manager 是全局单例，路由层 + WS 端点共享同一连接池。**How to apply**：WS 广播触发放路由层（service 返回值含足够信息：chain_status/next_seq），service 层不依赖 WS 模块；广播器是全局单例，路由层和 WS 端点共享。

3. **WS 循环内用独立 session（不能持有请求级 Depends session）**：WS 端点用 `async with async_session_maker() as db` 在 stroke 推送时查 DB 校验当前节点责任人。不能用 Depends(get_db)（请求级 session 在 WS 长连接里会过期/泄漏）。每次 stroke 推送开独立 session 查 chain+current_node，校验 node.author_id==user_id。**How to apply**：WebSocket 端点内查 DB 用独立 async_session_maker() session（每次操作开新 session），不用 Depends(get_db)（请求级 session 不适合长连接）。

4. **同步 WS 测试的阻塞问题**：初版用 starlette TestClient 的 websocket_connect（同步 WS）测广播 + 非责任人推送，receive_json 会阻塞死等（同步 WS 无超时，"不应收到消息"的场景无法测）。改为：鉴权/订阅/断开用 TestClient 同步 WS（有消息场景），广播逻辑用 ConnectionManager 单元测试（MagicMock(spec=WebSocket)，不涉及真实连接）。分离关注点：端点行为用集成测试，广播逻辑用单元测试。**How to apply**：同步 WS 测试只测"有消息"的场景（鉴权/订阅/断开）；广播逻辑/无消息场景用单元测试（mock WebSocket），避免 receive_json 阻塞死等。

5. **WS 测试 token 用 create_access_token 直接生成（不依赖 DB 注册）**：初版用 TestClient HTTP 注册拿 token，但运行时 SQLite 文件库数据持久化，重跑用户名冲突 400。WS 端点 decode_token 只验签不查 DB，token 生成不需 DB。改用 `create_access_token(str(uuid4()), 'wstester')` 直接生成有效 JWT。**How to apply**：WS 鉴权测试若端点只验签不查 DB，用 create_access_token 直接生成 token（不需注册用户），避免 DB 持久化导致的用户名冲突。

6. **MagicMock 是 Any 子类型，不需 type: ignore**：测试用 MagicMock(spec=WebSocket) 注入 ConnectionManager 的 set[WebSocket]，初版加 `# type: ignore[arg-type]`，但 mypy 报 unused-ignore（MagicMock 是 Any，set[WebSocket].add(Any) 不报 arg-type）。删掉所有 type: ignore。**How to apply**：unittest.mock.MagicMock 在 mypy 里是 Any 子类型，注入强类型容器（set[WebSocket]）不需 type: ignore；先不加 ignore，mypy 报错再加（避免 unused-ignore）。

7. **前端 stroke 推送节流（避免 WS flooding）**：P05 作画时 pointermove 高频触发（每秒数十次），每次推送 stroke 会 flooding WS。用 200ms 间隔节流（Date.now() - lastFlush < 200 跳过），平衡实时性与性能。**How to apply**：前端高频事件（绘画 pointermove）推送 WS 时节流（200ms 间隔），避免 flooding；节流间隔按实时性需求调（围观笔迹 200ms 够流畅）。

---

## T-020 作品详情功能闭环（只读全链/游客可访问/thumb_url/like_count）（2026-08-20）

**结果**：ruff/mypy 通过（38 source files），pytest 72 passed（T-020 10 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 3 项验证全过（广场列表 + 作品详情 + 404）。

**踩坑与经验**：

1. **只读公开接口不加 get_current_user（游客可访问）**：作品广场 + 详情是公开只读功能，GET /api/works 和 GET /api/works/{id} 不加 get_current_user 依赖。任何访客可浏览已完成作品（符合公开广场语义）。测试验证无 token 仍 200。**How to apply**：只读公开接口（广场列表/作品详情）不加鉴权依赖（无 get_current_user），游客可访问；需鉴权的写操作（建链/接力/投票）才加 get_current_user。

2. **只读全链只展示 completed 链（未完成返回 404）**：作品详情要求链已完成（status=completed），未完成链不出现在广场列表，查详情也返回 404「作品不存在」。list_completed_chains 查询过滤 status=completed，get_work_detail 校验 chain.status != completed → LookupError → 404。**How to apply**：只读展示功能（作品广场/详情）只展示已完成数据（status=completed），未完成的不展示（列表过滤 + 详情 404），避免暴露半成品。

3. **thumb_url 取首个 draw 节点 content_url（链缩略图）**：广场卡片缩略图取链中第一个 draw 节点（seq 最小）的 content_url。get_thumb_url 查 Node.type=draw + content_url IS NOT NULL 按 seq 升序取首条，无则返回空字符串（前端 fallback 首字占位）。**How to apply**：列表缩略图取链/集合中第一个图片节点（按 seq 升序）的 content_url，无图片时返回空字符串让前端 fallback 占位。

4. **AI 补位节点 author_id=None（nickname fallback 到 author_label）**：模型设计 AI 补位节点 author_id=None（无真实用户）。get_work_detail 构建节点时，author_id 为空则 nickname fallback 到 node.author_label（AI 补位时存"AI"）。get_node_authors 批量查 User，author_map 不含 None key（只查有 author_id 的），自然 fallback。**How to apply**：AI 补位/匿名节点 author_id=None，构建响应时 author_id 为空则 nickname fallback 到 author_label 字段（节点表存的标签），不强行查 User。

5. **most_liked 排序用 Vote 子查询 + outerjoin + coalesce**：list_completed_chains 的 most_liked 排序用 Vote 子查询统计每链点赞数，outerjoin（无点赞的链也有记录）+ coalesce(cnt, 0)（无点赞返回 0）降序。latest（默认）按 created_at 降序。不支持的 sort 降级为 latest。**How to apply**：按关联表计数排序（如按点赞数）用子查询统计 + outerjoin（保证无关联的记录也在）+ coalesce（无关联返回 0），不支持的排序模式降级为默认（latest）。

6. **like_count 查 Vote 表 count（功能未实现前返回 0）**：like_count 查 Vote 表 count（T-021 投票功能实现后才有数据）。当前无 Vote 记录返回 0。count_likes 用 select(func.count()).select_from(Vote).where(Vote.chain_id == chain_id)。**How to apply**：依赖后续任务的字段（如 like_count 依赖 T-021 投票），当前查关联表 count（无数据返回 0），不阻塞当前任务；后续任务实现后自然有数据。

---

## T-021 投票功能闭环（三维度投票/唯一约束/权限校验/结果统计）（2026-08-20）

**结果**：ruff/mypy 通过（42 source files），pytest 82 passed（T-021 10 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 12 项验证全过（完整投票流程）。

**踩坑与经验**：

1. **403 统一语义不区分原因（避免泄露状态）**：链未完成/非成员/已投过 → 都返回 403「链未完成或无权投票」，不区分原因。契约只定义这一个 403 message。原因：不告诉非成员"链已完成但你不该投"（泄露链状态），只说"无权"。PermissionError 在 service 层统一抛此 message。**How to apply**：权限/状态校验失败的 403 用统一 message（不区分"未完成/非成员/已操作"），避免通过响应差异泄露内部状态；契约只定义一个 403 message 时严格遵循。

2. **唯一约束 = 每人每维度一票（DB 层兜底 + service 预检）**：Vote 表 uq_vote_chain_user_dim(chain_id,user_id,dimension) 唯一约束。create_votes 批量插入时该用户该维度已投过 → IntegrityError → rollback → raise ValueError。service 层先用 has_voted 预检（任一维度投过→403），IntegrityError 是并发兜底。**How to apply**：唯一性约束用 DB 唯一索引兜底 + service 层预检（预检给清晰错误，DB 兜底防并发）；批量插入捕获 IntegrityError → rollback → raise 业务异常。

3. **三维度齐全校验用 set 比较**：submit_votes 校验 set(dimension)=={most_drift,best_draw,best_describe}，缺维度或重复维度 → 400。用 set 比较一次性校验"恰好三维度各一个"（缺维度/多维度/重复维度都 fail）。**How to apply**：枚举集合校验用 set(dims)==EXPECTED_SET（一次比较覆盖缺/多/重复），比逐个 if 清晰。

4. **投票结果 target_author fallback（AI 节点 author_id=None）**：count_by_chain 只返回 target_node_id 无 author。get_result 批量查 Node 取 author_id+author_label，再批量查 User。author_id 为空（AI 补位节点）时 nickname fallback 到 node.author_label（与 T-020 作品详情一致）。**How to apply**：统计查询不含关联实体时，先批量查关联（Node 取 author_id+label），再批量查用户，author_id 空时 fallback 到 label 字段（AI/匿名节点）。

5. **路由前缀共享（多 router 同 prefix 不冲突）**：votes.py 用 prefix=/api/chains，与 chains.py 共享前缀。FastAPI 允许多 router 共享前缀（按 tags 区分），只要路径不重叠（chains.py 有 //{room_code}/{id}/join/{id}/detail，votes.py 有 /{id}/votes//{id}/votes/result）。**How to apply**：子资源路由（如 /api/chains/{id}/votes）可独立 router 文件共享父资源前缀（/api/chains），路径不重叠即可，按 tags 区分文档分组。

6. **投票测试构造 completed 链需全部节点 submitted**：测试投票需链 completed + 全部节点 submitted + 成员。复用 T-020 的 _create_completed_chain 辅助（构造 completed 链 + 4 节点 submitted + 创建者成员）。token 用 create_access_token(user.id, user.nickname)（get_current_user 查 DB 验证用户存在，用户须先建）。**How to apply**：投票/权限测试构造 completed 链（status=completed + 全部节点 status=submitted + ChainMember），token 生成须用户已入 DB（get_current_user 查 DB 验证）。

---

## T-022 通知功能闭环（2026-08-20）

**背景**：实现站内通知（your_turn/node_submitted/chain_done），节点提交/链完成时生成通知，用户顶部铃铛看列表、标记已读。前端 AppHeader 已接入真实 API，后端补通知分层 + submit 路由层通知生成。

**结果**：ruff/mypy 通过（46 source files），pytest 92 passed（T-022 10 测试全过无回归），后端 8099 真实联调 13 项验证全过（完整通知闭环：提交→生成通知→列表→标记已读→链完成 chain_done）。

**踩坑与经验**：

1. **通知生成放路由层不放 service 层（分层约束）**：通知生成需 chain 成员列表+下一位责任人，与 T-019 WS notify 同位置同语义。放路由层（nodes.py submit 路由），service 层（NodeService）不感知通知模块（不引入 NotificationRepository），保持分层约束。路由层用 ChainRepository.get_members 查成员 + NotificationRepository 写通知。**How to apply**：跨模块副作用（通知/WS/日志）放路由层（与 HTTP 请求同生命周期，可访问 DB session + 鉴权用户 + 关联数据），service 层只做纯业务逻辑（不感知 HTTP/外部模块）；service 返回值补足路由层所需信息（如 next_author_id）。

2. **DB 通知持久化 + WS 实时推送双轨（不替代）**：WS notify（T-019）在线即时推送（不保证送达，离线丢）；DB 通知（T-022）持久化到 Notification 表（离线用户登录后 GET /api/notifications 可见）。两者同位置同语义（submit 路由层），互不替代。**How to apply**：实时通知双轨——WS 推即时感知（在线用户），DB 持久化兜底（离线用户登录可见）；两者同位置触发，WS 不保证送达故 DB 必须持久化。

3. **mark_read 防越权用 WHERE 子句过滤（不靠应用层校验）**：UPDATE Notification SET read=True WHERE id IN (...) AND user_id==current_user.id AND read.is_(False)。WHERE 带 user_id 过滤，用户无法标记他人通知（即使传入他人 notification_id，rowcount=0）。不靠应用层先查后改（有 TOCTOU 风险）。**How to apply**：批量更新防越权用 SQL WHERE user_id 过滤（一条 UPDATE 同时校验所有权+更新），不靠应用层先查所有权再改（TOCTOU + 多查询）；返回 rowcount 告知实际改了几条。

4. **get_db 自动 commit（路由层不显式 commit）**：src/db/session.py get_db 在 yield 后 await session.commit()（成功提交/异常 rollback）。路由层通知生成只需 add/flush，不需显式 commit，与 NodeService 内部只 flush 不 commit 一致。**How to apply**：FastAPI 依赖注入的 get_db 若自动 commit（yield 后 commit），路由层/service 层只需 add/flush（不显式 commit），commit 由依赖统一处理；异常时依赖自动 rollback（事务原子性）。

5. **测试轮转稳定性 joined_at 显式设值（同事务时间戳相同）**：测试环境同事务快速执行，ChainMember server_default=func.now() 时间戳可能相同，导致 members.sort(key=joined_at) 排序不稳定，轮转 idx=seq%member_count 取错人 → next_author_id 错位（your_turn 通知发错人）。test_t017 同款问题。解法：extra_members 显式设 joined_at=now+(i+1)秒，保证创建者在前、后续成员按加入顺序在后。**How to apply**：测试构造按时间排序的成员列表时，显式设 joined_at 递增（now+i 秒），不靠 server_default=func.now()（同事务时间戳相同致排序不稳定）；运行时无此问题（真实加入有时间差）。

6. **httpx AsyncClient 块外用 client 报 RuntimeError**：test_mark_read_success 的 resp2（第二次 GET）在 `async with AsyncClient` 块外，块退出 client 关闭后 resp2 用它报 "Cannot send a request, as the client has been closed"。解法：所有请求移入块内（post 后、退出前）。**How to apply**：httpx AsyncClient 用 `async with` 上下文管理器时，所有 client.get/post 必须在块内（块退出即关闭连接）；块外的请求会 RuntimeError，需移入块内或新建 client。

---

## T-023 个人资料/我的作品功能闭环（2026-08-20）

**背景**：实现个人主页 GET /api/users/me（资料+参与/创建统计）+ GET /api/users/me/works（我的作品列表含 role/status/thumb_url）。前端 P08 ProfilePage 已接入真实 API，后端补 users 分层。

**结果**：ruff/mypy 通过（47 source files），pytest 103 passed（T-023 11 测试全过无回归），前端 type-check/lint/build 通过，后端 8099 真实联调 11 项验证全过。

**踩坑与经验**：

1. **list_my_works 范围含 in_progress（区别于广场只 completed）**：广场 GET /api/works 只查 completed 链；个人主页 GET /api/users/me/works 查用户参与/创建的所有链（含 in_progress+completed）。前端 MyWorkCard 有"进行中"label，期望显示用户参与的所有链。**How to apply**：列表查询范围按场景定——广场（公开浏览）只 completed；个人主页（我的活动）含所有状态；不加 status 过滤即含全部。

2. **OR + distinct 去重（创建者既是 creator 又是 member）**：用户参与（ChainMember.user_id==）OR 创建（Chain.creator_id==）可能重叠（创建者也是成员）。select(Chain).where(creator_id==user_id | id.in_(member_chain_ids)).distinct() 去重，避免创建者链出现两次。**How to apply**：OR 查询涉及重叠集合时用 .distinct() 去重（创建者同时是成员会导致同链出现两次）；子查询 member_chain_ids + OR creator_id 覆盖两种归属。

3. **select(Chain.distinct()) vs select(Chain).distinct()**：初版用 select(Chain.distinct())，mypy 报 "type[Chain] has no attribute distinct"（distinct 不是 ORM 类的类方法）。正确写法是 select(Chain).where(...).distinct()（Query 对象的 distinct() 方法）。**How to apply**：SQLAlchemy 2.0 去重用 select(Entity).where(...).distinct()（Query.distinct() 方法），不是 Entity.distinct()（类方法不存在）；mypy 会报 attr-defined。

4. **datetime→str 用 isoformat（service 层转换，不靠 Pydantic 自动）**：ORM 的 created_at 是 datetime 对象，Pydantic 模型声明 str。service 层构造 dict 时手动 .isoformat() 转 str。初版直接传 datetime，Pydantic model_validate 报 ValidationError（string_type）。**How to apply**：ORM datetime 字段转响应时，service 层构造 dict 用 .isoformat() if x else ""（与 T-020 WorkService 一致），不靠 Pydantic 自动转换（datetime→str 自动转换格式不可控，且 model_validate 严格类型校验会报错）。

5. **UserService 构造函数多 repo 可选注入**：__init__(self, repo, work_repo=None)。auth 路由 register/login 只需 user_repo（传1参数）；users 路由 get_me/get_my_works 需查 thumb_url（传 user_repo + work_repo）。work_repo 可选保持 auth 路由兼容（不破坏现有 register/login 调用）。**How to apply**：service 类被多路由复用但所需 repo 不同时，构造函数把非必需 repo 设可选默认 None（保持旧调用兼容）；需要时路由层传全，不需要时传部分。

6. **thumb_url 复用已有 repository 方法（N+1 可接受）**：list_my_works 逐个 chain 调 work_repo.get_thumb_url（N+1 查询）。链数有限（用户参与/创建的链数有限），N+1 可接受，MVP 简单清晰。若需优化可批量查所有 chain 的首个 draw 节点。**How to apply**：列表查询的关联字段（如 thumb_url）优先复用已有 repository 方法（get_thumb_url），N+1 在结果集有限时可接受（个人主页链数有限）；不必过早优化批量查询。

---

## T-024 AI 补位定时任务功能闭环（2026-08-20）

**背景**：实现 APScheduler 每小时扫描 24h 未提交 pending 节点 → 调海康 MaaS 生成内容（draw 调 Qwen-Image 文生图 / describe 调 Qwen3.6 VLM 看图）→ 写节点 is_ai=true + status=ai_filled → 推进链 + 建下一节点 + notify 下一位；7 天未完成链标记 expired + 通知成员。

**结果**：ruff/mypy 通过（49 source files），pytest 113 passed（T-024 10 测试 + 全量无回归），前端 type-check/lint 通过，真实联调 draw/describe 双节点 AI 补位全过（调真实海康 MaaS）。

**踩坑与经验**：

1. **MaaS 返回格式实现前先探测（不靠文档猜）**：海康 MaaS 各模型返回格式不一致，实现前先发测试请求探测：Qwen-Image POST /images/generations → 200 + `data[0].url`（MaaS 存储 URL）；Qwen3.6 VLM POST /chat/completions → 200 + `choices[0].message.content`。按实际格式解析，不靠文档猜测。**How to apply**：对接外部 AI 服务前，先用 curl/httpx 发一个最小测试请求看真实返回结构（字段名、嵌套层级、URL vs base64），再写解析代码；不靠文档猜测字段名（文档常滞后或不准）。

2. **VLM 看图远程 URL 受限需降级（本地 base64 优先 + 纯文本兜底）**：draw 节点生成的 MaaS 图片 URL 下载受限（返回 36 bytes 错误页，VLM 无法访问远程 URL）。解法：_fetch_image_base64 本地 /uploads/ 文件直接读 base64 传 VLM（真实看图），远程 URL 尝试下载（>1000 bytes 才用，过滤错误页），下载失败降级纯文本续写（VLM 生成描述性文字兜底）。**How to apply**：VLM 看图优先用本地文件 base64（可控可访问），远程 URL 下载需校验返回体大小（>1000 bytes 才算真图，否则是错误页），下载失败降级纯文本续写保证闭环不中断；不假设 VLM 能直接访问任意远程 URL。

3. **定时任务独立 session（不持有请求级 session）**：APScheduler 定时任务不持有请求级 session，用 async_session_maker() 独立 session（与 T-019 WS stroke 校验同模式）。_ai_fill_job 内 try/commit/rollback，异常不中断 scheduler（记日志下次扫描重试）。**How to apply**：定时任务/WS 循环等非请求级上下文用 async_session_maker() 独立 session（不依赖 get_db 依赖注入），任务内自行 commit/rollback；异常 catch 记日志不抛（防止 scheduler 崩溃），下次执行重试。

4. **补位失败不中断（单节点失败跳过，下次扫描重试）**：单个节点补位失败（MaaS 调用失败抛 RuntimeError）记日志跳过，不中断整个扫描。scan_and_fill 返回 {filled, expired, errors} 统计。**How to apply**：批量扫描任务（定时补位/批量处理）单条失败 catch 记日志跳过，不抛异常中断整批；返回 {成功数, 失败数} 统计；失败项下次扫描自然重试（pending 节点仍 pending）。

5. **补位通知复用 submit 语义（service 层直接用 repo，不调路由）**：AI 补位后通知与人工 submit 同语义——链完成→成员 chain_done；否则→下一位 your_turn + 成员 node_submitted。抽到 AiFillService._notify_chain_event（service 层直接用 NotificationRepository，不调 nodes.py 路由）。**How to apply**：定时任务/后台任务的副作用（通知/状态变更）在 service 层直接用 repository 实现（不调 HTTP 路由，路由层是请求入口不是业务逻辑入口）；通知语义与对应人工操作（submit）保持一致（your_turn/node_submitted/chain_done）。

6. **datetime tz 比较需统一 aware（_is_node_timeout 容错 naive）**：节点 created_at 可能是 naive datetime（SQLite 存储无 tz）。_is_node_timeout/_is_chain_expired 比较 created_at + timeout < now 时，now 用 datetime.now(datetime.UTC) 是 aware，naive + aware 比较报错。解法：created = node.created_at; if created.tzinfo is None: created = created.replace(tzinfo=datetime.UTC)（容错补 tz）。**How to apply**：SQLite datetime 字段无 tz，与 aware datetime 比较前先容错补 tz（if x.tzinfo is None: x = x.replace(tzinfo=UTC)）；不要假设 ORM 返回的 datetime 都是 aware。

---

## T-025 E2E 回归验证 + 启动文档（2026-08-20）

**背景**：最终回归任务，全系统 E2E 真实联调（注册→创建链→邀请→接力→AI补位→回放→投票→分享）+ 输出 docs/startup.md。不替代各功能首次联调，只做跨模块链路验证。

**结果**：ruff/mypy 通过（49 source files），pytest 113 passed 无回归，前端 type-check/lint 通过，E2E 33 步真实联调全过（跨 7 模块 + AI 补位真实 MaaS 复验），docs/startup.md 输出。

**踩坑与经验**：

1. **E2E 联调用脚本直连后端 API（不经前端，验证后端契约）**：E2E 用 curl 直连后端 8099 跑全流程（注册/建链/接力/投票/通知/个人主页/AI补位），验证后端 API 契约 + 跨模块链路。前端 UI 各页面在对应任务（T-013~T-024）已分别联调。**How to apply**：E2E 回归用脚本直连后端 API（curl/httpx）验证跨模块链路 + 后端契约，比经前端点击更可复现可自动化；前端 UI 联调在各功能任务首次联调时做，E2E 不重复。

2. **nodes 路由路径参数是 chain_id 不是 node_id（设计决策）**：GET /api/nodes/{id}/previous 和 POST /api/nodes/{id}/submit 的 {id} 实际是 chain_id（路由内调 service.get_previous(chain_id, user)）。前端 RelayPage 从 URL /chain/:id/relay 取 chain_id 传给 nodes API。E2E 初次用 node_id 调用 404，改用 chain_id 通过。**How to apply**：REST 路径参数命名要反映实际语义——接力页上下文是链，用 chain_id 定位当前节点（service 内按 current_seq 查当前 pending 节点）比用 node_id 更自然；路径参数命名 {id} 有歧义时，文档/注释必须写明实际是 chain_id 还是 node_id。

3. **detail vs works 节点结构差异（按场景裁剪字段）**：GET /api/chains/{id}/detail（链大厅）返回进度节点链，节点无 content（防剧透+进度展示，只看 seq/type/author/is_ai）；GET /api/works/{id}（作品详情）返回完整内容链，节点含 content（已完成链可看全链）。验证节点内容用 works API；未完成链 works 返回 None（广场只 completed）。**How to apply**：同一实体（Node）按场景返回不同字段子集——进度展示场景裁剪 content（防剧透+减负载），内容查看场景返回全字段；列表查询（广场）只查 completed，详情查询按场景定状态过滤。

4. **Windows curl 单引号 JSON 转义问题（用文件传 body）**：Windows Git Bash 下 `curl -d '{"k":"中文"}'` 单引号内中文/特殊字符会被转义致 "error parsing body"。解法：JSON body 写文件 `curl -d @file.json`。**How to apply**：Windows Git Bash 联调脚本传 JSON body 用文件（cat > file.json << 'EOF' ... EOF + curl -d @file.json），不用单引号内联 JSON（中文/特殊字符转义问题）；Linux/Mac 无此问题。

5. **AI 补位跨任务回归（E2E 中复验 T-024）**：E2E 中复验 AI 补位：建链2 + seq=0 节点 created_at 改 25h 前 + 手动触发 scan_and_fill → 调真实 MaaS Qwen-Image → is_ai=True + status=ai_filled + 链推进。与 T-024 单独联调结果一致。**How to apply**：E2E 回归对涉及外部服务的功能（AI 补位）也要复验真实调用（不只单元测试 mock），确认跨任务集成无回归；手动触发定时任务（调 scan_and_fill）验证真实 MaaS 调用。
