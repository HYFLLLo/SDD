# 测试报告：T-023 个人资料/我的作品功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> GET /api/users/me（个人资料：昵称/参与链数/创建链数）+ GET /api/users/me/works（我的作品列表，含 role=creator/参与者 + status=in_progress/completed + thumb_url）全部命中真实后端，个人主页闭环验证通过：个人资料含基础信息+参与/创建统计 + 我的作品列表含角色/状态/缩略图 + 防越权（用户只看自己参与/创建的链）+ 无 token 401。前端 P08 ProfilePage 已完整接入真实 API（getUserProfile/getMyWorks 真实 Axios 调用，无 Mock 分支），MyWorkCard 缩略图用真实 thumb_url（有图显图，无图 fallback 首字，与广场页 WorkThumb 一致）。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在个人主页看到真实个人资料（昵称、参与链数、创建链数） | PASS | GET /api/users/me → {id,username,nickname,avatar_url,created_at,participated_chains,created_chains}。真实联调：userA 建链后 participated=2/created=2（建2链，创建者自动成员） |
| 2 | 用户看到自己的参与/创建真实作品卡片列表 | PASS | GET /api/users/me/works → items 含 {id,title,chain_length,status,role,thumb_url,created_at}。真实联调：userA 2 条作品 role=creator status=in_progress |
| 3 | 点击作品卡片跳转作品详情页 | PASS | MyWorkCard 用 `<Link to={`/work/${work.id}`}>`，与广场页一致跳转 WorkDetailPage |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 GET /api/users/me、GET /api/users/me/works 单元/集成测试通过 | PASS | test_t023_users.py 11 测试全过（资料 4 + 作品 7） |
| 2 | frontend/src/services/users.ts 已将 Mock 替换为真实后端 API | PASS | users.ts 本就是真实 Axios 调用（getUserProfile/getMyWorks），无 Mock 分支，T-023 无需改动 |
| 3 | 后端能验证个人主页请求命中真实后端 | PASS | 真实联调：curl GET /api/users/me（token）→ 200 含真实资料+统计；GET /api/users/me/works → 200 含 role/status/thumb_url；无 token → 401 |
| 4 | P08 页面不展示 [Mock] 数据 | PASS | ProfilePage docstring 清理 Mock 字样，MyWorkCard thumb 用真实 thumb_url。getUserProfile/getMyWorks 全真实调用，无 [Mock] 数据 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | Vite proxy /api → 8099（T-006 已配，T-023 复用） |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 47 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build | PASS | built 通过（chunk size 警告非阻塞） |

## 后端分层实现

| 层 | 文件 | 职责 |
|----|------|------|
| 模型 | src/models/user.py（扩展） | 新增 UserProfileResponse（资料+统计）/ MyWorkItemResponse（列表项含 role/status/thumb_url）/ MyWorkListResponse |
| 数据访问 | src/repositories/user.py（扩展） | 新增 count_participated（ChainMember 计数）/ count_created（Chain.creator_id 计数）/ list_my_works（creator OR member，distinct 去重，分页+倒序） |
| 业务服务 | src/services/user.py（扩展） | 新增 get_profile（user+统计）/ list_my_works（chains+role 判定+thumb_url 查询），构造函数注入 WorkRepository（查 thumb_url） |
| 路由 | src/api/routes/users.py（新建） | GET /api/users/me + GET /api/users/me/works，需登录鉴权，LookupError→404 |

## 关键设计决策

### 1. list_my_works 范围含 in_progress（区别于广场）

广场 GET /api/works 只查 completed 链；个人主页 GET /api/users/me/works 查用户参与/创建的所有链（含 in_progress + completed）。前端 MyWorkCard 有"进行中"label，说明期望显示用户参与的所有链。list_my_works 不加 status 过滤。

### 2. role 判定（creator / participant）

chain.creator_id == user_id → "creator"，否则 "participant"（用户是成员但非创建者）。list_my_works 范围含 creator OR member，role 在 service 层按 creator_id 判定。创建者既是 creator 又是 member，但 role 标 creator（优先）。

### 3. list_my_works 的 OR + distinct 去重

用户参与的链（ChainMember.user_id==）OR 创建的链（Chain.creator_id==）可能重叠（创建者也是成员）。SQLAlchemy `select(Chain).where(creator_id==user_id | id.in_(member_chain_ids)).distinct()` 去重，避免创建者链出现两次。

### 4. thumb_url 复用 WorkRepository.get_thumb_url

thumb_url 取链第一个 draw 节点的 content_url（与广场页一致）。list_my_works 逐个 chain 调 work_repo.get_thumb_url（N+1，链数有限可接受；MVP 简单清晰）。UserService 注入 WorkRepository（参照 VoteService 多 repo 注入）。

### 5. datetime → str 用 isoformat（service 层转换）

ORM 的 created_at 是 datetime 对象，Pydantic 模型声明 str。service 层构造 dict 时手动 `.isoformat()` 转 str（与 T-020 WorkService 一致），不靠 Pydantic 自动转换（避免 datetime 序列化格式不一致）。

### 6. UserService 构造函数 work_repo 可选

`__init__(self, repo, work_repo=None)`。auth 路由 register/login 只需 user_repo（不查 thumb），传一个参数即可；users 路由 get_me/get_my_works 传两个（user_repo + work_repo）。work_repo 可选保持 auth 路由兼容（不破坏现有 register/login）。

## 真实联调验证

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | 注册 userA（主页甲） | 200 + access_token |
| 2 | userA GET /api/users/me（新用户） | participated=0 / created=0 |
| 3 | userA GET /api/users/me/works（空） | total=0 |
| 4 | userA 建链 + 提交 seq=0 draw（造 thumb_url） | 200 + chain_status=in_progress |
| 5 | userA GET /api/users/me（建链后） | participated=2 / created=2 |
| 6 | userA GET /api/users/me/works | 2 条，role=creator，status=in_progress，thumb_url 有值 |
| 7 | 注册 userB（主页乙） | 200 |
| 8 | userB GET /api/users/me | participated=0 / created=0（看不到 userA 活动） |
| 9 | userB GET /api/users/me/works | total=0（防越权，看不到 userA 的链） |
| 10 | 无 token GET /api/users/me | 401 |
| 11 | 无 token GET /api/users/me/works | 401 |

## 测试清单

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_get_profile_basic | 个人资料含 nickname/username/created_at | PASS |
| test_get_profile_stats_zero | 新用户参与=0/创建=0 | PASS |
| test_get_profile_stats_after_activity | 建链+加入后 participated/created 正确 | PASS |
| test_get_profile_no_token | 无 token → 401 | PASS |
| test_my_works_empty | 无作品 → 空列表 | PASS |
| test_my_works_as_creator | 创建者作品 role=creator | PASS |
| test_my_works_as_participant | 参与者作品 role=participant | PASS |
| test_my_works_includes_in_progress | 含进行中链（status=in_progress） | PASS |
| test_my_works_pagination | 分页 | PASS |
| test_my_works_no_token | 无 token → 401 | PASS |
| test_my_works_not_in_others | 用户看不到他人参与/创建的链（防越权） | PASS |

## 回归

- pytest 全量：103 passed（T-001~T-023 累计，无回归）
- ruff src+tests：All checks passed!
- mypy src：Success: no issues found in 47 source files
- 前端 type-check/lint/build：全过
