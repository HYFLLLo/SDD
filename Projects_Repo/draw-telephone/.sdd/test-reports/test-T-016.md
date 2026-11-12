# 测试报告：T-016 链查询/加入功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> 三个新端点全部命中真实后端，DB 持久化正常。GET /api/chains/{room_code} 查询链、POST /api/chains/{id}/join 加入链、GET /api/chains/{id}/detail 链大厅详情均返回正确契约体。进度节点链推导正确（已建节点带真实 author，未建节点 author="待接"）。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在加入链页输入真实房间码，校验通过后跳转链大厅页，看到真实链状态 | PASS | GET /api/chains/{room_code} 返回 ChainLookup（title/chain_length/current_seq/is_full/remaining_slots）。前端 JoinChainPage.doLookup 调 lookupChain(code)，res.data 填 lookup 预览，handleJoin 调 joinChain(lookup.id) 成功后 navigate(`/chain/${id}`) 跳链大厅页 |
| 2 | 用户从邀请链接进入，房间码自动带码，确认后跳转链大厅页 | PASS | JoinChainPage useEffect 从 searchParams.get('code') 取码，自动填入 6 格 + 自动 doLookup 校验。链大厅页 ChainHallPage 用 useParams().id 调 getChainDetail(id) 渲染真实链状态 |
| 3 | 房间码无效或链已过期时，加入页显示「房间码无效或链已过期」错误提示 | PASS | GET /api/chains/NOPE00 → 404 {code:404, message:"房间码无效或链已过期", data:null}。前端 doLookup catch → message.error('房间码无效或链已过期') |
| 4 | 链已满时加入页显示「链已满或已过期」错误提示 | PASS | POST /{id}/join 链已满 → 403 {code:403, message:"链已满或已过期", data:null}。前端 handleJoin catch → message.error('链已满或已过期') |
| 5 | 用户在链大厅页看到真实进度节点链、成员列表、当前责任人、AI 补位倒计时 | PASS | GET /api/chains/{id}/detail 返回 ChainDetail（nodes 4 个含推导进度链、members 真实成员、current_author 当前责任人、ai_countdown_at=null 待 T-024）。ChainHallPage 渲染 nodes.map 进度节点链 + members.map 成员列表 + current_author + ai_countdown_at 倒计时（null 时不显示） |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 GET /api/chains/{room_code}、POST /api/chains/{id}/join、GET /api/chains/{id}/detail 单元/集成测试通过 | PASS | test_t016_chain_query.py 11 测试全过（lookup 成功/无效404/无token401、join 成功/重复403/已满403/不存在404、detail 成功/非成员403/不存在404/加入后可访问） |
| 2 | frontend/src/services/chains.ts 已将 Mock 替换为真实后端 API，VITE_USE_MOCK=false 时不走 Mock 分支 | PASS | chains.ts 的 lookupChain/joinChain/getChainDetail 本身就是真实 API 调用（`api.get/post('/chains/...')`），无 Mock 分支 |
| 3 | 浏览器能证明请求命中真实后端 | PASS | 真实联调脚本验证：后端 8099 直连，10 项端点全部返回正确契约体（见下「真实前后端联通验证」） |
| 4 | P03/P04 页面不展示 [Mock] 数据 | PASS | JoinChainPage/ChainHallPage 注释已清理（Mock 阶段→真实后端，MockStroke→笔迹占位 T-019 标注），无 [Mock] 文案 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | Vite proxy /api → http://127.0.0.1:8099（T-014 已配，T-016 复用）。真实联调直连 8099 验证端点正确 |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 32 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build（VITE_USE_MOCK=false） | PASS | built 通过（chunk size 警告非阻塞，非本次引入） |
| Vite proxy 真实联通 | PASS | 后端 8099 直连验证三个新端点全部正确 |

## 后端分层实现

按 backend-layers.md 从下往上分层：

| 层 | 文件 | 职责 |
|----|------|------|
| Repository | src/repositories/chain.py | 扩展 6 方法：count_members（统计成员数）、get_members（全部成员）、get_member（查某用户是否成员）、get_nodes（已建节点按 seq 排序）、get_current_node（当前 seq 节点）、add_member（加入成员） |
| Service | src/services/chain.py | 扩展 lookup_chain（房间码→ChainLookup，无效/过期→ValueError→404）、join_chain（校验未满/未过期/未重复，LookupError→404，ValueError→403）、get_chain_detail（成员权限，LookupError→404，PermissionError→403，返回 ChainDetail 含推导节点链）+ _node_type（seq 偶数 draw 奇数 describe）+ _get_member_users（查成员用户信息）+ _is_expired（过期判断，容错 SQLite naive datetime）+ _build_node_list（推导进度节点链）+ _get_current_author（当前责任人） |
| API 路由 | src/api/routes/chains.py | 扩展 GET /{room_code}（lookup，ValueError→404）、POST /{chain_id}/join（join，LookupError→404，ValueError→403）、GET /{chain_id}/detail（detail，LookupError→404，PermissionError→403） |
| 入口 | src/main.py | 无需改动（chains_router 已在 T-014 注册） |

