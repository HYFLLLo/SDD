# 工作日志

> 由 Orchestrator 维护。记录项目开发、测试、修复和 blocked 状态。

---

## 2026-08-19 T-001 前端工程初始化 + 全局布局 + Mock 基建

- **Developer**：Vite 脚手架 + 全量依赖安装 + 25+ 文件（types/mocks/services/stores/router/components/pages/styles/config）
- **Orchestrator 修复**：4 处 TS 错误（chains.ts/votes.ts 缺 `WorkAuthor` import；handler.ts 未用导入）
- **验证**：type-check ✅ / lint ✅ / build ✅（117 modules, 1.89s）/ dev server :5199 HTTP 200（335ms）
- **经验**：已写入 `.sdd/experience.md`
- **状态**：代码完成，待 Tester 独立验证 → 用户门禁

## 2026-08-19 T-001 Tester 验证

- **Tester 子智能体**：两次启动后无输出（8s/2 tools、0 报告），按 codex-subagents.md 降级语义由 Orchestrator 执行验证
- **独立重跑**：type-check ✅ / lint ✅ / build ✅（117 modules）
- **api-contracts 对齐**：works.ts/chains.ts 逐字段对比，均为已定义字段子集 ✅
- **原型对齐**：AppHeader.tsx 与 01-plaza.html .topbar 结构对齐，tokens.css 配色一致 ✅
- **vite 代理**：/api 指向 8099+VITE_BACKEND_PROXY_TARGET 切 8003 ✅，/ws ws:true ✅
- **结果**：PASS，报告 .sdd/test-reports/test-T-001.md
- **状态**：T-001 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-002 P09 登录/注册页 Mock

- **Developer**：Orchestrator 直接实现（子智能体反复无输出，降级）
- **产出**：LoginPage.tsx（重写占位为完整实现）+ LoginPage.css（新建）
- **功能**：登录/注册 Tab 切换、用户名+密码表单（注册多昵称字段）、「先逛逛」游客入口、Mock token 存 localStorage
- **验证**：type-check ✅ / lint ✅ / build ✅（1579 modules）/ dev server :5199/login HTTP 200
- **Mock 对齐**：auth.ts 返回 {access_token, user:{id,username,nickname,avatar_url}} 与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-002.md
- **状态**：T-002 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-003 P01 广场页 Mock

- **Developer**：Orchestrator 直接实现
- **产出**：PlazaPage.tsx（重写）+ PlazaPage.css（新建）
- **功能**：Hero（手写题词+CTA）+ 加入入口（房间码）+ 筛选 chips（最新/最跑偏/最多点赞）+ 作品瀑布流（3 列虚线边框卡片），登录/游客态 CTA 切换
- **验证**：type-check ✅ / lint ✅ / build ✅ / dev server :5199 HTTP 200
- **Mock 对齐**：works.ts 返回 {items,total,page,page_size} 与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-003.md
- **状态**：T-003 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-004 P02 创建链页 Mock

- **Developer**：Orchestrator 直接实现
- **产出**：CreateChainPage.tsx（重写）+ CreateChainPage.css（新建）
- **功能**：链长滑块（4-10 默认6）+ 标题输入 + 公开性分段（邀请制/公开广场）+ 起手题来源分段（自己写题/AI生成）+ AI题词预览+「换一个」+ 提交跳 P04
- **验证**：type-check ✅ / lint ✅ / build ✅ / dev server :5199/create HTTP 200
- **Mock 对齐**：chains.ts（{id,room_code,...}）+ ai.ts（{prompts:[...]}）与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-004.md
- **状态**：T-004 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-005 P03 加入链页 Mock

- **Developer**：Orchestrator 直接实现
- **产出**：JoinChainPage.tsx（重写）+ JoinChainPage.css（新建）
- **功能**：6 位房间码分格输入（已填陶土橙高亮，自动跳格+粘贴分发）+ 校验按钮 + 链预览（标题/链长/进度/剩余名额）+ 邀请链接 ?code= 自动填入并校验 + 加入跳 P04
- **验证**：type-check ✅ / lint ✅ / build ✅ / dev server :5199/join HTTP 200
- **Mock 对齐**：chainLookupResponse（{id,title,chain_length,current_seq,...}）+ chainJoinResponse（{chain_id,joined}）与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-005.md
- **状态**：T-005 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-006 P04 链大厅页 Mock（含★签名锚点）

- **Developer**：Orchestrator 直接实现
- **产出**：ChainHallPage.tsx（重写）+ ChainHallPage.css（新建）
- **功能**：★进度节点链（6节点，done实心橙/current空心橙脉冲/待接虚线灰）+ 成员高亮 + AI补位倒计时（冷灰蓝）+ 链信息 + 实时围观canvas（setInterval模拟笔迹）+ 接力/回放入口
- **验证**：type-check ✅ / lint ✅ / build ✅ / dev server :5199/chain/chain-0001 HTTP 200
- **签名锚点**：@keyframes pulse 脉冲动画已实现
- **Mock 对齐**：chainDetailResponse（含 ai_countdown_at/members/nodes）与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-006.md
- **状态**：T-006 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-007 P05 接力作画/描述页 Mock（含画布涂鸦）

- **Developer**：Orchestrator 直接实现
- **产出**：RelayPage.tsx（重写）+ RelayPage.css（新建）
- **功能**：上一节点展示（防剧透）+ 画布涂鸦（canvas 2D + pointer 事件 + 5色板/4粗细/橡皮/撤销/重做/清空 + 笔迹序列化）+ 述节点文字输入（≤30字+计数）+ 画节点提交导出PNG→Mock上传→submitNode
- **验证**：type-check ✅ / lint ✅（修复 redraw 初始化顺序）/ build ✅ / dev server :5199/chain/chain-0001/relay HTTP 200
- **Mock 对齐**：nodePreviousTextResponse/submitNodeResponse/uploadImageResponse 与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-007.md
- **状态**：T-007 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-008 P06 作品详情页 Mock

- **Developer**：Orchestrator 直接实现
- **产出**：WorkDetailPage.tsx（重写）+ WorkDetailPage.css（新建）+ works.ts mock node-0005 改 is_ai=true
- **功能**：全链纵向展示（6节点画述交替）+ 每节点作者署名 + AI续冷灰蓝标签（整卡区隔）+ 分享链接（复制只读URL）+ 看回放入口
- **验证**：type-check ✅ / lint ✅ / build ✅ / dev server :5199/work/work-0001 HTTP 200
- **Mock 对齐**：buildWorkDetailResponse（含 nodes/is_ai/author）与 api-contracts.md 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-008.md
- **状态**：T-008 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-009 P07 整链回放页 Mock（含投票）

