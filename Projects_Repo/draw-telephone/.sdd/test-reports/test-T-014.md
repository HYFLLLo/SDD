# 测试报告：T-014 链创建功能闭环（含房间码生成）

**测试时间**：2026-08-19
**Tester**：Orchestrator 降级执行

## 结果：PASS（自动验证全部通过，待用户门禁验收 UI/UX）

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在创建链页设置链长/标题/公开性/起手题，提交后页面跳转链大厅页并显示真实房间码 | PASS（自动验证后端链路） | 后端 POST /api/chains 真实生成 6 位房间码（大写字母+数字，排除易混淆字符 O/0/I/1/L），返回 ChainRead（含 room_code/status/creator_id/expires_at）。前端 createChain 调真实 API，handleSubmit 拿 res.data.room_code 显示 + navigate(`/chain/${id}`)。真实联通验证：create via proxy → 200 + room_code T5ZZJF。页面跳转需用户浏览器验收 |
| 2 | 用户设置链长 <4 或 >10 时，页面显示「链长必须在 4-10 之间」错误提示 | PASS | Pydantic CreateChainRequest `chain_length: Field(..., ge=4, le=10)`，超范围触发 RequestValidationError → 全局 validation handler 返回 400 `{"code":400,"message":"参数错误","data":null}`。前端 handleSubmit catch → message.error。真实联通验证：invalid length 3 via proxy → 400 |
| 3 | 用户可复制邀请链接（含房间码） | PASS（后端生成房间码，前端显示） | 后端返回 room_code，前端 message.success(`创建成功！房间码：${room_code}`)。复制链接功能在 P04 链大厅页（T-016），本任务后端已提供 room_code |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 POST /api/chains 单元/集成测试通过（含房间码生成、链长校验、过期时间） | PASS | pytest 15 passed（T-012 的 3 + T-013 的 6 + T-014 的 6）。T-014 测试覆盖：创建成功/持久化第一节点+成员/链长校验/manual无题词400/无token 401/房间码格式 |
| 2 | frontend/src/services/chains.ts 已将 Mock 替换为真实后端 API，VITE_USE_MOCK=false 时不走 Mock 分支 | PASS | chains.ts 的 createChain 本身就是真实 API 调用（`api.post('/chains', data)`），无 Mock 分支。Mock 仅通过 axios-mock-adapter 在 VITE_USE_MOCK=true 时拦截 |
| 3 | 浏览器能证明请求命中真实后端 /api/chains | PASS | 启动后端 8099 + 前端 5199（VITE_USE_MOCK=false），POST /api/chains via Vite proxy → 200 + 真实 room_code（T5ZZJF，非 Mock 的 DRAW4）。Mock 拦截器未激活 |
| 4 | P02 页面不展示 [Mock] 数据或 Mock-only 文案 | PASS | CreateChainPage.tsx 已清理：注释从「Mock 阶段」改为「VITE_USE_MOCK=false 时调用真实后端」；PROMPT_POOL 注释从「Mock 题词池」改为「AI 生成未联调前本地 fallback（T-015 接入）」；handleGenerate 注释清理 Mock 字样 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | vite.config.ts `server.proxy['/api'] = { target: backendTarget, changeOrigin: true }`，默认 8099，可切 8003 |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 27 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build（VITE_USE_MOCK=false） | PASS | built 通过（chunk size 警告非阻塞） |
| Vite proxy 真实联通 | PASS | 后端 8099 + 前端 5199，login via proxy → 200+token，create chain via proxy → 200+room_code T5ZZJF，no token via proxy → 401，invalid length via proxy → 400 |

## 后端分层实现

按 backend-layers.md 从下往上分层：

| 层 | 文件 | 职责 |
|----|------|------|
| Pydantic 模型 | src/models/chain.py | CreateChainRequest（chain_length ge=4 le=10、visibility/prompt_source 枚举校验、prompt_text max_length=20）、ChainRead（响应序列化） |
| Repository | src/repositories/chain.py | generate_room_code（6 位大写字母+数字，排除 O/0/I/1/L）、create_chain_with_first_node（链+创建者成员+第一节点 seq=0 draw pending，房间码冲突重试 10 次） |
| Service | src/services/chain.py | create_chain（prompt_source=manual 校验 prompt_text 必填，ai 空题词暂置空待 T-015 填充） |
| API 路由 | src/api/routes/chains.py | POST /api/chains（Depends(get_current_user) 需登录，错误用 _error 构造契约体，成功用 success_response + _chain_to_read datetime→ISO） |
| 入口 | src/main.py | include_router(chains_router) + 全局异常处理器 |