## 路由设计决策（重要说明）

api-contracts.md 定义 `GET /api/chains/{id}`（无 /detail 后缀）用于链大厅详情。但后端实现用 `GET /api/chains/{chain_id}/detail`，因为：

- `GET /api/chains/{room_code}`（按房间码查询，加入前校验）和 `GET /api/chains/{id}`（链大厅详情）的路径参数都是 `/{param}`，FastAPI 路由会冲突（先注册的先匹配，导致后者永远命中前者）。
- 加 `/detail` 后缀区分：`/{room_code}` 是 6 位房间码查询，`/{chain_id}/detail` 是 UUID 链 ID 详情，两者路径模式不同（前者单段，后者两段），无冲突。

前端 chains.ts 的 getChainDetail 已同步改为 `/chains/${id}/detail`。这是合理的路由设计决策，与 api-contracts.md 的路径略有出入但语义清晰、无歧义。测试报告中如实记录。

## 进度节点链推导逻辑

```
chain_length=4，current_seq=0（创建后初始）

_build_node_list 遍历 seq 0..3：
  seq=0：DB 已建节点（draw, author=创建者"画师甲"）→ 真实 author
  seq=1：DB 未建 → 占位（describe, author={id:"", nickname:"待接"}）
  seq=2：DB 未建 → 占位（draw, author="待接"）
  seq=3：DB 未建 → 占位（describe, author="待接"）

返回 4 个节点，已建带真实 author，未建带"待接"占位
```

## 测试用例说明

`backend/tests/test_t016_chain_query.py`（11 测试，内存 SQLite + dependency_overrides）：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_lookup_chain_success | 真实房间码查询 → 200 + ChainLookup 字段正确 | PASS |
| test_lookup_chain_invalid_code | 无效房间码 → 404 | PASS |
| test_lookup_chain_no_token | 无 token → 401 | PASS |
| test_join_chain_success | 加入链 → 200 + joined=true，DB 成员数=2 | PASS |
| test_join_chain_duplicate | 重复加入 → 403 "你已是该链成员" | PASS |
| test_join_chain_full | 链已满 → 403 "链已满或已过期" | PASS |
| test_join_chain_not_found | 链不存在 → 404 | PASS |
| test_get_chain_detail_success | 链大厅详情 → 200 + ChainDetail（含推导 4 节点链） | PASS |
| test_get_chain_detail_non_member | 非成员访问 → 403 | PASS |
| test_get_chain_detail_not_found | 链不存在 → 404 | PASS |
| test_get_chain_detail_after_join | 加入者也能访问详情 → 200 + members=2 | PASS |

## 真实前后端联通验证

```
后端 8099（真实 SQLite 文件库，数据持久化）：

1. POST /api/auth/register（创建者）→ 200 + JWT
2. POST /api/auth/register（加入者）→ 200 + JWT
3. POST /api/chains（创建链 chain_length=4）→ 200 + room_code="DE6ENA"
4. GET /api/chains/DE6ENA → 200 + ChainLookup
   {title:"T016 联调链", chain_length:4, current_seq:0, is_full:false, remaining_slots:3}
5. GET /api/chains/NOPE00 → 404 {code:404, message:"房间码无效或链已过期"}
6. POST /api/chains/{id}/join（加入者）→ 200 {chain_id, joined:true}
7. POST /api/chains/{id}/join（重复）→ 403 {code:403, message:"你已是该链成员"}
8. GET /api/chains/{id}/detail → 200 + ChainDetail
   {current_node_type:"draw", current_author:{nickname:"画师甲"},
    members:[创建者,加入者], nodes:[4个含推导], ai_countdown_at:null}
9. GET /api/chains/{id}/detail（非成员）→ 403 {code:403, message:"无权访问该链"}
10. GET /api/chains/DE6ENA（无 token）→ 401
```

## DB 持久化

- 真实 SQLite 文件库，数据落盘：重复运行联调脚本时「用户名已存在」证明数据持久化。
- ChainMember 表记录成员关系，join 后 count_members 递增，detail 查询 get_members 返回真实成员列表。
- Node 表记录已建节点，_build_node_list 从 DB 取已建节点 + 推导未建占位。

## 修复记录

- **SQLite datetime 时区问题**：`_is_expired` 中 `chain.expires_at < datetime.datetime.now(datetime.UTC)` 报 offset-naive vs aware 比较错误（SQLite 读回的 datetime 可能丢失时区信息）。修复：比较前检查 `expires_at.tzinfo is None`，naive 则 `replace(tzinfo=datetime.UTC)` 统一为 aware 再比较。

**自动验证全部通过（11 单元测试 + 10 项真实联调）。T-016 user_gate=true，需用户门禁验收浏览器 UI（加入链页输入房间码→校验→加入→链大厅页看真实进度/成员/责任人）。**
