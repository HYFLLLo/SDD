# 测试报告：T-020 作品详情功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> GET /api/works（广场列表）+ GET /api/works/{id}（只读全链）全部命中真实后端，作品详情闭环验证通过：游客可访问（无 JWT）+ completed 链列表（分页 + 排序 + thumb_url/member_count/like_count）+ 作品详情全链节点（draw/describe 交替，含 author/content_url/content_text/is_ai）+ 404「作品不存在」。前端 P01 广场页用 thumb_url 显示真实缩略图，P06 作品详情页用 content_url 显示真实画作。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在广场页看到真实已完成作品卡片列表 | PASS | P01 PlazaPage 调真实 GET /api/works，渲染 completed 链卡片列表（含 chain_length/member_count/like_count/thumb_url）。WorkThumb 用 thumb_url 显示真实画作，无 thumb_url 时 fallback 首字占位 |
| 2 | 用户点作品卡片进作品详情页，看到真实全链内容（画/述交替），每节点作者署名 | PASS | P06 WorkDetailPage 调真实 GET /api/works/{id}，纵向展示全链节点（draw/describe 交替）。ChainNodeCard 显示 author.nickname 署名 + 第 N 棒 + 画/述类型标签。image 节点用 content_url 显示真实画作，text 节点显示「描述」 |
| 3 | AI 补位的节点展示带 AI 续标签 | PASS | ChainNodeCard 检测 node.is_ai，true 时加 ai-node 样式（冷灰蓝边框 + 背景）+ 「AI 续」标签。后端 is_ai 字段从 Node 表直接取。测试 test_get_work_detail_ai_node_tag 验证 is_ai=true 节点 + author_id=None 时 nickname fallback 到 author_label |
| 4 | 作品不存在时，详情页显示「作品不存在」提示 | PASS | 后端 GET /api/works/{id} 链不存在或未完成 → 404 {code:404,message:"作品不存在",data:null}。前端 getWorkDetail catch → message.error + work=null → 渲染「作品不存在」空状态。测试 test_get_work_detail_not_found + test_get_work_detail_incomplete_404 验证 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 GET /api/works、GET /api/works/{id} 单元/集成测试通过 | PASS | test_t020_works.py 10 测试全过（列表 5 + 详情 5） |
| 2 | frontend/src/services/works.ts 已将 Mock 替换为真实后端 API | PASS | works.ts 本就是真实 Axios 调用（getWorks/getWorkDetail），无 Mock 分支，T-020 无需改动 |
| 3 | 后端能验证广场/详情请求命中真实后端 | PASS | 真实联调：curl GET /api/works → 200 返回 chain-0001 completed 链（含 thumb_url/member_count/like_count）；GET /api/works/chain-0001 → 200 返回 6 节点全链 |
| 4 | P01/P06 页面不展示 [Mock] 数据 | PASS | P01 删 Mock 注释，WorkThumb 用真实 thumb_url；P06 删 Mock 注释，ChainNodeCard 用真实 content_url。无 [Mock] 占位 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | Vite proxy /api → 8099（T-006 已配，T-020 复用） |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 38 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build | PASS | built 通过（1996 modules，chunk size 警告非阻塞） |

## 后端分层实现

| 层 | 文件 | 职责 |
|----|------|------|
| 模型 | src/models/work.py | WorkAuthorResponse/WorkListItemResponse/WorkNodeResponse/WorkDetailResponse/WorkListResponse（Pydantic 响应模型） |
| 数据访问 | src/repositories/work.py | WorkRepository：list_completed_chains（分页+排序，most_liked 用 Vote 子查询）/ get_chain / get_creator / get_nodes（status="submitted" 按 seq）/ get_node_authors（批量）/ count_members / count_likes（Vote 表）/ get_thumb_url（首个 draw 节点 content_url） |
| 业务服务 | src/services/work.py | WorkService：list_works（遍历 completed 链查 member_count/like_count/thumb_url）+ get_work_detail（链+creator+已提交节点+批量 author，LookupError→404） |
| 路由 | src/api/routes/works.py | GET /api/works（分页+排序）+ GET /api/works/{id}（详情），游客可访问无 get_current_user，404 返回契约格式 |

## 关键设计决策

### 1. 游客可访问（无 JWT 鉴权）