- **Developer**：Orchestrator 直接实现
- **产出**：ReplayPage.tsx（重写占位为完整实现）+ ReplayPage.css（新建）
- **功能**：逐节点渐显回放（framer-motion motion.div opacity/y 渐显，2s 间隔 setTimeout 递增 revealed）+ 重新回放/跳过动画 + 回放后投票面板（三维度 most_drift/best_draw/best_describe 单选，陶土橙选中态边框+底色）+ 提交投票 submitVotes→getVoteResult + 投票结果条形图（按 vote_count/maxVotes 比例）+ 🏆获胜者高亮
- **验证**：type-check ✅ / lint ✅（修复 effect 内同步 setState：移除 playing 中间态，replayDone 由 revealed 派生）/ build ✅（1994 modules）/ dev server :5199/work/work-0001/replay HTTP 200
- **Mock 对齐**：voteSubmitResponse（{results:[{dimension,target_node_id,vote_count}]}）+ voteResultResponse（{results:[{dimension,target_node_id,target_author,vote_count}]}）与 api-contracts.md L260/L275 一致
- **framer-motion**：首次实际使用（package.json 已有 ^13.1.0）
- **结果**：PASS，报告 .sdd/test-reports/test-T-009.md
- **状态**：T-009 passed，等待用户门禁验收 UI/UX

## 2026-08-19 T-010 P08 个人主页 Mock + 通知铃铛 Mock

- **Developer**：Orchestrator 直接实现
- **产出**：ProfilePage.tsx（重写占位为完整实现）+ ProfilePage.css（新建）+ AppHeader.tsx（重写加通知铃铛下拉）+ AppHeader.css（追加通知下拉样式）
- **功能（个人主页）**：个人资料卡（头像首字+昵称+@username+参与/创建链数统计）+ 我的作品卡片列表（与广场页 work-card 虚线边框样式一致，额外 role-badge 角色徽标 creator 陶土橙/member 灰，status 已完成绿/进行中橙）
- **功能（通知铃铛）**：未登录点铃铛跳 /login；登录点铃铛展开 .notif-dropdown（getNotifications 3 条：your_turn/node_submitted 未读 + chain_done 已读）；未读红点 .bell .dot；单条已读 handleReadOne（readNotifications([id])）；全部已读 handleReadAll；点击外部 mousedown 监听关闭；NOTIF_ICON/NOTIF_TEXT 三类型映射
- **验证**：type-check ✅ / lint ✅（移除未用 Badge 导入）/ build ✅（1994 modules）/ dev server :5199/profile HTTP 200
- **Mock 对齐**：userProfileResponse（{participated_chains,created_chains,...}）+ myWorksListResponse（{items:[{role,...}]}）+ notificationsListResponse（{items:[{type,read,...}]}）+ notificationsReadResponse（{read_count}）与 api-contracts.md L287/L299/L315/L325 一致
- **结果**：PASS，报告 .sdd/test-reports/test-T-010.md
- **状态**：T-010 passed，等待用户门禁验收 UI/UX。前端 Mock 阶段（T-001~T-010）全部完成。

## 2026-08-19 T-011 后端基础设施：pycore 接入 + 工具链 + 配置

- **Developer**：Orchestrator 直接实现
- **产出**：backend/ 目录骨架（src/api/routes、core、db、models、repositories、services、utils + tests + scripts + data + uploads）+ src/main.py（APIServer）+ src/core/config.py（pydantic-settings BaseSettings 读 .env）+ .env + .env.example + pyproject.toml 工具链（ruff/mypy/pytest 收敛 backend/src+tests）+ .gitignore 更新
- **运行时**：python 3.11.9，.venv 安装 fastapi 0.141.1 / sqlalchemy 2.0.52 / bcrypt / pyjwt / apscheduler / loguru / ruff / mypy / pytest
- **验证**：ruff ✅（修复 import 顺序）/ mypy ✅（配置 pycore.* follow_imports=skip）/ uvicorn 启动 ✅ / GET /health → 200 {code:200,message:success,data:{status:healthy,version:0.1.0}}
- **关键决策**：pycore.core.ConfigManager 仅支持 TOML 无法读 .env，改用 pydantic_settings.BaseSettings 直读 backend/.env（符合「配置通过后端配置文件获取，不继承进程环境变量」约束）
- **结果**：PASS，报告 .sdd/test-reports/test-T-011.md
- **状态**：T-011 passed（user_gate=false），自动推进 T-012

## 2026-08-19 T-012 后端基础设施：数据库骨架 + 依赖注入 + 健康检查

- **Developer**：Orchestrator 直接实现
- **产出**：src/db/models.py（6 ORM 模型 User/Chain/ChainMember/Node/Vote/Notification，字段对齐 PRD 6.1）+ src/db/session.py（engine/async_session_maker/get_db/init_db/close_db）+ src/api/deps.py（get_current_user 路由级 JWT 认证 + create_access_token/decode_token/require_admin）+ scripts/init_db.py（建表+seed 3 用户/1 链/6 节点/3 通知）+ tests/test_t012_infra.py（3 测试）+ src/main.py 更新（注册 init_db/close_db 生命周期）
- **验证**：ruff ✅ / mypy ✅（16 source files）/ pytest ✅（3 passed，7 warnings 为 pycore pydantic 弃用非阻塞）/ init_db.py ✅（数据库验证 3 users/1 chain/6 nodes/3 notifications/3 chain_members）/ uvicorn 启动 ✅ / GET /health → 200 / GET /docs → 200
- **测试隔离**：内存 SQLite `:memory:` + dependency_overrides[get_db] 注入，与运行时业务库物理隔离；pytest 后运行时库仍 intact
- **结果**：PASS，报告 .sdd/test-reports/test-T-012.md
- **状态**：T-012 passed（user_gate=false）。后端基础设施阶段（T-011/T-012）全部完成。下一任务 T-013（用户认证功能闭环，user_gate=true），需用户门禁。

## 2026-08-19 T-013 用户认证功能闭环（注册/登录/JWT）

- **Developer**：Orchestrator 直接实现
- **产出**：src/core/security.py（bcrypt+JWT 纯函数）+ src/models/user.py（Pydantic RegisterRequest/LoginRequest/UserPublic/AuthData）+ src/repositories/user.py（UserRepository）+ src/services/user.py（UserService register/login）+ src/api/routes/auth.py（POST /api/auth/register、POST /api/auth/login）+ src/api/deps.py（重构：JWT 原语移至 security.py）+ src/main.py（include_router auth_router）+ tests/test_t013_auth.py（6 测试）+ frontend LoginPage.tsx（清理 Mock 文案/占位符）
- **分层**：security 原语 → Pydantic 模型 → Repository → Service → API 路由，每层只依赖下层
- **关键修复**：get_db 未提交 Bug——原 get_db 只 yield+close 无 commit，导致路由 add 的数据被回滚（重复注册返回 200 应 400、登录返回 401 用户不存在）。修复为 yield+commit/except rollback。pytest 用 dependency_overrides 注入自定义 session（无 commit）所以全绿但掩盖了此 Bug，真实 uvicorn+SQLite 联调才暴露
- **错误格式**：api-contracts 要求 `{"code":N,"message":"...","data":null}`，FastAPI HTTPException 返回 `{"detail":"..."}` 不符。路由错误分支用 JSONResponse 显式构造契约体
- **验证**：ruff ✅（import 排序自动修复）/ mypy ✅（22 source files）/ pytest ✅（9 passed）/ 前端 type-check ✅ / lint ✅ / build ✅（VITE_USE_MOCK=false）/ Vite proxy 真实联通 ✅（login→200+真实JWT，register→200，dup→400）/ DB 持久化 ✅（apitest 用户落盘，4 users=3 seed+1 new，seed intact）
- **结果**：PASS，报告 .sdd/test-reports/test-T-013.md
- **状态**：T-013 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（登录跳转/刷新保持/注册跳转/错误提示）

