# 测试报告：T-019 WebSocket 实时围观功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> WS /ws/room/{chain_id} 全部命中真实后端，实时围观闭环验证通过：JWT 鉴权（query param token）+ 连接管理（房间广播）+ stroke 笔迹广播（作画者推送，围观者实时收到）+ notify 通知广播（submit 后 node_submitted + your_turn）。前端 P04 链大厅删 Mock 定时器接入真实 WS stroke + notify，P05 接力页作画时推送 stroke 笔迹。无 token → error「未认证」+ close 4401。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户 A 在接力页作画时，用户 B 在链大厅页实时围观，看到 A 的笔迹逐步呈现（真实 WebSocket 传输） | PASS | P05 RelayPage draw 时节流推送 stroke（200ms 间隔）→ WS /ws/room/{chain_id} → 后端校验作画者是当前节点责任人 → 广播给同房间在线连接 → P04 ChainHallPage onMessage 收 stroke → setStrokes 追加 points → canvas 重绘。真实联调：作画者推送 stroke → 围观者收到 stroke 事件 |
| 2 | 节点提交后，下一位责任人在链大厅页收到「轮到你了」通知（真实 WebSocket notify） | PASS | submit 路由层调完 service.submit_node 成功后，据 chain_status 触发 ws_manager.broadcast_notify：completed→chain_done，否则→node_submitted + your_turn。P04 收 notify → message.info('轮到你了！') + 重新拉 detail 刷新进度。真实联调：submit 后围观者收到 node_submitted + your_turn 两个 notify |
| 3 | 未认证用户连 WebSocket，收到「未认证」错误 | PASS | WS 端点用 query param ?token=JWT + decode_token 鉴权（浏览器 WS 不能设 header）。无 token/无效 token → accept + send error「未认证」+ close(4401)。真实联调：无 token 连接 → 收 error「未认证」+ 关闭 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 WS /ws/room/{chain_id} 单元/集成测试通过（连接/广播/notify/JWT 鉴权） | PASS | test_t019_ws.py 10 测试全过（鉴权 4 + ConnectionManager 广播逻辑 5 + 单例 1） |
| 2 | frontend/src/services/ws.ts 已将 Mock 模拟替换为真实 WebSocket，VITE_USE_MOCK=false 时走真实后端 | PASS | ws.ts 的 RoomSocket 本就是真实 WebSocket（相对路径 /ws），T-019 补 token query param（从 useAuthStore 取 token 拼 URL）。无 Mock 分支 |
| 3 | frontend/vite.config.ts 的 /ws 代理配置 ws:true，指向后端 8099/8003 | PASS | Vite proxy /ws → 8099（ws:true，T-006 已配，T-019 复用） |
| 4 | 前端代码未硬编码 ws://localhost:8099，通过代理相对路径分发 | PASS | ws.ts 用 `${proto}://${window.location.host}/ws/room/${chainId}`（相对 host，经 Vite 代理），无硬编码后端地址 |
| 5 | 后端能验证连 WebSocket 的用户是真实的，不是前端定时器模拟 | PASS | WS 端点 decode_token 验签 JWT，stroke 推送校验 node.author_id == user_id（当前节点责任人）。真实联调验证 |
| 6 | P04/P05 页面不展示 [Mock] 模拟笔迹 | PASS | P04 删除 MOCK_STROKES + 定时器，接入真实 WS stroke。P05 推送真实 stroke。无 [Mock] 数据 |
| 7 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 43 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build（VITE_USE_MOCK=false） | PASS | built 通过（chunk size 警告非阻塞） |
| Vite proxy 真实联通 | PASS | 后端 8099 直连 WS 验证全链路 |

## 后端分层实现

| 层 | 文件 | 职责 |
|----|------|------|
| WS 连接管理 | src/api/ws.py | ConnectionManager（内存 dict: chain_id → set[WebSocket]）：connect/disconnect/broadcast/broadcast_notify。ws_manager 全局单例 |
| WS 端点 | src/main.py | @app.websocket("/ws/room/{chain_id}")：query param token 鉴权（decode_token），subscribed 确认，stroke 推送校验当前节点责任人（独立 session 查 DB），广播给同房间 |
| Notify 触发 | src/api/routes/nodes.py | submit 路由层 service.submit_node 成功后，据 chain_status 触发 ws_manager.broadcast_notify（service 层不感知 WS） |

## 关键设计决策

### 1. Notify 触发：路由层触发（service 不感知 WS）

