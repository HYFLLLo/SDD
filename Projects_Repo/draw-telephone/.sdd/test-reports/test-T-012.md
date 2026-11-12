# 测试报告：T-012 后端基础设施：数据库骨架 + 依赖注入 + 健康检查

**测试时间**：2026-08-19
**Tester**：Orchestrator 降级执行

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | backend/src/db/models.py 和 session.py 基于 pycore 模板扩展，含 User/Chain/Node/Vote/Notification 业务模型 | PASS | models.py 定义 Base(DeclarativeBase) + User/Chain/ChainMember/Node/Vote/Notification 六模型，字段与 PRD 6.1 数据契约对齐（UUID 主键、chain_length 4-10、room_code 6 位、seq 从 0、type draw/describe、is_ai、status 枚举、expires_at 7 天）。session.py 定义 engine/async_session_maker/get_db/init_db/close_db，基于 settings.database_url 构建 sqlite+aiosqlite 连接 |
| 2 | backend/src/api/deps.py 基于 pycore 模板扩展，get_current_user 作为路由级认证依赖 | PASS | deps.py 实现 `get_current_user(credentials=Depends(security), db=Depends(get_db))` 路由级依赖，从 Bearer token 解析 user_id 查库返回 User。使用项目 `src.db.session.get_db`，不使用 pycore 默认会话。另含 create_access_token/decode_token/require_admin |
| 3 | 受保护路由通过 Depends(...) 鉴权，无凭证/无效凭证返回 401 统一错误格式，无权限返回 403 | PASS | get_current_user：无凭证→401「缺少认证令牌」；decode_token 失败→401「无效或过期的认证令牌」；用户不存在→401「用户不存在」。require_admin：role!=admin→403「需要管理员权限」。均用 HTTPException + WWW-Authenticate: Bearer 头。测试 test_get_current_user_no_token 验证无凭证→401 |
| 4 | 认证/权限为路由级依赖，不要求出现在 app.user_middleware | PASS | 认证通过 `Depends(get_current_user)` 注入路由参数，未注册全局 AuthMiddleware。main.py 只注册 init_db/close_db 生命周期，无认证中间件 |
| 5 | GET /health 返回 200 | PASS | uvicorn 启动后 `curl /health` → `{"code":200,"message":"success","data":{"status":"healthy","version":"0.1.0"}}`。测试 test_health_check 验证 status_code==200 + body.code==200 + data.status=="healthy" |
| 6 | 真实 SQLite 文件存在，目标业务表和 seed 数据已落盘 | PASS | backend/data/draw_telephone.db 存在（69632 字节）。init_db.py 运行后验证：3 users / 1 chain / 6 nodes / 3 notifications / 3 chain_members。pytest 后运行时库仍 intact（3 users/1 chain/6 nodes） |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | $PY -m pytest backend/tests 通过 | PASS | 3 passed, 7 warnings in 0.89s（warnings 为 pycore pydantic v1 弃用警告，非项目代码，不阻塞） |
| 2 | cd backend && PYTHONPATH=.. $PY scripts/init_db.py 通过 | PASS | 建表 + seed 成功，输出「表已创建」「seed 数据已写入: 3 用户, 1 链, 6 节点, 3 通知」。数据库验证 mockuser found |
| 3 | cd backend && PYTHONPATH=.. $PY -m uvicorn src.main:app --host 127.0.0.1 --port 8099 可短时启动 | PASS | Uvicorn running on http://127.0.0.1:8099，Application startup complete（init_db 生命周期建表），GET /health → 200，GET /docs → 200 |
| 4 | SQLite 数据库文件、目标表、seed 数据真实存在（不只依赖测试夹具） | PASS | backend/data/draw_telephone.db 文件存在；运行时库查询返回 3 users/1 chain/6 nodes（非测试夹具的 :memory: 库） |
| 5 | $PY -m ruff check backend/src backend/tests 通过 | PASS | All checks passed!（per-file-ignores B008 排除 api/**/*.py 的 FastAPI Depends 默认值误报） |
| 6 | $PY -m mypy backend/src backend/tests 通过 | PASS | Success: no issues found in 16 source files（[[tool.mypy.overrides]] pycore.* follow_imports=skip 排除框架内部） |

## 测试用例说明

`backend/tests/test_t012_infra.py` 使用独立测试库（内存 SQLite `:memory:` + 事务回滚夹具），与运行时业务库物理隔离：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_health_check | GET /health → 200，body.code==200，data.status=="healthy" | PASS |
| test_tables_created | 6 张业务表全部创建（users/chains/chain_members/nodes/votes/notifications） | PASS |
| test_get_current_user_no_token | 无凭证调用 get_current_user → HTTPException 401 | PASS |

测试隔离机制：
- `test_engine` = create_async_engine("sqlite+aiosqlite:///:memory:")，独立于运行时 engine
- `test_db` fixture：每函数建表 + 销毁（create_all/drop_all），不污染运行时库
- `override_db` fixture：app.dependency_overrides[get_db] 注入测试 session，测试后 clear

## 短时启动验证

```
cd backend && PYTHONPATH=.. python -m uvicorn src.main:app --host 127.0.0.1 --port 8099
→ Initializing draw-telephone backend | host=127.0.0.1 port=8099
→ Started server process [8912]
→ API server started / Application startup complete
→ Uvicorn running on http://127.0.0.1:8099
→ GET /health → 200 {"code":200,"message":"success","data":{"status":"healthy","version":"0.1.0"}}
→ GET /docs → 200
```

## 数据库 seed 数据验证

init_db.py 写入的 seed 数据（与前端 Mock 数据对齐，供后续联调）：

- **3 用户**：mockuser/小A、userB/小B、userC/小C（bcrypt 哈希密码）
- **1 链**：chain-0001「戴帽子的猫」，chain_length=6，status=completed，room_code=ABC123
- **3 链成员**：mock-uuid / mock-uuid-b / mock-uuid-c
- **6 节点**：draw/describe 交替（seq 0-5），node-0005 is_ai=True 署名「AI 续」status=ai_filled
- **3 通知**：your_turn（未读）/ node_submitted（未读）/ chain_done（已读）

## 超出范围发现（不影响当前任务判定）

- **init_db.py 中文输出在 Windows 控制台乱码**：print 的中文在 GBK 控制台显示乱码，但不影响功能——数据库数据验证通过（UTF-8 存储），后续可考虑 print 改英文或设 PYTHONIOENCODING=utf-8。
- **pydantic v1 弃用警告**：pytest 7 warnings 来自 pycore 内部 pydantic config（`model_config` 弃用提示），pycore 不在质量门禁范围，非阻塞。

**验证已完成。T-012 user_gate=false，自动推进 T-013（用户认证功能闭环，user_gate=true，需用户门禁）。**