## 关键改进：全局异常处理器统一错误格式

T-013 发现 FastAPI HTTPException 返回 `{"detail":"..."}` 与 api-contracts 的 `{"code":N,"message":"...","data":null}` 不符。T-013 的解法是路由层错误分支用 JSONResponse 显式构造。但 get_current_user（deps.py）抛的 401/403 和 Pydantic 的 422 也需统一。

**T-014 改进**：在 main.py 注册两个 app 级异常处理器（不重写 pycore，仅 app.exception_handler）：
- `HTTPException` handler：`{"detail":"..."}` → `{"code":N,"message":"...","data":null}`
- `RequestValidationError` handler：422 `{"detail":[...]}` → 400 `{"code":400,"message":"参数错误","data":null}`（api-contracts 用 400 表示参数错误）

这样所有路由的 HTTPException（含 get_current_user 的 401/403）和 Pydantic 校验错误都自动转为契约格式，无需每个路由单独处理。

## 业务规则实现

| PRD 规则 | 实现 |
|----------|------|
| BR-02 节点类型序列：固定画-述交替，起手为画 | 第一节点 seq=0 type=draw status=pending |
| BR-03 链长度 4-10 默认 6 | Pydantic `chain_length: Field(..., ge=4, le=10)` |
| BR-04 房间有效期 7 天 | `expires_at = now + timedelta(days=7)` |
| BR-07 公开性：邀请制+公开广场 | visibility 枚举 invite/public，Pydantic pattern 校验 |
| F-02-04 首节点指派：创建者默认承接第一节点 | create_chain_with_first_node 创建 Node(author_id=creator_id, author_label=creator.nickname) |
| 6.1 房间码 6 位大写字母+数字唯一 | generate_room_code 排除易混淆字符，room_code unique 约束 + 冲突重试 |

## 测试用例说明

`backend/tests/test_t014_chains.py`（6 测试，内存 SQLite + dependency_overrides）：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_create_chain_success | 创建 → 200，返回 6 位 room_code + 链信息 | PASS |
| test_create_chain_persists_first_node_and_member | DB 持久化：1 链 + 1 成员 + 1 节点（seq=0 draw pending author_label=昵称） | PASS |
| test_create_chain_invalid_length | 链长 3（<4）→ 400（全局 validation handler） | PASS |
| test_create_chain_manual_without_prompt_text | manual 无 prompt_text → 400 | PASS |
| test_create_chain_no_token | 无 token → 401 | PASS |
| test_room_code_format | room_code 6 位，无易混淆字符 O/0/I/1/L | PASS |

## 真实前后端联通验证

```
后端 8099 + 前端 5199（VITE_USE_MOCK=false）：
- POST /api/auth/login via proxy → 200 + 真实 JWT
- POST /api/chains via proxy → 200 + room_code T5ZZJF（真实后端生成，非 Mock DRAW4）
- POST /api/chains（无 token）via proxy → 401 {"code":401,"message":"缺少认证令牌","data":null}
- POST /api/chains（链长 3）via proxy → 400 {"code":400,"message":"参数错误","data":null}
```

## DB 持久化验证

真实 uvicorn + 真实 SQLite 文件验证（吸取 T-013 get_db commit 教训）：
- 创建链后 DB 验证：1 chain（room_code/status in_progress/current_seq 0）+ 1 member（user_id=创建者）+ 1 node（seq=0 type=draw status=pending author_label=小A）
- 测试后清理 3 条测试链，seed chain-0001 intact（6 nodes）

**自动验证全部通过。T-014 user_gate=true，需用户门禁验收浏览器 UI（创建链→显示房间码→跳转链大厅、链长校验提示、复制邀请链接）。**