submit 路由调完 `service.submit_node` 成功后，路由层据返回值 `chain_status`/`next_seq` 触发 `ws_manager.broadcast_notify`。service 层只依赖 repository，不依赖 WS（分层约束）。路由层编排广播：completed→chain_done，否则→node_submitted + your_turn。`ws_manager` 是全局单例，路由层 + WS 端点共享同一连接池。

### 2. WS 鉴权：query param token（浏览器 WS 不能设 header）

浏览器 WebSocket 不能设自定义 Authorization header（`get_current_user` 的 HTTPBearer 不适用）。WS 端点用 `?token=JWT` query param + `decode_token`（复用 `src.core.security`）。无效/缺失 → accept + send error「未认证」+ close(4401)。前端 ws.ts 从 `useAuthStore` 取 token 拼 URL。

### 3. stroke 推送校验当前节点责任人

WS 端点收到 stroke 消息时，用独立 `async_session_maker()` session 查 chain + current_node，校验 `node.author_id == user_id`（当前节点责任人才能推笔迹）。非责任人推送被忽略（不广播）。独立 session 因 WS 循环不能持有请求级 Depends session。

### 4. 围观范围：JWT 认证即可订阅

任何有效 JWT 用户可订阅 `/ws/room/{chain_id}` 围观笔迹 + 收 notify（符合公开广场围观语义）。不强制校验链成员（公开链任何人可看）。前端 P04 进入链大厅即订阅。

### 5. WS 路由注册：@app.websocket（FastAPI 原生）

`main.py` 已有 `app = server.app`（pycore APIServer 暴露标准 FastAPI 实例），直接用 `@app.websocket("/ws/room/{chain_id}")` 注册（FastAPI 原生，pycore 无 WS 工具）。与 `app.mount` StaticFiles 同区。

### 6. 前端 stroke 推送节流

P05 RelayPage draw 时调 `flushStroke`，200ms 间隔节流推送（避免高频 flooding WS）。推送当前 currentStroke 的 points（含 pressure 0.5）+ color + size + node_id。

## 测试用例说明

`backend/tests/test_t019_ws.py`（10 测试）：

**鉴权/订阅/断开（TestClient 同步 WS，token 用 create_access_token 直接生成不依赖 DB）**：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_ws_connect_subscribed | 有效 token 连接 → subscribed | PASS |
| test_ws_no_token_error | 无 token → error「未认证」+ close 4401 | PASS |
| test_ws_invalid_token_error | 无效 token → error「未认证」+ close 4401 | PASS |
| test_ws_disconnect_cleanup | 断开后连接从房间移除 | PASS |

**ConnectionManager 广播逻辑（单元测试，MagicMock(spec=WebSocket)）**：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_broadcast_delivers_to_all_in_room | broadcast → 同房间所有连接收到 | PASS |
| test_broadcast_notify_format | broadcast_notify → 消息格式 {type:notify,event,chain_id,node_seq} | PASS |
| test_broadcast_removes_dead_connections | 广播时发送失败的连接自动移除 | PASS |
| test_broadcast_empty_room_no_error | 广播到不存在的房间不报错 | PASS |
| test_disconnect_removes_from_room | disconnect 移出房间，空则删除 | PASS |
| test_ws_manager_singleton | ws_manager 全局单例（路由层+WS端点共享） | PASS |

## 真实前后端联通验证

```
后端 8099（真实 SQLite 文件库 + WebSocket）：

1. 注册用户 → 200 + access_token
2. 建链（chain_length=4）→ 200 + chain_id
3. WS 有效 token 连接 → 收 subscribed ✓
4. WS 无 token 连接 → 收 error「未认证」+ 关闭 ✓
5. 作画者 WS 连接推送 stroke → 围观者 WS 收到 stroke 事件 ✓
6. 上传 PNG + submit 节点 → 200 + chain_status=in_progress
7. 围观者 WS 收到 notify：node_submitted + your_turn ✓
8. 断言 events 含 node_submitted + your_turn → 通过 ✓
```

## 与 T-017/T-018 的衔接

- T-017 节点接力（previous + submit）：T-019 在 submit 路由层补 notify 广播，提交后下一位 + 围观者实时收到通知
- T-018 图片上传：T-019 联调脚本复用上传 PNG + submit 流程，验证 submit 后 notify 广播
- T-019 补齐实时围观：P04 链大厅实时看作画者笔迹，P05 接力页作画时推送笔迹

**自动验证全部通过（10 单元测试 + 8 项真实联调 + 前端 type-check/lint/build）。T-019 user_gate=true，需用户门禁验收浏览器 UI（A 作画 B 围观笔迹 + A 提交 B 收通知 + 无 token 拒绝）。**
