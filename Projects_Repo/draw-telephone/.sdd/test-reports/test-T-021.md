# 测试报告：T-021 投票功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> POST /api/chains/{id}/votes（提交投票）+ GET /api/chains/{id}/votes/result（结果统计）全部命中真实后端，投票闭环验证通过：链完成 + 房间成员权限 + 三维度各一票（most_drift/best_draw/best_describe）+ 唯一约束（每人每链只能投一次，重复→403）+ target_node 属于链校验 + 结果统计含 target_author。前端 P07 回放页已完整接入真实 API（submitVotes/getVoteResult 真实调用，无 Mock 分支），回放节点画作用 content_url 显示真实图片。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在回放页回放完成后，三维度（最跑偏/最佳画/最佳描述）各投一票，提交成功 | PASS | P07 ReplayPage 回放完成后显示 VotePanel（三维度单选），handleSubmit 调 submitVotes(id,{votes}) → POST /api/chains/{id}/votes → 200。真实联调：A 建链+接力完成+投票三维度 → 200 + results 三维度 vote_count=1 |
| 2 | 用户提交投票后看到三维度投票结果统计（三维度票数+领先者） | PASS | submitVotes 成功后调 getVoteResult(id) → GET /api/chains/{id}/votes/result → 200 + results 含 target_author{nickname} + vote_count。VoteResultView 渲染三维度统计条形图 + 🏆 领先者。真实联调：投票后查结果 → 200 三维度含「投票A」1票 |
| 3 | 链未完成时投票，页面提示「链未完成或无权投票」 | PASS | 后端 chain.status != completed → PermissionError → 403「链未完成或无权投票」。前端 submitVotes catch → message.error。测试 test_submit_votes_chain_not_completed 验证 403 |
| 4 | 非房间成员投票，页面提示权限提示 | PASS | 后端 get_member 返回 None → PermissionError → 403「链未完成或无权投票」。测试 test_submit_votes_non_member 验证。真实联调：非成员 B 投票 → 403 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 POST /api/chains/{id}/votes、GET /api/chains/{id}/votes/result 单元/集成测试通过 | PASS | test_t021_votes.py 10 测试全过（投票 7 + 结果 3） |
| 2 | frontend/src/services/votes.ts 已将 Mock 替换为真实后端 API | PASS | votes.ts 本就是真实 Axios 调用（submitVotes/getVoteResult），无 Mock 分支，T-021 无需改动 |
| 3 | 后端能验证回放/投票请求命中真实后端 | PASS | 真实联调：curl POST /api/chains/{id}/votes（成员 token）→ 200 + GET /api/chains/{id}/votes/result → 200 含 target_author；无 token → 401；非成员/重复 → 403 |
| 4 | P07 页面不展示 [Mock] 数据 | PASS | P07 删 Mock 注释，ReplayNodeItem image 用真实 content_url。submitVotes/getVoteResult/getWorkDetail 全真实调用。无 [Mock] 数据 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | Vite proxy /api → 8099（T-006 已配，T-021 复用） |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 42 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build | PASS | built 通过（chunk size 警告非阻塞） |

## 后端分层实现

| 层 | 文件 | 职责 |
|----|------|------|
| 模型 | src/models/vote.py | VoteItemRequest/VoteRequest/VoteCountItem/VoteResultItem/VoteResultResponse/VoteResultDetailResponse（Pydantic，target_author 复用 WorkAuthorResponse） |
| 数据访问 | src/repositories/vote.py | VoteRepository：create_votes（批量插入，IntegrityError→ValueError 已投过）/ has_voted / count_by_chain（按 dimension+target_node_id 分组统计）/ get_node / get_nodes_by_ids / get_node_authors |
| 业务服务 | src/services/vote.py | VoteService：submit_votes（链存在+成员+完成+三维度齐全+target 属于链+未投过）+ get_result（分组统计+批量查 target_author，author_id 空时 fallback author_label） |
| 路由 | src/api/routes/votes.py | POST /api/chains/{id}/votes + GET /api/chains/{id}/votes/result，需登录鉴权，LookupError→404/PermissionError→403/ValueError→400 |

## 关键设计决策

### 1. 403 统一语义（不区分原因）