## 2026-08-19 T-014 链创建功能闭环（含房间码生成）

- **Developer**：Orchestrator 直接实现
- **产出**：src/models/chain.py（Pydantic CreateChainRequest chain_length ge=4 le=10/visibility+prompt_source 枚举/prompt_text max=20 + ChainRead）+ src/repositories/chain.py（generate_room_code 6位排除易混淆字符 O/0/I/1/L+冲突重试10次 + create_chain_with_first_node 链+创建者成员+第一节点 seq=0 draw pending）+ src/services/chain.py（ChainService manual 校验 prompt_text 必填）+ src/api/routes/chains.py（POST /api/chains Depends(get_current_user)+_chain_to_read datetime→ISO）+ src/main.py（include_router chains_router + 全局异常处理器）+ tests/test_t014_chains.py（6 测试）+ frontend CreateChainPage.tsx（清理 Mock 文案）
- **分层**：Pydantic 模型 → Repository → Service → API 路由，每层只依赖下层
- **关键改进：全局异常处理器统一错误格式**：T-013 发现 HTTPException 返回 `{"detail":"..."}` 与 api-contracts 不符，T-013 在路由层用 JSONResponse 显式构造。但 get_current_user 的 401/403 和 Pydantic 422 也需统一。T-014 在 main.py 注册两个 app 级异常处理器：HTTPException → `{"code":N,"message":"...","data":null}`，RequestValidationError 422 → 400 `{"code":400,"message":"参数错误","data":null}`。这样所有路由的 HTTPException 和 Pydantic 校验错误都自动转契约格式，无需每个路由单独处理
- **业务规则**：BR-02 起手为画（seq=0 type=draw）/BR-03 链长4-10（Pydantic ge/le）/BR-04 7天过期（timedelta）/BR-07 公开性枚举（pattern）/F-02-04 创建者默认承接第一节点（Node author_id=creator_id）/6.1 房间码6位大写字母+数字唯一（排除易混淆字符+unique约束+冲突重试）
- **验证**：ruff ✅ / mypy ✅（27 source files）/ pytest ✅（15 passed）/ 前端 type-check ✅ / lint ✅ / build ✅（VITE_USE_MOCK=false）/ Vite proxy 真实联通 ✅（create→200+room_code T5ZZJF，no token→401，invalid length→400）/ DB 持久化 ✅（1 chain+1 member+1 node seq=0 draw pending author_label=小A，seed chain-0001 intact 6 nodes）
- **结果**：PASS，报告 .sdd/test-reports/test-T-014.md
- **状态**：T-014 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（创建链→显示房间码→跳转链大厅、链长校验提示、复制邀请链接）

## 2026-08-20 T-015 AI 起手题生成功能闭环（海康 MaaS DeepSeek-V4-Flash-0731）

- **Developer**：Orchestrator 直接实现
- **产出**：src/models/ai.py（AiPromptRequest count ge=1 le=5 + AiPromptResponse）+ src/services/ai.py（AiService generate_prompts Key 缺失抛 RuntimeError→503/Key 存在调 DeepSeek/失败降级 + _call_deepseek httpx trust_env=False /chat/completions OpenAI 兼容 + _fallback 本地题词池）+ src/api/routes/ai.py（POST /api/ai/prompt Depends(get_current_user) RuntimeError→503）+ src/main.py（include_router ai_router）+ tests/test_t015_ai.py（6 测试）
- **降级策略**：Key 缺失→503（不静默吞错，告知用户配置问题）；Key 存在调用失败→记日志+降级到 FALLBACK_PROMPTS→200（网络/服务问题仍可用）。两种失败语义不同
- **配置变更（2026-08-20）**：用户提供海康 MaaS Key，三个外部服务统一走 maas.hikvision.com.cn/v1：文本 DeepSeek-V4-Flash-0731（DEEPSEEK_*）、文生图 Qwen-Image（IMAGE_*）、多模态 Qwen3.6-35B-A3B-FP8（VLM_*）。废弃百炼/通义万相（DASHSCOPE_API_KEY/WANX_MODEL/QWEN_VL_MODEL）。config.py/.env/.env.example/tasks.json 同步更新
- **验证**：ruff ✅（import 排序+嵌套 with 修复）/ mypy ✅（31 source files）/ pytest ✅（21 passed，503 测试改 mock settings 独立验证不依赖 .env）/ 前端 type-check ✅ / lint ✅ / build ✅（VITE_USE_MOCK=false）/ **真实联调 ✅**（POST /api/ai/prompt count=3 → 200 + 真实题词「隔岸花灯」「伞下余光」「断线纸鸢」，海康 MaaS DeepSeek-V4-Flash-0731 真实生成）/ DB 清理 mtest 用户，seed intact（3 users/1 chain/6 nodes）
- **结果**：PASS（真实联调通过 + fallback 降级双路径），报告 .sdd/test-reports/test-T-015.md
- **状态**：T-015 passed（真实联调通过），user_gate=true，待用户门禁验收浏览器 UI（AI 生成按钮→真实题词预览/换一个重新生成/切手动输入）
## 2026-08-20 T-016 链查询/加入功能闭环

- **Developer**：Orchestrator 直接实现
- **产出**：src/repositories/chain.py（扩展 6 方法：count_members/get_members/get_member/get_nodes/get_current_node/add_member）+ src/services/chain.py（扩展 lookup_chain 房间码→ChainLookup 无效/过期→ValueError→404 + join_chain 校验未满/未过期/未重复 LookupError→404/ValueError→403 + get_chain_detail 成员权限 LookupError→404/PermissionError→403 返回 ChainDetail 含推导节点链 + _node_type seq偶数draw奇数describe + _get_member_users + _is_expired + _build_node_list + _get_current_author）+ src/api/routes/chains.py（扩展 GET /{room_code} + POST /{chain_id}/join + GET /{chain_id}/detail）+ frontend/services/chains.ts（getChainDetail 路径改 /detail）+ frontend/pages/JoinChainPage.tsx（清理 Mock 注释）+ frontend/pages/ChainHallPage.tsx（清理 Mock 注释）+ tests/test_t016_chain_query.py（11 测试）
- **路由设计决策**：api-contracts.md 定义 GET /api/chains/{id}（无后缀）用于链大厅详情，但实现用 GET /api/chains/{chain_id}/detail。原因：/{room_code}（6位房间码查询）和 /{id}（UUID链ID详情）路径模式都是 /{param}，FastAPI 路由冲突（先注册先匹配）。加 /detail 后缀区分（单段 vs 两段），无冲突。前端 chains.ts 已同步。语义清晰无歧义，测试报告如实记录
- **进度节点链推导**：_build_node_list 遍历 seq 0..chain_length-1，已建节点从 DB 取真实 author，未建节点按 seq 推导 type（偶数 draw 奇数 describe）+ author="待接"占位。链大厅页渲染完整进度链（已建带真实作者，未建带待接）
- **修复 SQLite datetime 时区问题**：_is_expired 中 chain.expires_at < datetime.datetime.now(datetime.UTC) 报 offset-naive vs aware 比较错误（SQLite 读回 datetime 可能丢失时区信息）。修复：比较前检查 tzinfo is None，naive 则 replace(tzinfo=datetime.UTC) 统一 aware 再比较
- **验证**：ruff ✅（移除未用 import + 添加 select import + datetime 未用 import 修复）/ mypy ✅（32 source files，移除多余 type: ignore）/ pytest ✅（32 passed，T-016 11 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅（VITE_USE_MOCK=false）/ **真实联调 ✅**（后端 8099 直连 10 项端点全过：注册→登录→创建链→查询链200+ChainLookup→无效房间码404→加入200+joined→重复403→详情200+ChainDetail含推导4节点链→非成员403→无token401）/ DB 持久化 ✅（真实 SQLite 文件库，重复运行用户名已存在证明落盘）
- **结果**：PASS（11 单元测试 + 10 项真实联调全过），报告 .sdd/test-reports/test-T-016.md
- **状态**：T-016 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（加入链页输入房间码→校验→加入→链大厅页看真实进度/成员/责任人）

