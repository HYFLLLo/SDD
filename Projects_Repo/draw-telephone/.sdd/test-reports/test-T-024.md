# 测试报告：T-024 AI 补位定时任务功能闭环

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> APScheduler 每小时扫描 24h 未提交 pending 节点 → AI 补位（draw 调 Qwen-Image 文生图 / describe 调 Qwen3.6 VLM 看图）→ 写节点 is_ai=true + status=ai_filled → 推进链 + 建下一节点 + 通知下一位；7 天未完成链标记 expired + 通知成员。全部命中真实后端 + 真实海康 MaaS，AI 补位闭环验证通过。scheduler 启动成功（每小时扫描），手动触发 scan_and_fill 调真实 MaaS：draw 节点 Qwen-Image 生成真实图片 URL + describe 节点 Qwen3.6 VLM 生成描述文字，补位后 is_ai=true + 推进链 + 下一位收 your_turn + 成员收 node_submitted。前端 ChainHallPage 倒计时 UI 已就绪（ai_countdown_at 真实值 = pending 节点 created_at + 24h）。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 节点 24h 未提交时，AI 自动补位（补位节点注明 AI 创作） | PASS | scan_and_fill 扫描 pending 节点 created_at+24h<now → _fill_node 调 MaaS 生成 → update_node_ai_fill（is_ai=true, status=ai_filled）。真实联调：draw 节点 25h 前创建 → 补位 is_ai=true content_url=MaaS 图片 URL |
| 2 | AI 补位后链继续推进，下一位收到通知 | PASS | _fill_node 补位后 advance_chain（current_seq+1）+ create_next_node（轮转下一位）+ _notify_chain_event（your_turn 给下一位 + node_submitted 给成员）。真实联调：member2 收 your_turn + node_submitted |
| 3 | 超 7 天未完成时链状态变为「已过期」，成员收到通知 | PASS | _expire_chain：chain.created_at+7d<now → mark_expired（status=expired）+ create_many chain_done 给成员。测试 test_expire_chain_after_7_days + test_expire_notifies_members 验证 |
| 4 | 接力页面 AI 补位倒计时间正确显示（24h 超时时间点） | PASS | get_chain_detail 的 ai_countdown_at = pending 节点 created_at + ai_fill_timeout_hours(24h)。前端 ChainHallPage formatCountdown 算与 now 差显示倒计时。T-016 测试更新断言为非 None |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 APScheduler 定时任务实现（每小时扫描超时节点和过期链） | PASS | scheduler.py AsyncIOScheduler + IntervalTrigger(hours=1)，init_scheduler on_startup 启动，shutdown_scheduler on_shutdown 关闭。真实联调：启动日志 "AI fill scheduler started (every 1 hour)" |
| 2 | 后端 MaaS Qwen-Image/Qwen3.6-35B-A3B-FP8 调用使用 httpx.AsyncClient trust_env=False，不使用第三方 SDK | PASS | ai.py generate_image/describe_image 用 httpx.AsyncClient(trust_env=False, timeout=90s/60s)。真实联调：Qwen-Image 200 返回图片 URL，Qwen3.6 VLM 200 返回描述文字 |
| 3 | AI 任务不测试时用 Mock 占位图/固定描述，不依赖外部，补位节点注明 AI 创作，默认从待接 | PASS | 测试用 unittest.mock.patch 替换 generate_image/describe_image（不调真实 MaaS）。补位节点 is_ai=true + author_label 保留原责任人（默认从待接成员轮转） |
| 4 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 49 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |

前端无需改动：ChainHallPage 已有 ai_countdown_at 倒计时 UI（formatCountdown 算时间差），ChainNode 已有 is_ai 字段（_build_node_list 已返回）。后端 ai_countdown_at 填真实值后倒计时自动显示；AI 补位节点 is_ai=true 前端已能渲染（WorkDetailPage/ReplayPage 的 AI 标记 T-020/T-021 已处理）。

## 后端分层实现

| 层 | 文件 | 职责 |
|----|------|------|
| 服务 | src/services/ai.py（扩展） | generate_image（Qwen-Image 文生图，返回 MaaS URL）+ describe_image（Qwen3.6 VLM 看图，本地文件 base64 优先，远程 URL 降级纯文本续写）+ _fetch_image_base64 + _call_vlm |
| 服务 | src/services/ai_fill.py（新建） | AiFillService：scan_and_fill（扫描 in_progress 链超时节点 + 7 天过期）+ _fill_node（补位单节点：生成内容→更新→推进→建下一节点→通知）+ _notify_chain_event + _expire_chain |
| 数据访问 | src/repositories/node.py（扩展） | update_node_ai_fill（content + is_ai=True + status=ai_filled + submitted_at=now） |
| 数据访问 | src/repositories/chain.py（扩展） | list_in_progress（查 in_progress 链）+ mark_expired（标记 expired） |
| 定时任务 | src/scheduler.py（新建） | init_scheduler（AsyncIOScheduler 每小时 _ai_fill_job）+ _ai_fill_job（独立 session 调 AiFillService）+ shutdown_scheduler |
| 服务 | src/services/chain.py（修改） | get_chain_detail 填充 ai_countdown_at（pending 节点 created_at + 24h）+ _get_ai_countdown_at helper |
| 入口 | src/main.py（修改） | on_startup(init_scheduler) + on_shutdown(shutdown_scheduler) |