链未完成 / 非成员 / 已投过 → 都返回 403「链未完成或无权投票」。契约只定义这一个 403 message，不区分原因，避免泄露投票状态（如不告诉非成员"链已完成但你不该投"，只说"无权"）。PermissionError 在 service 层统一抛此 message。

### 2. 唯一约束 = 每人每维度一票

Vote 表 `uq_vote_chain_user_dim(chain_id,user_id,dimension)` 唯一约束。create_votes 批量插入时若该用户该维度已投过 → IntegrityError → rollback → raise ValueError。但 service 层先用 has_voted 预检（任一维度投过 → 403），IntegrityError 是兜底（并发场景）。

### 3. 三维度齐全校验

submit_votes 校验 set(dimension) == {most_drift, best_draw, best_describe}，缺维度或重复维度 → 400「必须为三个维度各投一票」。DIMENSIONS 常量定义三维度集合。

### 4. target_node 属于链校验

每个 vote 的 target_node_id 逐个查 get_node，校验 node.chain_id == chain.id 且 node.status == "submitted"。不属于链或未提交 → 400「投票目标节点不属于该链」。

### 5. get_result 的 target_author fallback

count_by_chain 返回 [{dimension, target_node_id, vote_count}]，无 author。get_result 批量查 Node 取 author_id + author_label，再批量查 User。author_id 为空（AI 补位节点）时 nickname fallback 到 node.author_label（与 T-020 作品详情一致）。

### 6. 路由前缀共享 /api/chains

votes.py 用 prefix="/api/chains"，与 chains.py 共享前缀。FastAPI 允许多 router 共享前缀（按 tags 区分），路径不重叠：chains.py 有 `""`/`/{room_code}`/`/{id}/join`/`/{id}/detail`，votes.py 有 `/{id}/votes`/`/{id}/votes/result`。

## 测试用例说明

`backend/tests/test_t021_votes.py`（10 测试，独立内存 SQLite + dependency_overrides + 构造 completed 链 + 全部 submitted 节点 + 成员）：

**POST /api/chains/{id}/votes（7 测试）**：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_submit_votes_success | 成员投三维度 → 200 + 三维度 vote_count=1 | PASS |
| test_submit_votes_chain_not_completed | 链未完成 → 403 | PASS |
| test_submit_votes_non_member | 非成员 → 403 | PASS |
| test_submit_votes_already_voted | 重复投票 → 403 | PASS |
| test_submit_votes_missing_dimension | 三维度不齐 → 400 | PASS |
| test_submit_votes_invalid_target | target 不属于链 → 400 | PASS |
| test_submit_votes_no_token | 无 token → 401 | PASS |

**GET /api/chains/{id}/votes/result（3 测试）**：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_get_vote_result_success | 投票后查结果 → 200 含 target_author + vote_count | PASS |
| test_get_vote_result_chain_not_found | 链不存在 → 404 | PASS |
| test_get_vote_result_empty | 无投票 → 200 空结果 | PASS |

## 真实前后端联通验证

```
后端 8099（真实 SQLite 文件库）：

1. 注册用户 A → 200 + access_token ✓
2. 建链（chain_length=4，manual 起手「戴帽子的猫」）→ 200 + chain_id + room_code ✓
3-6. A 接力提交 4 节点（draw→describe→draw→describe）→ 链 completed ✓
7. 查作品详情 → 200 + 4 节点（draw/describe 交替 + content_url）✓
8. A 投票（三维度）→ 200 + results 三维度 vote_count=1 ✓
9. 查投票结果 → 200 + 三维度含 target_author（投票A）+ vote_count=1 ✓
10. 重复投票 → 403「链未完成或无权投票」✓
11. 非成员 B 投票 → 403「链未完成或无权投票」✓
12. 无 token 投票 → 401「缺少认证令牌」✓
```

## 与 T-017/T-020 的衔接

- T-017 节点接力：T-021 投票依赖链完成（submit 推进到 completed），接力提交的节点是投票 target
- T-020 作品详情：T-021 投票结果 target_author 复用 T-020 的 WorkAuthorResponse + author fallback 逻辑；like_count（T-020 广场列表）查 Vote 表，T-021 实现后广场 like_count 有数据

**自动验证全部通过（10 单元测试 + 12 项真实联调 + 前端 type-check/lint/build）。T-021 user_gate=true，需用户门禁验收浏览器 UI（回放完成后三维度投票 + 提交看结果 + 未完成/非成员提示）。**
