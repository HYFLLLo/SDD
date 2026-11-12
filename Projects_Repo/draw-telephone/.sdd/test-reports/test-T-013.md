# 测试报告：T-013 用户认证功能闭环（注册/登录/JWT）

**测试时间**：2026-08-19
**Tester**：Orchestrator 降级执行

## 结果：PASS（自动验证全部通过，待用户门禁验收 UI/UX）

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在登录页输入测试账号密码，点击登录，页面成功跳转到广场页，且刷新后仍保持登录状态 | PASS（自动验证后端链路） | 后端 POST /api/auth/login 真实签发 JWT，Token 存 localStorage（useAuthStore login 写入 token+user），Axios 拦截器自动加 Authorization 头。刷新后 useAuthStore 从 localStorage 读取 token+user 恢复登录态。真实前后端联通验证：通过 Vite proxy 5199 → 后端 8099，login → 200 + 真实 JWT。页面跳转/刷新保持需用户浏览器验收 |
| 2 | 用户在注册页填写用户名/密码/昵称注册，注册成功后自动登录跳转广场页 | PASS（自动验证后端链路） | 后端 POST /api/auth/register 真实签发 JWT + 返回 user，useAuthStore register 写入 token+user 后 navigate('/')。真实联通验证：register via proxy → 200 + 真实 JWT。页面跳转需用户浏览器验收 |
| 3 | 用户名已存在时注册页显示「用户名已存在」错误提示 | PASS | 后端 register 路由捕获 ValueError → 返回 `{"code":400,"message":"用户名已存在","data":null}`。前端 handleRegister catch → message.error('用户名已存在')。真实联通验证：dup via proxy → 400 + 正确消息 |
| 4 | 密码错误时登录页显示「用户名或密码错误」错误提示 | PASS | 后端 login 路由捕获 PermissionError → 返回 `{"code":401,"message":"用户名或密码错误","data":null}`。前端 handleLogin catch → message.error('用户名或密码错误')。真实联通验证：wrongpw via proxy → 401 + 正确消息 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 POST /api/auth/register、POST /api/auth/login 单元/集成测试通过 | PASS | pytest 9 passed（T-012 的 3 + T-013 的 6）。T-013 测试覆盖：注册成功/重复400/登录成功/密码错误401/用户不存在401/Token跨请求持久化 |
| 2 | frontend/src/services/auth.ts 已将 Mock 替换为真实后端 API，VITE_USE_MOCK=false 时不走 Mock 分支 | PASS | auth.ts 本身就是真实 API 调用（`api.post('/auth/login')`），无 Mock 分支。Mock 仅通过 axios-mock-adapter 在 main.tsx 的 `VITE_USE_MOCK===true` 时拦截。VITE_USE_MOCK=false 时请求经 Vite proxy 命中真实后端 |
| 3 | 浏览器能证明请求命中真实后端 /api/auth/login，而非 frontend/src/mocks/* | PASS | 启动后端 8099 + 前端 5199（VITE_USE_MOCK=false），通过 Vite proxy POST /api/auth/login → 200 + 真实 JWT（eyJ... 签名 token，非 mock-token-xxx）。Mock 拦截器未激活，请求穿透到后端 |
| 4 | P09 页面不展示 [Mock] 数据、Mock 账号提示或 Mock-only 文案 | PASS | LoginPage.tsx 已清理：注释从「Mock 阶段」改为「VITE_USE_MOCK=false 时调用真实后端」；占位符从 `mockuser`/`mockpass` 改为「输入用户名」/「输入密码」；移除「Mock 账号」说明 |
| 5 | frontend/vite.config.ts 的 /api 代理指向后端 8099（或通过 VITE_BACKEND_PROXY_TARGET 切 8003） | PASS | vite.config.ts `server.proxy['/api'] = { target: backendTarget, changeOrigin: true }`，backendTarget 默认 `http://localhost:8099`，可通过 VITE_BACKEND_PROXY_TARGET 切 8003 |
| 6 | frontend/.env 的 VITE_API_BASE_URL 用相对路径 /api | PASS | frontend/.env `VITE_API_BASE_URL=/api`（相对路径，经 Vite proxy 转发） |
| 7 | JWT 真实签发与校验，Token 存 localStorage 并在 Axios 拦截器加 Authorization 头 | PASS | 后端 create_access_token 用 jwt.encode（HS256 + settings.jwt_secret + exp 7天）。前端 api.ts 拦截器 `config.headers.Authorization = Bearer ${token}`。测试 test_token_persists_across_requests 验证注册 token 经 get_current_user 解析出真实用户 |
| 8 | $PY -m ruff check backend/src backend/tests 通过 | PASS | All checks passed!（import 排序自动修复 3 处） |
| 9 | $PY -m mypy backend/src backend/tests 通过 | PASS | Success: no issues found in 22 source files（T-012 的 16 + T-013 新增 6） |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build（VITE_USE_MOCK=false） | PASS | built in 494ms（941KB chunk，antd 全量，MVP 可接受） |
| Vite proxy 真实联通 | PASS | 后端 8099 + 前端 5199（VITE_USE_MOCK=false），POST /api/auth/login via proxy → 200 + 真实 JWT；POST /api/auth/register via proxy → 200；dup via proxy → 400 |

## 后端分层实现

按 backend-layers.md 从下往上分层，每层只依赖下层：

| 层 | 文件 | 职责 |
|----|------|------|
| 安全原语 | src/core/security.py | hash_password/verify_password（bcrypt）、create_access_token/decode_token（JWT，纯函数不引入 HTTP 语义） |
| Pydantic 模型 | src/models/user.py | RegisterRequest/LoginRequest（入参）、UserPublic（出参，不含密码）、AuthData（access_token+user） |
| Repository | src/repositories/user.py | get_by_id/get_by_username/create（IntegrityError→ValueError 数据冲突） |
| Service | src/services/user.py | register（ValueError→400 用户名已存在）、login（PermissionError→401 凭据错误，不区分用户不存在与密码错误避免枚举） |
| API 路由 | src/api/routes/auth.py | POST /api/auth/register、POST /api/auth/login，错误用 JSONResponse 显式构造契约体 |
| 依赖注入 | src/api/deps.py | 重构：JWT 原语移至 security.py，get_current_user 用 decode_token（None→401） |
| 入口 | src/main.py | server.include_router(auth_router) |

## 关键修复：get_db 未提交 Bug

**现象**：首次真实联调时，注册返回 200 但重复注册也返回 200（应 400），登录返回 401（用户不存在）。

**根因**：`src/db/session.py` 的 `get_db()` 只 yield + close，**没有 commit**。路由层 add/flush 的数据在 session close 时被回滚，从未持久化到 SQLite 文件。因此：
- 重复注册：DB 中无用户 → 无 IntegrityError → 返回 200（错误）
- 登录：DB 中无用户 → PermissionError → 401（错误）
- 只有 init_db.py 直接 commit 的 seed 用户能登录

**修复**：get_db 改为 `yield session; await session.commit()`（成功提交）+ `except: rollback`（异常回滚），符合 backend-layers.md 模板。

**验证**：修复后真实联调全过——注册 200、重复 400、登录 200、密码错误 401、seed 用户登录 200、apitest 用户持久化到 DB（4 users = 3 seed + 1 new）。

**教训**：pytest 用 dependency_overrides 注入自定义 `_get_test_db`（无 commit），所以 pytest 全绿但**不能证明 get_db 的 commit 逻辑正确**。必须用真实 uvicorn + 真实 SQLite 文件验证持久化。

## 错误响应格式对齐

api-contracts.md 要求错误响应 `{"code":N,"message":"...","data":null}`，但 FastAPI 默认 HTTPException 返回 `{"detail":"..."}`。解决方案：路由层错误分支用 `JSONResponse(status_code=N, content={"code":N,"message":"...","data":None})` 显式构造契约体，成功分支用 pycore `success_response`。未注册全局异常处理器（保持 pycore APIServer 不重写）。

## 测试用例说明

`backend/tests/test_t013_auth.py`（6 测试，内存 SQLite + dependency_overrides）：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_register_success | 注册 → 200，返回 access_token + user（username/nickname/avatar_url=null） | PASS |
| test_register_duplicate | 重复用户名 → 400「用户名已存在」 | PASS |
| test_login_success | 登录 → 200，返回 access_token + user | PASS |
| test_login_wrong_password | 密码错误 → 401「用户名或密码错误」 | PASS |
| test_login_nonexistent_user | 用户不存在 → 401（与密码错误同消息，避免枚举） | PASS |
| test_token_persists_across_requests | 注册 token 经 get_current_user 解析出真实用户 | PASS |

## 真实前后端联通验证

```
后端 8099 + 前端 5199（VITE_USE_MOCK=false）：
- GET /health via backend → 200 healthy
- GET / via frontend → 200 HTML（root div 存在）
- POST /api/auth/login via Vite proxy → 200 + 真实 JWT（eyJ...）
- POST /api/auth/register via proxy → 200 + 真实 JWT
- POST /api/auth/register（重复）via proxy → 400「用户名已存在」
```

## 超出范围发现（不影响当前任务判定）

- **Windows 控制台中文乱码**：curl/httpx 打印的中文 JSON 在 GBK 控制台显示乱码，但数据本身 UTF-8 正确（写入文件验证 nickname='接口测试'）。不影响功能。
- **端口残留**：uvicorn 后台进程未正确退出会占用 8099，导致下次启动 bind 失败。验证前需 taskkill 清理。

**自动验证全部通过。T-013 user_gate=true，需用户门禁验收浏览器 UI 交互（登录跳转/刷新保持登录/注册跳转/错误提示）。**
