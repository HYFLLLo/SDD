# 测试报告：T-001 前端工程初始化 + 全局布局 + Mock 基建

**测试时间**：2026-08-19
**Tester**：Orchestrator 降级执行（Tester 子智能体两次启动后无输出，按 codex-subagents.md 降级语义由主会话执行验证）

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户打开前端开发服务器，看到全局顶部导航栏（Logo「画意接龙」+ 广场/我的导航 + 通知铃铛 + 头像占位），配色为米白纸底 + 陶土橙点缀 | PASS | `src/components/AppHeader.tsx` 含 Logo「画意接龙」(L15)、广场/我的 NavLink (L19-24)、🔔 通知铃铛 (L28-31)、头像占位 (L32-34)；`AppHeader.css` 使用 `var(--bg)` 米白底 + `var(--accent)` 陶土橙点缀，与原型 `01-plaza.html .topbar` 结构对齐 |
| 2 | 用户访问根路径，页面能正常渲染不报错，路由骨架可跳转占位页 | PASS | `src/router/index.tsx` 覆盖 9 个路由（Plaza/Login/CreateChain/JoinChain/ChainHall/Relay/WorkDetail/Replay/Profile），ProtectedRoute 保护需登录路由；build 通过（117 modules），dev server :5199 HTTP 200 |
| 3 | 页面整体视觉风格与原型 draw-telephone.pen 的手账涂鸦本方向一致（米白底、陶土橙 accent、冷灰蓝 AI 区隔） | PASS | `src/styles/tokens.css` 定义 `--bg:#FAF6EF`(米白纸底)、`--accent:#C8643C`(陶土橙)、`--ai:#6B7A8F`(冷灰蓝 AI 区隔)，与原型 assets/style.css 配色一致 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | npm run type-check 通过 | PASS | 独立重跑 `tsc -b --noEmit`，0 错误（Orchestrator 已修复 4 处初版 TS 错误：chains.ts/votes.ts 缺 WorkAuthor import、handler.ts 未用导入） |
| 2 | npm run lint 通过 | PASS | 独立重跑 `oxlint`，0 error 0 warning |
| 3 | npm run build 通过 | PASS | 独立重跑 `tsc -b && vite build`，117 modules transformed，1.89s，dist 产物正常 |
| 4 | vite.config.ts 配置 server.proxy['/api'] 指向 8099 且支持 VITE_BACKEND_PROXY_TARGET 切 8003 | PASS | `vite.config.ts:7` `backendTarget = env.VITE_BACKEND_PROXY_TARGET \|\| 'http://localhost:8099'`，L15 `/api` 代理使用 backendTarget |
| 5 | vite.config.ts 配置 /ws 的 ws:true 代理 | PASS | `vite.config.ts:8` wsTarget = backendTarget.replace(/^http/,'ws')，L16 `/ws` 代理 `ws: true` |
| 6 | frontend/.env 的 VITE_API_BASE_URL 使用相对路径 /api，未硬编码完整 URL | PASS | `.env:1` `VITE_API_BASE_URL=/api`（相对路径） |
| 7 | Mock 数据格式与 api-contracts.md 一致 | PASS | 逐字段对比：works.ts (WorkListItem/WorkDetail/WorkNode)、chains.ts (Chain/ChainLookup/ChainJoinResponse/ChainDetail) 均为 api-contracts.md 已定义字段的子集，响应包装 `{code,message,data}` 与分页 `{items,total,page,page_size}` 格式一致 |
| 8 | 固定高度容器在浏览器中验证文字完整显示，容器高度 ≥ 内容理论高度 × 1.2 | PASS（静态） | Mock 阶段禁止浏览器自动化；静态检查 AppHeader.css topbar height:56px、tokens.css 预留 --r-card:12px 圆角与 --shadow 缓冲，无固定高度溢出风险。此条为系统级经验约束，实际容器溢出在后续真实联调阶段复验 |

## 代码质量检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 文件是否真的被创建 | PASS | src/ 下 62 个文件（types 12 + mocks 11 + services 11 + stores 1 + router 2 + components 2 + pages 10 + styles 2 + main.tsx + App.tsx） |
| 语法错误 | PASS | type-check/build 通过 |
| 硬编码密钥/密码 | PASS | grep 无 sk-/api_key/bearer/password 硬编码 |
| TODO/FIXME/HACK 标记 | PASS | grep 无任何标记 |
| 导入路径正确 | PASS | type-check 通过，无未解析导入 |
| 硬编码 ws://localhost | PASS | ws.ts 使用 `window.location.host` + 相对 /ws 路径，注释明确禁止硬编码 |

## 超出范围发现（不影响当前任务判定）

无。所有检查项均在 acceptanceCriteria 范围内通过。

## Mock 阶段测试边界遵守说明

本任务为 `type=frontend` 且 `frontendIntegration.required=false`，验证全程遵守 Mock 阶段边界：
- 未使用 Playwright/Puppeteer/Cypress 等 E2E 工具
- 未开启多标签页测试
- 未验证真实后端连通性（Mock 阶段不启动后端）
- 未验证真实 WebSocket 握手
- 仅使用静态代码分析 + 构建验证 + 单页面 UI 静态检查

**验证已完成，等待 Orchestrator 向用户报告并获取门禁确认。**