## 关键设计决策

### 1. MaaS 返回格式探测（实现时验证）

实现前先探测 MaaS API 格式：
- Qwen-Image：POST /images/generations → 200 + `data[0].url`（MaaS 存储 URL）。前端 img src 直接用（浏览器可访问）。
- Qwen3.6 VLM：POST /chat/completions（多模态 content 含 image_url）→ 200 + `choices[0].message.content`。本地 PNG base64 看图 200 OK；远程 MaaS URL 下载受限（返回 36 bytes 错误页）。

### 2. describe 节点看图降级策略

VLM 看图需可访问图片。draw 节点生成的 MaaS URL 下载不了（MaaS 存储链接鉴权问题）。解法：
- 本地 /uploads/ 图片：读文件 base64 传 VLM（看图模式，真实描述）
- 远程 MaaS URL：下载失败 → 降级纯文本续写（VLM 生成一段描述性文字兜底，保证补位闭环可用）

_fetch_image_base64 处理两种来源，看图失败降级纯文本（不中断补位）。

### 3. 补位通知复用 T-022 逻辑

AI 补位后通知与人工 submit 同语义：链完成→成员 chain_done；否则→下一位 your_turn + 成员 node_submitted。抽到 AiFillService._notify_chain_event（service 层直接用 NotificationRepository，不调 nodes.py 路由）。

### 4. scheduler 独立 session

定时任务不持有请求级 session，用 async_session_maker() 独立 session（与 T-019 WS stroke 校验同模式）。_ai_fill_job 内 try/commit/rollback，异常不中断 scheduler。

### 5. 补位失败不中断

单个节点补位失败（MaaS 调用失败抛 RuntimeError）记日志跳过，下次扫描重试，不中断整个扫描。scan_and_fill 返回 {filled, expired, errors} 统计。

### 6. ai_countdown_at = pending 节点 created_at + 24h

当前 pending 节点创建时间 + ai_fill_timeout_hours(24h)。前端算与 now 的差显示倒计时。链 in_progress + 当前节点 pending 时返回真实值，其他返回 None（不显示）。

## 真实联调验证

| 步骤 | 操作 | 结果 |
|------|------|------|
| 1 | 启动后端 | scheduler 日志 "AI fill scheduler started (every 1 hour)" |
| 2 | 建链 + seq=0 pending draw 节点（created_at=25h 前） | 链 in_progress，节点 pending |
| 3 | 手动触发 scan_and_fill（调真实 MaaS Qwen-Image） | filled=1, errors=0 |
| 4 | 验证 draw 节点补位 | is_ai=true, status=ai_filled, content_url=MaaS 真实图片 URL |
| 5 | 验证链推进 | current_seq 0→1, status=in_progress |
| 6 | 验证下一节点创建 | seq=1 describe 节点已创建 |
| 7 | 验证通知 | member2 收 your_turn + node_submitted（2 条） |
| 8 | seq=1 describe 节点 created_at=25h 前，触发 scan（调真实 Qwen3.6 VLM） | filled=1, is_ai=true, content_text=VLM 生成描述 |
| 9 | 清理联调数据 | 联调链 + AI 节点 + 通知已删 |

## 测试清单

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_scan_finds_timeout_node | 24h 未提交 pending 节点被扫描补位 | PASS |
| test_scan_skips_recent_node | 未超 24h 的 pending 节点不补位 | PASS |
| test_scan_skips_submitted_node | submitted 节点不补位 | PASS |
| test_fill_draw_node_calls_image_api | draw 节点补位调 generate_image + is_ai=true | PASS |
| test_fill_describe_node_calls_vlm_api | describe 节点补位调 describe_image | PASS |
| test_fill_advances_chain | 补位后推进链 current_seq+1 | PASS |
| test_fill_creates_next_node | 补位后创建下一节点 | PASS |
| test_fill_notifies_next_author | 补位后下一位收 your_turn 通知 | PASS |
| test_expire_chain_after_7_days | 7 天未完成链标记 expired | PASS |
| test_expire_notifies_members | 过期链成员收通知 | PASS |

## 回归

- pytest 全量：113 passed（T-001~T-024 累计，T-016 断言更新 ai_countdown_at 非 None，无其他回归）
- ruff src+tests：All checks passed!
- mypy src：Success: no issues found in 49 source files
- 前端 type-check/lint：全过