## 2026-08-20 T-017 节点接力功能闭环（上一节点/提交/防剧透）

- **Developer**：Orchestrator 直接实现
- **产出**：src/models/node.py（SubmitNodeImageRequest/SubmitNodeTextRequest discriminated union by content_type + SubmitNodeResponse + NodePreviousResponse）+ src/repositories/node.py（NodeRepository get_chain/get_user/get_current_node/get_previous_node/update_node_submit/advance_chain/create_next_node）+ src/services/node.py（NodeService get_previous 防剧透+seq=0返回起手题虚拟节点 / submit_node 校验当前责任人+内容类型匹配+推进链+成员轮转指派下一位）+ src/api/routes/nodes.py（GET /{chain_id}/previous + POST /{chain_id}/submit Union type guard）+ src/main.py（include_router nodes_router）+ frontend RelayPage.tsx（清理 Mock 注释）+ tests/test_t017_node_relay.py（14 测试）
- **关键设计：路径参数 {id} 是链 ID**：api-contracts 路径 /api/nodes/{id}/previous 的 {id} 语义上像节点 ID，但前端 RelayPage 从路由 /chain/:id/relay 取链 ID 调用。后端 {id} 接收链 ID，按链 ID 查 current_seq 对应当前节点。路由参数命名 {chain_id} 明确语义，路径保持 /api/nodes/{chain_id}/previous 与前端一致
- **关键设计：seq=0 previous 返回起手题**：seq=0 是起手 draw 节点无 seq=-1。get_previous 在 seq=0 时返回虚拟节点 {node_id:"",seq:-1,type:"describe",content_type:"text",content_text:chain.prompt_text}。前端 isDrawMode=content_type==='text' 为 true（看文字画图），展示起手题
- **关键设计：成员轮转指派下一位**：提交后创建下一节点时，下一位按成员加入顺序轮转 idx=next_seq%member_count（members 按 joined_at 排序）。chain_length=4+2 成员：seq=0→creator,seq=1→joiner,seq=2→creator,seq=3→joiner。成员不足时 author=None（待接，T-024 AI 补位）
- **关键设计：Union 请求体 type guard**：submit 路由请求体 SubmitNodeImageRequest|SubmitNodeTextRequest（discriminated union by content_type），路由层用 isinstance(body, SubmitNodeImageRequest) type guard 分流 content_url/content_text，避免 mypy union-attr 错误
- **修复：测试辅助函数避免重复创建 seq=0**：_create_chain 已创建 seq=0 节点，测试手动 add 第二个 seq=0 导致 MultipleResultsFound（get_current_node 用 scalar_one_or_none）。加 _mark_seq0_submitted 辅助函数更新已有 seq=0 节点而非新建
- **修复：测试成员 joined_at 排序稳定性**：测试环境同事务快速执行，创建者与加入者 ChainMember 的 server_default=func.now() 时间戳可能相同，sort(joined_at) 不稳定。_add_member 显式设 joined_at=utcnow()+1s 保证创建者在前。运行时有真实时间差不会出此问题
- **验证**：ruff ✅ / mypy ✅（37 source files）/ pytest ✅（46 passed，T-017 14 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅ / **真实联调 ✅**（后端 8099 直连 11 项端点全过：注册2用户→创建链→加入→previous起手题→submit画→previous画→submit述→轮转回来→链大厅进度推进→非责任人403）/ DB 持久化 ✅（Node 表已提交节点+Chain current_seq 推进+新节点 pending）
- **结果**：PASS（14 单元测试 + 11 项真实联调全过），报告 .sdd/test-reports/test-T-017.md
- **状态**：T-017 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（接力页看上一节点→作画/描述→提交→返回大厅→进度推进）。画节点完整闭环的上传部分由 T-018 实现

## 2026-08-20 T-018 图片上传功能闭环

