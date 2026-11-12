# 测试报告：T-022 通知功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> GET /api/notifications（通知列表+unread_only+分页）+ POST /api/notifications/read（标记已读）+ submit 路由层通知生成（your_turn/node_submitted/chain_done）全部命中真实后端，通知闭环验证通过：节点提交后自动生成站内通知（下一位责任人收 your_turn、所有成员收 node_submitted、链完成所有成员收 chain_done）+ 通知持久化到 DB（离线用户登录可见）+ 列表分页/unread_only 过滤 + 批量标记已读（防越权，只标记自己的）。前端 AppHeader 已完整接入真实 API（getNotifications/readNotifications 真实调用，无 Mock 分支），铃铛下拉显示真实通知列表。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 节点提交后，下一位责任人收到「轮到你了」通知 | PASS | submit 路由层 chain_status != completed 时，取 data.next_author_id → notif_repo.create(next_author_id, "your_turn", ...)。真实联调：creator 提交 seq=0 → member2 通知列表含 your_turn（轮转 idx=1%2=1→member2） |
| 2 | 节点提交后，所有成员收到「节点提交」通知 | PASS | submit 路由层 chain_status != completed 时，notif_repo.create_many 给全部 member_user_ids 发 node_submitted。真实联调：creator 提交 seq=0 → member2 + creator 均收 node_submitted |
| 3 | 链完成后，所有成员收到「链完成」通知 | PASS | submit 路由层 chain_status == completed 时，notif_repo.create_many 给全部 member_user_ids 发 chain_done。真实联调：链完成（seq=3 提交）→ member2 + creator 均收 chain_done |
| 4 | 用户在顶部铃铛看到通知列表（含类型/链标题/已读状态） | PASS | GET /api/notifications → items 含 type/chain_id/chain_title/read/created_at。真实联调：member2 列表 6 条（your_turn×2/node_submitted×3/chain_done×1），creator 列表 5 条 |
| 5 | 用户可批量标记通知已读 | PASS | POST /api/notifications/read {notification_ids} → read_count。真实联调：member2 标记 1 条 your_turn → read_count=1，unread_only 查询剩 1 条 |
| 6 | 未读/已读状态正确区分 | PASS | unread_only=true 只返回 read=False。真实联调：标记后 unread_only 查询 your_turn 已读不再出现，剩 node_submitted |
| 7 | 无登录访问通知 → 401 | PASS | GET /api/notifications 无 token → 401。测试 test_list_notifications_no_token 验证 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 GET /api/notifications、POST /api/notifications/read 单元/集成测试通过 | PASS | test_t022_notifications.py 10 测试全过（列表 5 + 已读 3 + submit 通知生成 2） |
| 2 | frontend/src/services/notifications.ts 已将 Mock 替换为真实后端 API | PASS | notifications.ts 本就是真实 Axios 调用（getNotifications/readNotifications），无 Mock 分支，T-022 无需改动 |
| 3 | 后端能验证通知请求命中真实后端 | PASS | 真实联调：curl GET /api/notifications（token）→ 200 含真实通知；POST /api/notifications/read → read_count；无 token → 401 |
| 4 | AppHeader 铃铛不展示 [Mock] 数据 | PASS | AppHeader getNotifications/readNotifications 全真实调用，无 [Mock] 分支 |
| 5 | frontend/vite.config.ts 的 /api 代理配置正确 | PASS | Vite proxy /api → 8099（T-006 已配，T-022 复用） |
| 6 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 46 source files |

## 后端分层实现

| 层 | 文件 | 职责 |
|----|------|------|
| 模型 | src/models/notification.py | NotificationItemResponse/NotificationListResponse/NotificationReadRequest/NotificationReadResponse（Pydantic） |
| 数据访问 | src/repositories/notification.py | NotificationRepository：create（单条）/ create_many（批量）/ list_by_user（分页+unread_only+倒序，返回 list+total）/ mark_read（批量 UPDATE，只标记自己的，防越权） |
| 业务服务 | src/services/notification.py | NotificationService：list_notifications（分页+unread_only → {items,total,page,page_size}）+ mark_read（→ {read_count}） |
| 路由 | src/api/routes/notifications.py | GET /api/notifications（page/page_size/unread_only Query）+ POST /api/notifications/read，需登录鉴权 |
| 触发点 | src/api/routes/nodes.py submit 路由 | service.submit_node 成功后（与 WS notify 同位置），路由层用 ChainRepository 查成员 + NotificationRepository 写 DB 通知 |

## 关键设计决策

### 1. 通知生成放路由层（不放 service 层）