作品广场 + 详情是公开只读功能，GET /api/works 和 GET /api/works/{id} 不加 get_current_user 依赖。任何访客可浏览已完成作品（符合公开广场语义）。测试 test_list_works_guest_accessible + test_get_work_detail_guest_accessible 验证无 token 仍 200。

### 2. 只展示 completed 链

只有 status="completed" 的链才作为作品展示。未完成链（in_progress/closed/expired）不出现在广场列表，查详情也返回 404。list_completed_chains 查询过滤 status="completed"，get_work_detail 校验 chain.status != "completed" → LookupError。测试 test_list_works_excludes_incomplete_chains + test_get_work_detail_incomplete_404 验证。

### 3. thumb_url 取首个 draw 节点 content_url

广场卡片缩略图取链中第一个 draw 节点（seq 最小）的 content_url。get_thumb_url 查 Node.type=="draw" + content_url IS NOT NULL，按 seq 升序取首条。无 draw 节点或无 content_url 返回空字符串（前端 fallback 首字占位）。

### 4. like_count 查 Vote 表（T-021 前返回 0）

like_count 查 Vote 表 count（T-021 投票功能实现后才有数据）。当前无 Vote 记录返回 0。count_likes 用 select(func.count()).select_from(Vote)。

### 5. AI 补位节点 author_id=None

模型设计 AI 补位节点 author_id=None（无真实用户）。get_work_detail 构建节点时，author_id 为空则 nickname fallback 到 node.author_label（AI 补位时存"AI"）。get_node_authors 批量查 User，author_map 不含 None key，自然 fallback。测试 test_get_work_detail_ai_node_tag 验证。

### 6. most_liked 排序用 Vote 子查询

list_completed_chains 的 most_liked 排序用 Vote 子查询统计每链点赞数，outerjoin + coalesce 降序。latest（默认）按 created_at 降序。不支持的 sort 降级为 latest。

## 测试用例说明

`backend/tests/test_t020_works.py`（10 测试，独立内存 SQLite + dependency_overrides 注入）：

**GET /api/works 广场列表（5 测试）**：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_list_works_empty | 无作品 → 空列表 + total=0 | PASS |
| test_list_works_returns_completed_chains | completed 链 → 含 member_count/like_count/thumb_url | PASS |
| test_list_works_excludes_incomplete_chains | in_progress 链不展示 | PASS |
| test_list_works_pagination | page + page_size 分页 | PASS |
| test_list_works_guest_accessible | 游客无 token 仍 200 | PASS |

**GET /api/works/{id} 作品详情（5 测试）**：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_get_work_detail_success | 全链节点（draw/describe 交替 + author + content_url/text + is_ai） | PASS |
| test_get_work_detail_not_found | 不存在 → 404「作品不存在」 | PASS |
| test_get_work_detail_incomplete_404 | 未完成链 → 404 | PASS |
| test_get_work_detail_guest_accessible | 游客无 token 仍 200 | PASS |
| test_get_work_detail_ai_node_tag | AI 补位节点 is_ai=true + nickname="AI" | PASS |

## 真实前后端联通验证

```
后端 8099（真实 SQLite 文件库）：

1. GET /api/works（无 token）→ 200 + completed 链列表（chain-0001，含 thumb_url/member_count/like_count）✓
2. GET /api/works/chain-0001（无 token）→ 200 + 全链 6 节点（draw/describe 交替，含 author/content_url/content_text/is_ai）✓
3. GET /api/works/nonexistent-id → 404 {code:404,message:"作品不存在",data:null} ✓
4. /health → 200 healthy ✓
```

## 与 T-017/T-018/T-019 的衔接

- T-017 节点接力：T-020 作品详情读全链已提交节点（status="submitted"），接力提交的节点在此展示
- T-018 图片上传：T-020 作品详情/广场缩略图用 content_url（上传返回的 /uploads/xxx.png 路径）显示真实画作
- T-019 WebSocket：T-020 是只读展示，不涉及 WS；链完成后才出现在广场（completed 状态由 submit 触发）

**自动验证全部通过（10 单元测试 + 3 项真实联调 + 前端 type-check/lint/build）。T-020 user_gate=true，需用户门禁验收浏览器 UI（广场看真实作品卡片 + 详情看全链真实图片 + 不存在提示）。**