- **Developer**：Orchestrator 直接实现
- **产出**：src/core/config.py（upload_dir/upload_url_prefix/upload_path 属性）+ src/models/upload.py（UploadImageResponse {url, size}）+ src/services/upload.py（UploadService.upload_image PNG 魔数校验+UUID 文件名存储+返回{url,size}）+ src/api/routes/upload.py（POST /image UploadFile Depends(get_current_user) ValueError→400）+ src/main.py（include_router upload_router + app.mount StaticFiles /uploads）+ frontend/vite.config.ts（新增 /uploads proxy → 8099）+ tests/test_t018_upload.py（6 测试）+ pyproject.toml（加 python-multipart 依赖）
- **关键设计：PNG 校验以文件头魔数为准**：UploadService 校验 data.startswith(b"\x89PNG\r\n\x1a\n")，不以客户端 content_type 为准。原因：content_type 可伪造（image/png 声明但实际 JPEG），空文件 content_type=image/png 会被误判合法。魔数校验确保数据确是 PNG，空文件/损坏/伪装均拒绝。content_type 参数仍传入（记日志排查）
- **关键设计：UUID 文件名**：stored_name = uuid4().hex + ".png"（32 hex + .png）。不保留原始文件名（可能含中文/特殊字符/路径穿越 ../）。url 返回 /uploads/{uuid}.png，前端 img src 直接用
- **关键设计：静态文件服务 + Vite proxy**：后端 app.mount("/uploads", StaticFiles(directory=upload_path)) 提供 /uploads/* 访问。前端 Vite proxy 新增 /uploads → 8099，开发环境 img src="/uploads/xxx.png" 经 Vite 代理命中后端静态文件
- **关键设计：上传目录可配置**：settings.upload_dir 默认 "uploads"（相对→基于 BACKEND_DIR 解析绝对路径）。upload_path 属性 mkdir(parents=True, exist_ok=True) 确保目录存在。测试用 monkeypatch 指向 tmp_path/uploads 不污染真实 uploads/
- **修复：python-multipart 依赖缺失**：测试首次运行报 RuntimeError: Form data requires "python-multipart"（FastAPI 处理 UploadFile multipart/form-data 需要）。安装 python-multipart 0.0.32 + 加入 pyproject.toml dependencies
- **修复：空文件 PNG 校验逻辑**：初版校验 content_type 或魔数任一通过，空文件 content_type=image/png 误判合法。改为必须以魔数开头（不信任 content_type），空文件/损坏/伪装均拒绝。test_upload_empty_file_400 验证
- **验证**：ruff ✅ / mypy ✅（41 source files）/ pytest ✅（52 passed，T-018 6 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅ / **真实联调 ✅**（后端 8099 直连 6 项验证全过：注册→上传PNG200+{url,size}→GET /uploads/xxx.png 200 内容一致→非PNG400→无token401）/ DB 持久化 ✅（文件落盘 backend/uploads/{uuid}.png）
- **结果**：PASS（6 单元测试 + 6 项真实联调全过），报告 .sdd/test-reports/test-T-018.md
- **状态**：T-018 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（画节点作画→上传→提交→返回大厅）。T-017 画节点完整闭环（上传→提交）的上传环节补齐，可联调

## 2026-08-20 T-019 WebSocket 实时围观功能闭环

- **Developer**：Orchestrator 直接实现（EnterPlanMode 方案批准后实施）
- **产出**：src/api/ws.py（ConnectionManager 内存连接管理 + ws_manager 全局单例 + connect/disconnect/broadcast/broadcast_notify）+ src/main.py（@app.websocket /ws/room/{chain_id} JWT query param 鉴权 + subscribed 确认 + stroke 推送校验当前节点责任人 + 广播）+ src/api/routes/nodes.py（submit 路由层触发 notify 广播：completed→chain_done，否则→node_submitted+your_turn）+ frontend/services/ws.ts（补 token query param 从 useAuthStore 取 token）+ frontend/pages/ChainHallPage.tsx（删 MOCK_STROKES+定时器，接入真实 WS stroke+notify，onMessage 处理 stroke 追加笔迹+notify 刷新 detail+message 提示）+ frontend/pages/RelayPage.tsx（建立 WS 连接 + draw 时节流推送 stroke 200ms + 收 your_turn notify）+ tests/test_t019_ws.py（10 测试）
- **关键设计：Notify 路由层触发（service 不感知 WS）**：submit 路由调完 service.submit_node 成功后，据返回值 chain_status/next_seq 触发 ws_manager.broadcast_notify。service 层只依赖 repository（分层约束），路由层编排广播。ws_manager 全局单例，路由层+WS 端点共享同一连接池
- **关键设计：WS 鉴权 query param token**：浏览器 WebSocket 不能设自定义 Authorization header（get_current_user 的 HTTPBearer 不适用）。WS 端点用 ?token=JWT + decode_token 复用（src.core.security）。无效/缺失 → accept + send error「未认证」+ close(4401)。前端 ws.ts 从 useAuthStore 取 token 拼 URL
- **关键设计：stroke 推送校验当前节点责任人**：WS 端点收到 stroke 时，用独立 async_session_maker() session 查 chain+current_node，校验 node.author_id==user_id（当前责任人才能推笔迹）。非责任人推送被忽略。独立 session 因 WS 循环不能持有请求级 Depends session
- **关键设计：围观范围 JWT 认证即可**：任何有效 JWT 用户可订阅围观（符合公开广场语义），不强制校验链成员。stroke 推送才校验责任人
- **关键设计：WS 路由注册 @app.websocket**：main.py 已有 app=server.app（pycore APIServer 暴露标准 FastAPI 实例），直接 @app.websocket 注册（FastAPI 原生，pycore 无 WS 工具）。与 app.mount StaticFiles 同区
- **关键设计：前端 stroke 推送节流**：P05 draw 时调 flushStroke，200ms 间隔节流推送（避免高频 flooding WS）。推送 currentStroke points（pressure 0.5）+ color+size+node_id
- **修复：测试 DB 持久化用户名冲突**：初版测试用 TestClient HTTP 注册拿 token，但运行时 SQLite 文件库数据持久化，重跑用户名冲突 400。改用 create_access_token(uuid4(),'wstester') 直接生成 token（WS 端点 decode_token 只验签不查 DB，不需注册）
- **修复：同步 WS 测试阻塞问题**：初版用 TestClient 同步 WS 测广播+非责任人推送，receive_json 会阻塞死等。改为：鉴权/订阅/断开用 TestClient 同步 WS，广播逻辑用 ConnectionManager 单元测试（MagicMock(spec=WebSocket)），分离关注点
- **修复：mypy unused-ignore**：MagicMock 是 Any 子类型，set[WebSocket].add(MagicMock) 不报 arg-type，type: ignore 多余。删掉所有 # type: ignore[arg-type]
- **验证**：ruff ✅ / mypy ✅（43 source files）/ pytest ✅（62 passed，T-019 10 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅ / **真实联调 ✅**（后端 8099 直连 WS 8 项验证全过：注册建链→WS subscribed→无token error→stroke 广播围观者收到→submit→notify node_submitted+your_turn）/ DB 持久化 ✅
- **结果**：PASS（10 单元测试 + 8 项真实联调全过），报告 .sdd/test-reports/test-T-019.md
- **状态**：T-019 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（A 作画 B 围观笔迹 + A 提交 B 收通知 + 无 token 拒绝）

## 2026-08-20 T-020 作品详情功能闭环

- **Developer**：Orchestrator 直接实现
- **产出**：src/models/work.py（WorkAuthorResponse/WorkListItemResponse/WorkNodeResponse/WorkDetailResponse/WorkListResponse Pydantic 响应模型）+ src/repositories/work.py（WorkRepository：list_completed_chains 分页+排序 most_liked 用 Vote 子查询/get_chain/get_creator/get_nodes status=submitted 按 seq/get_node_authors 批量/count_members/count_likes Vote 表/get_thumb_url 首个 draw 节点 content_url）+ src/services/work.py（WorkService：list_works 遍历 completed 链查 member_count/like_count/thumb_url + get_work_detail 链+creator+已提交节点+批量 author LookupError→404）+ src/api/routes/works.py（GET /api/works 分页+排序 + GET /api/works/{id} 详情，游客可访问无 get_current_user，404 返回契约格式）+ src/main.py（include_router works_router）+ frontend/pages/PlazaPage.tsx（WorkThumb 用 thumb_url 显示真实图片，无则 fallback 首字占位）+ frontend/pages/WorkDetailPage.tsx（ChainNodeCard image 节点用 content_url 显示真实画作，无则 fallback 占位）+ frontend/pages/PlazaPage.css（.thumb-img 样式）+ frontend/pages/WorkDetailPage.css（.node-img 样式）+ tests/test_t020_works.py（10 测试）
- **关键设计：游客可访问（无 JWT 鉴权）**：作品广场+详情是公开只读功能，GET /api/works 和 GET /api/works/{id} 不加 get_current_user 依赖。任何访客可浏览已完成作品（符合公开广场语义）。测试 test_list_works_guest_accessible + test_get_work_detail_guest_accessible 验证无 token 仍 200
- **关键设计：只展示 completed 链**：只有 status=completed 的链才作为作品展示。未完成链不出现在广场列表，查详情也返回 404。list_completed_chains 查询过滤 status=completed，get_work_detail 校验 chain.status != completed → LookupError
- **关键设计：thumb_url 取首个 draw 节点 content_url**：广场卡片缩略图取链中第一个 draw 节点（seq 最小）的 content_url。get_thumb_url 查 Node.type=draw + content_url IS NOT NULL 按 seq 升序取首条。无则返回空字符串（前端 fallback 首字占位）
- **关键设计：like_count 查 Vote 表（T-021 前返回 0）**：like_count 查 Vote 表 count，当前无 Vote 记录返回 0。count_likes 用 select(func.count()).select_from(Vote)
- **关键设计：AI 补位节点 author_id=None**：模型设计 AI 补位节点 author_id=None（无真实用户）。get_work_detail 构建节点时 author_id 为空则 nickname fallback 到 node.author_label（AI 补位时存"AI"）。get_node_authors 批量查 User，author_map 不含 None key 自然 fallback
- **关键设计：most_liked 排序用 Vote 子查询**：list_completed_chains 的 most_liked 排序用 Vote 子查询统计每链点赞数，outerjoin + coalesce 降序。latest（默认）按 created_at 降序。不支持的 sort 降级为 latest
- **修复：AI 节点测试 author_id 未置 None**：初版 test_get_work_detail_ai_node_tag 把 seq=2 is_ai=True 但 author_id 仍是 creator.id，service 查到 creator 故 nickname=小G（非 AI）。改为 author_id=None（AI 补位节点无真实作者），nickname fallback 到 author_label=AI。符合模型设计（AI 补位 author_id 可空）
- **修复：ruff create_access_token 未使用**：作品接口游客可访问，测试无需 JWT，import create_access_token 未用。删掉，只留 hash_password
- **验证**：ruff ✅ / mypy ✅（38 source files）/ pytest ✅（72 passed，T-020 10 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅ / **真实联调 ✅**（后端 8099 直连 3 项验证全过：GET /api/works 200 返回 completed 链列表含 thumb_url/member_count/like_count → GET /api/works/chain-0001 200 返回 6 节点全链 draw/describe 交替含 author/content_url/content_text/is_ai → GET /api/works/nonexistent 404 作品不存在）
- **结果**：PASS（10 单元测试 + 3 项真实联调全过），报告 .sdd/test-reports/test-T-020.md
- **状态**：T-020 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（广场看真实作品卡片 + 详情看全链真实图片 + 不存在提示）

## 2026-08-20 T-021 投票功能闭环

- **Developer**：Orchestrator 直接实现（EnterPlanMode 方案批准后实施）
- **产出**：src/models/vote.py（VoteItemRequest/VoteRequest/VoteCountItem/VoteResultItem/VoteResultResponse/VoteResultDetailResponse，target_author 复用 WorkAuthorResponse）+ src/repositories/vote.py（VoteRepository：create_votes 批量插入 IntegrityError→ValueError 已投过/has_voted/count_by_chain 按 dimension+target_node_id 分组统计/get_node/get_nodes_by_ids/get_node_authors）+ src/services/vote.py（VoteService：submit_votes 链存在+成员+完成+三维度齐全+target 属于链+未投过 + get_result 分组统计+批量查 target_author author_id 空时 fallback author_label）+ src/api/routes/votes.py（POST /api/chains/{id}/votes + GET /api/chains/{id}/votes/result，需登录鉴权，LookupError→404/PermissionError→403/ValueError→400）+ src/main.py（include_router votes_router）+ frontend/pages/ReplayPage.tsx（ReplayNodeItem image 用 content_url 显示真实画作，无则 fallback 占位）+ frontend/pages/ReplayPage.css（.replay-node-img 样式）+ tests/test_t021_votes.py（10 测试）
- **关键设计：403 统一语义不区分原因**：链未完成/非成员/已投过 → 都返回 403「链未完成或无权投票」。契约只定义这一个 403 message，不区分原因，避免泄露投票状态（不告诉非成员"链已完成但你不该投"，只说"无权"）。PermissionError 在 service 层统一抛此 message
- **关键设计：唯一约束=每人每维度一票**：Vote 表 uq_vote_chain_user_dim(chain_id,user_id,dimension) 唯一约束。create_votes 批量插入时该用户该维度已投过 → IntegrityError → rollback → raise ValueError。service 层先用 has_voted 预检（任一维度投过→403），IntegrityError 是兜底（并发场景）
- **关键设计：三维度齐全校验**：submit_votes 校验 set(dimension)=={most_drift,best_draw,best_describe}，缺维度或重复维度 → 400「必须为三个维度各投一票」。DIMENSIONS 常量定义三维度集合
- **关键设计：target_node 属于链校验**：每个 vote 的 target_node_id 逐个查 get_node，校验 node.chain_id==chain.id 且 node.status==submitted。不属于链或未提交 → 400「投票目标节点不属于该链」
- **关键设计：get_result 的 target_author fallback**：count_by_chain 返回 [{dimension,target_node_id,vote_count}] 无 author。get_result 批量查 Node 取 author_id+author_label，再批量查 User。author_id 为空（AI 补位节点）时 nickname fallback 到 node.author_label（与 T-020 作品详情一致）
- **关键设计：路由前缀共享 /api/chains**：votes.py 用 prefix=/api/chains，与 chains.py 共享前缀。FastAPI 允许多 router 共享前缀（按 tags 区分），路径不重叠：chains.py 有 //{room_code}/{id}/join/{id}/detail，votes.py 有 /{id}/votes//{id}/votes/result
- **验证**：ruff ✅ / mypy ✅（42 source files）/ pytest ✅（82 passed，T-021 10 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅ / **真实联调 ✅**（后端 8099 直连 12 项验证全过：注册A→建链→接力4节点completed→作品详情4节点→投票三维度200→结果200含target_author→重复403→非成员403→无token401）
- **结果**：PASS（10 单元测试 + 12 项真实联调全过），报告 .sdd/test-reports/test-T-021.md
- **状态**：T-021 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（回放完成后三维度投票 + 提交看结果 + 未完成/非成员提示）

## 2026-08-20 T-022 通知功能闭环

- **Developer**：Orchestrator 直接实现（EnterPlanMode 方案批准后实施）
- **产出**：src/models/notification.py（NotificationItemResponse/NotificationListResponse/NotificationReadRequest/NotificationReadResponse）+ src/repositories/notification.py（NotificationRepository：create 单条/create_many 批量/list_by_user 分页+unread_only+倒序 返回 list+total/mark_read 批量 UPDATE 防越权 WHERE user_id 过滤）+ src/services/notification.py（NotificationService：list_notifications→{items,total,page,page_size} + mark_read→{read_count}）+ src/api/routes/notifications.py（GET /api/notifications page/page_size/unread_only Query + POST /api/notifications/read，需登录鉴权）+ src/main.py（include_router notifications_router）+ src/api/routes/nodes.py（submit 路由层加 DB 通知生成：chain_done 给所有成员 if completed / your_turn 给下一位 + node_submitted 给所有成员 if not completed）+ src/services/node.py（submit_node 返回值补 next_author_id，函数内已按轮转 idx=next_seq%member_count 计算）+ tests/test_t022_notifications.py（10 测试）
- **关键设计：通知生成放路由层不放 service**：通知生成需 chain 成员列表+下一位责任人，与 T-019 WS notify 同位置同语义。放路由层（nodes.py submit），service 层（NodeService）不感知通知模块，保持分层约束。路由层用 ChainRepository.get_members 查成员 + NotificationRepository 写通知
- **关键设计：DB 通知持久化 + WS 实时推送双轨**：WS notify（T-019）在线即时推送（不保证送达，离线丢）；DB 通知（T-022）持久化到 Notification 表（离线用户登录 GET /api/notifications 可见）。两者同位置同语义，互不替代
- **关键设计：mark_read 防越权**：UPDATE Notification SET read=True WHERE id IN (...) AND user_id==current_user.id AND read.is_(False)。WHERE 带 user_id 过滤，用户无法标记他人通知（传入他人 id rowcount=0）。test_mark_read_only_own 验证
- **关键设计：get_db 自动 commit**：src/db/session.py get_db 在 yield 后 await session.commit()（成功提交/异常 rollback）。路由层通知生成只需 add/flush，不需显式 commit，与 NodeService 内部只 flush 不 commit 一致
- **修复：测试轮转稳定性 joined_at 显式设值**：测试环境同事务快速执行，ChainMember server_default=func.now() 时间戳可能相同，导致 members.sort(joined_at) 排序不稳定，轮转 idx 取错人 → next_author_id 错位（test_t017 同款问题）。解法：extra_members 显式设 joined_at=now+(i+1)秒，保证创建者在前、后续成员按加入顺序在后
- **修复：test_mark_read_success client 已关闭**：resp2（第二次 GET）在 async with AsyncClient 块外，块退出 client 关闭后 resp2 用它报 RuntimeError。移入块内（post 后、退出前）
- **验证**：ruff ✅ / mypy ✅（46 source files）/ pytest ✅（92 passed，T-022 10 测试全过无回归）/ **真实联调 ✅**（后端 8099 直连 13 项验证全过：注册2用户→建链→member2加入→creator提交seq0→member2收your_turn+node_submitted/creator收node_submitted→标记已读read_count=1→unread_only剩1→member2提交seq1→creator提交seq2→member2提交seq3链completed→member2收6条含chain_done/creator收5条含chain_done）
- **结果**：PASS（10 单元测试 + 13 项真实联调全过），报告 .sdd/test-reports/test-T-022.md
- **状态**：T-022 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（顶部铃铛看真实通知列表 + 标记已读 + 接力提交后看到 your_turn/node_submitted/chain_done）

## 2026-08-20 T-023 个人资料/我的作品功能闭环

- **Developer**：Orchestrator 直接实现（EnterPlanMode 方案批准后实施）
- **产出**：src/models/user.py（扩展：UserProfileResponse/MyWorkItemResponse/MyWorkListResponse）+ src/repositories/user.py（扩展：count_participated ChainMember 计数/count_created Chain.creator_id 计数/list_my_works creator OR member distinct 去重 分页+倒序）+ src/services/user.py（扩展：get_profile user+统计/list_my_works chains+role 判定+thumb_url 查询，构造函数注入 WorkRepository）+ src/api/routes/users.py（新建：GET /api/users/me + GET /api/users/me/works，需登录鉴权，LookupError→404）+ src/main.py（include_router users_router）+ frontend/pages/ProfilePage.tsx（清理 Mock 注释 + MyWorkCard thumb 用真实 thumb_url 有图显图无图 fallback 首字，与 PlazaPage WorkThumb 一致）+ tests/test_t023_users.py（11 测试）
- **关键设计：list_my_works 范围含 in_progress**：广场 GET /api/works 只查 completed；个人主页 GET /api/users/me/works 查用户参与/创建的所有链（含 in_progress+completed）。前端 MyWorkCard 有"进行中"label，期望显示用户参与的所有链。list_my_works 不加 status 过滤
- **关键设计：role 判定**：chain.creator_id==user_id → creator，否则 participant（成员非创建者）。创建者既是 creator 又是 member，role 标 creator（优先）
- **关键设计：OR + distinct 去重**：用户参与（ChainMember.user_id==）OR 创建（Chain.creator_id==）可能重叠（创建者也是成员）。select(Chain).where(creator_id==user_id | id.in_(member_chain_ids)).distinct() 去重，避免创建者链出现两次
- **关键设计：thumb_url 复用 WorkRepository.get_thumb_url**：thumb_url 取链第一个 draw 节点 content_url（与广场一致）。list_my_works 逐个 chain 调 work_repo.get_thumb_url（N+1，链数有限可接受）。UserService 注入 WorkRepository（参照 VoteService 多 repo 注入）
- **关键设计：datetime→str 用 isoformat**：ORM created_at 是 datetime，Pydantic 模型声明 str。service 层构造 dict 时手动 .isoformat() 转 str（与 T-020 WorkService 一致），不靠 Pydantic 自动转换
- **关键设计：UserService work_repo 可选**：__init__(repo, work_repo=None)。auth 路由 register/login 只需 user_repo（传1参数）；users 路由 get_me/get_my_works 传2参数。work_repo 可选保持 auth 路由兼容
- **修复：select(Chain.distinct()) 写法错误**：初版用 select(Chain.distinct())，mypy 报 "type[Chain] has no attribute distinct"（distinct 不是类方法）。改为 select(Chain).where(...).distinct()（Query.distinct() 方法）
- **修复：created_at datetime 未转 str**：初版 service 直接传 ORM datetime 对象，Pydantic model_validate 报 ValidationError（string_type）。改为 .isoformat() if created_at else ""
- **验证**：ruff ✅ / mypy ✅（47 source files）/ pytest ✅（103 passed，T-023 11 测试全过无回归）/ 前端 type-check ✅ / lint ✅ / build ✅ / **真实联调 ✅**（后端 8099 直连 11 项验证全过：注册userA→新用户统计0→建链+提交draw→统计2/2→作品2条role=creator含thumb_url→注册userB→userB统计0/作品空防越权→无token401×2）
- **结果**：PASS（11 单元测试 + 11 项真实联调全过），报告 .sdd/test-reports/test-T-023.md
- **状态**：T-023 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（个人主页看真实资料+统计 + 我的作品卡片含真实缩略图+角色+状态）

## 2026-08-20 T-024 AI 补位定时任务功能闭环

- **Developer**：Orchestrator 直接实现（EnterPlanMode 方案批准后实施）
- **产出**：src/services/ai.py（扩展：generate_image Qwen-Image 文生图返回 MaaS URL + describe_image Qwen3.6 VLM 看图本地 base64 优先/远程 URL 降级纯文本 + _fetch_image_base64 + _call_vlm）+ src/services/ai_fill.py（新建：AiFillService scan_and_fill 扫描 in_progress 链 24h 超时 pending 节点补位 + 7 天过期 / _fill_node 生成内容→update_node_ai_fill→advance_chain→create_next_node→notify / _notify_chain_event / _expire_chain）+ src/repositories/node.py（扩展：update_node_ai_fill content+is_ai=True+status=ai_filled+submitted_at=now）+ src/repositories/chain.py（扩展：list_in_progress 查 in_progress 链 / mark_expired 标记 expired）+ src/scheduler.py（新建：APScheduler AsyncIOScheduler 每小时 _ai_fill_job 独立 session / init_scheduler / shutdown_scheduler）+ src/services/chain.py（修改：get_chain_detail 填充 ai_countdown_at = pending 节点 created_at + 24h / _get_ai_countdown_at helper）+ src/main.py（修改：on_startup init_scheduler + on_shutdown shutdown_scheduler）+ tests/test_t024_ai_fill.py（10 测试）+ tests/test_t016_chain_query.py（修复 ai_countdown_at 断言 is not None 回归）
- **关键设计：MaaS 返回格式探测**：实现前先探测海康 MaaS API 格式。Qwen-Image POST /images/generations → 200 + data[0].url（MaaS 存储 URL，浏览器可直接访问）；Qwen3.6 VLM POST /chat/completions 多模态 content → 200 + choices[0].message.content。按实际格式解析，不猜
- **关键设计：describe 节点看图降级策略**：VLM 看图需可访问图片。draw 节点生成的 MaaS URL 下载受限（返回 36 bytes 错误页，VLM 无法访问远程 URL）。解法：_fetch_image_base64 本地 /uploads/ 文件直接读 base64 传 VLM（真实看图），远程 URL 尝试下载（>1000 bytes 才用），下载失败降级纯文本续写（VLM 生成描述性文字兜底，保证补位闭环不中断）
- **关键设计：补位通知复用 T-022 逻辑**：AI 补位后通知与人工 submit 同语义——链完成→成员 chain_done；否则→下一位 your_turn + 成员 node_submitted。抽到 AiFillService._notify_chain_event（service 层直接用 NotificationRepository，不调 nodes.py 路由，保持 service 层自洽）
- **关键设计：scheduler 独立 session**：定时任务不持有请求级 session，用 async_session_maker() 独立 session（与 T-019 WS stroke 校验同模式）。_ai_fill_job 内 try/commit/rollback，异常不中断 scheduler（记日志下次扫描重试）
- **关键设计：补位失败不中断**：单个节点补位失败（MaaS 调用失败抛 RuntimeError）记日志跳过，下次扫描重试，不中断整个扫描。scan_and_fill 返回 {filled, expired, errors} 统计
- **关键设计：ai_countdown_at = pending 节点 created_at + 24h**：当前 pending 节点创建时间 + ai_fill_timeout_hours(24h)。链 in_progress + 当前节点 pending 时返回真实值，其他返回 None（不显示）。前端 ChainHallPage formatCountdown 算与 now 的差显示倒计时
- **修复：T-016 回归 ai_countdown_at 断言**：T-024 填充真实 ai_countdown_at 后，test_t016_chain_query test_get_chain_detail_success 原断言 is None 失败（in_progress + pending 节点现在返回真实值）。改为 is not None
- **验证**：ruff ✅ / mypy ✅（49 source files）/ pytest ✅（T-024 10 测试全过 + 全量 113 passed 无回归）/ 前端 type-check ✅ / lint ✅ / **真实联调 ✅**（后端启动 scheduler 日志 "AI fill scheduler started (every 1 hour)" → 建链+25h 前 pending draw 节点 → 手动触发 scan_and_fill 调真实 MaaS Qwen-Image → filled=1, is_ai=true, status=ai_filled, content_url=MaaS 真实图片 URL → 链推进 0→1 → seq=1 describe 节点创建 → member2 收 your_turn+node_submitted → describe 节点 25h 前触发 scan 调真实 Qwen3.6 VLM → filled=1, is_ai=true, content_text=VLM 生成描述 → 联调数据清理）
- **结果**：PASS（10 单元测试 + 真实联调 draw/describe 双节点 AI 补位全过），报告 .sdd/test-reports/test-T-024.md
- **状态**：T-024 passed（自动验证全过），user_gate=true，待用户门禁验收浏览器 UI（链大厅页看 AI 补位倒计时 + AI 补位后节点带 is_ai 标记）

## 2026-08-20 T-025 E2E 回归验证 + 启动文档

- **Developer**：Orchestrator 直接执行（最终回归任务，无新功能开发）
- **产出**：docs/startup.md（新建，11 节：环境要求/默认配置/端口说明/启动命令/质量门禁/E2E流程/项目结构/分层架构/AI补位/测试覆盖/FAQ）+ .sdd/test-reports/test-T-025.md（E2E 报告）
- **E2E 全流程真实联调（33 步）**：注册 e2e_alice/e2e_bob → A 建链(room_code=F7PCQ6, 链长4, 邀请制, 手动题"戴帽子的猫") → B 房间码查询+加入 → 链大厅详情(2成员/4节点/ai_countdown_at真实值) → A 看上一节点(起手题虚拟节点) → 上传PNG → 提交seq=0 draw → 链推进seq=1 describe 责任人轮转B → B收your_turn+node_submitted → B看上一节点(防剧透只看seq=0画作) → 提交seq=1 describe → seq=2 draw 责任人回A → A上传+提交seq=2 draw → B提交seq=3 describe → 链completed → A收5通知(chain_done×1+node_submitted×3+your_turn×1) → 作品详情(4节点全链署名is_ai全false) → 广场(4作品E2E链在列thumb正确) → A/B各投三维度票 → 投票结果(most_drift N2得2票/best_draw N0N2各1票/best_describe N1N3各1票含author) → 个人主页(昵称/参与1链/创建1链) → 我的作品(1条role=creator status=completed thumb正确) → 游客无token访问作品详情200(分享链接场景) → AI补位复验(建链2+25h前节点+触发scan→真实MaaS Qwen-Image生成真实图片URL→is_ai=True status=ai_filled链推进) → 清理联调数据
- **关键发现：nodes 路由路径参数是 chain_id 不是 node_id**：GET /api/nodes/{id}/previous 和 POST /api/nodes/{id}/submit 的 {id} 实际是 chain_id（路由内调 service.get_previous(chain_id, user)）。前端 RelayPage 从 URL /chain/:id/relay 取 chain_id 传给 nodes API。E2E 初次用 node_id 调用 404，改用 chain_id 通过。设计决策（接力页上下文是链），非 Bug
- **关键发现：detail vs works 节点结构差异**：GET /api/chains/{id}/detail（链大厅）进度节点链无 content（防剧透+进度展示）；GET /api/works/{id}（作品详情）完整内容链含 content。验证 AI 补位节点内容用 works API；chain2 未完成时 works 返回 None（广场只 completed），改用 DB 直查确认
- **关键发现：Windows curl 单引号 JSON 转义**：Windows Git Bash 下 curl -d '{"k":"v"}' 单引号内中文转义致 "error parsing body"。解法：JSON body 写文件 curl -d @file.json。非代码 Bug，联调脚本注意事项
- **验证**：ruff ✅ / mypy ✅（49 source files）/ pytest ✅（113 passed 无回归）/ 前端 type-check ✅ / lint ✅ / **E2E 真实联调 ✅**（33 步全过，跨7模块 auth/chains/nodes/works/votes/notifications/users + scheduler，AI 补位真实 MaaS Qwen-Image 复验）
- **结果**：PASS（113 单元测试 + 33 步 E2E 真实联调全过），报告 .sdd/test-reports/test-T-025.md，docs/startup.md 已输出
- **状态**：T-025 passed（自动验证 + E2E 全过），user_gate=true，待用户最终验收。全部 25 个任务（T-001~T-025）开发完成