通知生成需 chain 成员列表 + 下一位责任人，与 T-019 WS notify 同位置同语义。放路由层（nodes.py submit），service 层（NodeService）不感知通知模块，保持分层约束（service 只依赖 repository，不引入 NotificationRepository）。路由层用 ChainRepository.get_members 查成员 + NotificationRepository 写通知。

### 2. NodeService.submit_node 返回值补 next_author_id

原 submit_node 返回 {node_id, seq, status, next_seq, chain_status}，路由层无法知道下一位责任人。补 `next_author_id: str | None`（函数内已按成员轮转 idx=next_seq%member_count 计算好，只需加到返回值）。路由层据此给下一位发 your_turn 通知。链完成时 next_author_id=None（不创建下一节点）。

### 3. 通知持久化（DB）与实时推送（WS）双轨

- **WS notify**（T-019 已实现）：在线用户即时感知，submit 路由层 ws_manager.broadcast_notify
- **DB 通知**（T-022 新增）：持久化到 Notification 表，离线用户登录后 GET /api/notifications 可见

两者同位置同语义（submit 路由层），互不替代：WS 是即时推送（不保证送达，用户离线则丢），DB 是持久化兜底（保证可见）。

### 4. mark_read 防越权

UPDATE Notification SET read=True WHERE id IN (...) AND user_id == current_user.id AND read.is_(False)。WHERE 子句带 user_id 过滤，用户无法标记他人通知（即使传入他人 notification_id，rowcount=0）。测试 test_mark_read_only_own 验证：A 尝试标记 B 的通知 → read_count=0。

### 5. get_db 自动 commit

src/db/session.py 的 get_db 在 yield 后 `await session.commit()`（成功时提交，异常时 rollback）。路由层通知生成只需 add/flush，不需显式 commit，commit 由 get_db 依赖统一处理（与 NodeService.submit_node 内部只 flush 不 commit 一致）。

### 6. 测试轮转稳定性（joined_at 显式设值）

测试环境同事务快速执行，ChainMember 的 server_default=func.now() 时间戳可能相同，导致 `members.sort(key=lambda m: m.joined_at)` 排序不稳定，轮转 idx 取错人 → next_author_id 错位（test_t017 同款问题）。解法：extra_members 显式设 joined_at = now + (i+1)秒，保证创建者在前、后续成员按加入顺序在后。

## 真实联调验证

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | 注册 creator + member2 | 200 + access_token |
| 2 | creator 建链（chain_length=4） | 200 + chain_id |
| 3 | member2 加入链（/join） | 200 + joined=true |
| 4 | creator 提交 seq=0 draw | 200 + chain_status=in_progress + next_seq=1 |
| 5 | 查 member2 通知 | 2 条：your_turn + node_submitted |
| 6 | 查 creator 通知 | 1 条：node_submitted（无 your_turn，creator 不是下一位） |
| 7 | member2 标记 your_turn 已读 | read_count=1 |
| 8 | member2 unread_only 查询 | 剩 1 条 node_submitted |
| 9 | member2 提交 seq=1 describe | 200 + chain_status=in_progress + next_seq=2 |
| 10 | creator 提交 seq=2 draw | 200 + next_seq=3 |
| 11 | member2 提交 seq=3 describe | 200 + chain_status=completed |
| 12 | 查 member2 通知（链完成后） | 6 条：your_turn×2 + node_submitted×3 + chain_done×1 |
| 13 | 查 creator 通知（链完成后） | 5 条：your_turn×1 + node_submitted×3 + chain_done×1 |

通知类型、轮转责任人（idx=seq%member_count）、已读状态、持久化全部正确。

## 测试清单

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_list_notifications_empty | 无通知 → 空列表 | PASS |
| test_list_notifications_returns | 有通知 → 列表含 type/chain_title/read | PASS |
| test_list_notifications_unread_only | unread_only=true 只返回未读 | PASS |
| test_list_notifications_pagination | 分页 | PASS |
| test_list_notifications_no_token | 无 token → 401 | PASS |
| test_mark_read_success | 标记已读 → read_count + 再查已读 | PASS |
| test_mark_read_only_own | 只标记自己的通知（防越权） | PASS |
| test_mark_read_empty_ids | 空 ids → read_count=0 | PASS |
| test_submit_generates_your_turn_notification | submit 后下一位收到 your_turn + 成员收到 node_submitted | PASS |
| test_submit_generates_chain_done_notification | 链完成 submit 后成员收到 chain_done | PASS |

## 回归

- pytest 全量：92 passed（T-001~T-022 累计，无回归）
- ruff src+tests：All checks passed!
- mypy src：Success: no issues found in 46 source files
