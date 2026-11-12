# 测试报告：T-002 P09 登录/注册页 Mock

**测试时间**：2026-08-19
**Tester**：Orchestrator 降级执行（Tester 子智能体反复无输出，按 codex-subagents.md 降级语义由主会话验证）

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在登录/注册页切换 Tab，看到登录和注册两个表单 | PASS | `LoginPage.tsx` 使用 Ant Design `Tabs` 组件，activeKey=tab（'login'/'register'），登录表单含用户名+密码，注册表单含用户名+昵称+密码（L60-118） |
| 2 | 用户填写用户名密码点击登录，页面显示登录成功（Mock Token 存 localStorage），跳转广场页 | PASS | `handleLogin` 调用 `useAuthStore.login()`，store 将 `access_token` 存入 `localStorage`（useAuthStore.ts:35），成功后 `message.success('登录成功')` + `navigate(from ?? '/')` 跳转广场页 |
| 3 | 用户点击「先逛逛」，跳转广场页（游客态） | PASS | `handleGuest` 调用 `navigate('/', {replace:true})` 跳转广场页，不写 token 保持游客态 |
| 4 | 表单圆角输入框和陶土橙主按钮样式与原型一致 | PASS | `LoginPage.css` 输入框 `border-radius: var(--r-btn)` + `background: var(--canvas)`，主按钮 `background: var(--accent)` 陶土橙 + `border-radius: var(--r-btn)`，与原型手账涂鸦本方向一致 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | npm run type-check 通过 | PASS | 独立重跑 `tsc -b --noEmit`，0 错误 |
| 2 | npm run lint 通过 | PASS | 独立重跑 `oxlint`，0 error 0 warning |
| 3 | npm run build 通过 | PASS | 独立重跑 `tsc -b && vite build`，1579 modules transformed，423ms（chunk size 警告非阻塞，antd 体积所致） |
| 4 | Mock 数据格式与 api-contracts.md 的 POST /api/auth/register、POST /api/auth/login 响应一致 | PASS | mock auth.ts 返回 `{code:200, message:'success', data:{access_token, user:{id,username,nickname,avatar_url}}}`，与 api-contracts.md L41/L61 完全一致；handler.ts 拦截 `/auth/login`（mockuser/mockpass→200，否则→401）和 `/auth/register`（mockuser→400 已存在，否则→200） |
| 5 | Mock Token 存储在 localStorage，刷新后可读取 | PASS | useAuthStore 初始化时 `token: localStorage.getItem('token')`、`user: readStoredUser()` 从 localStorage 读取，刷新后状态保持 |

## 代码质量检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 文件是否真的被创建 | PASS | LoginPage.tsx（重写占位为完整实现）+ LoginPage.css（新建） |
| 硬编码密钥/密码 | PASS | Mock 账号 mockuser/mockpass 仅作为 placeholder 文案显示在输入框，非真实凭证 |
| TODO/FIXME/HACK 标记 | PASS | 无 |
| 导入路径正确 | PASS | type-check 通过 |
| Mock 阶段边界 | PASS | 未用 Playwright，未验真实 JWT 签发，未验服务端持久化，仅单页面 UI/状态/Mock 数据格式 |

## 超出范围发现（不影响当前任务判定）

无。

**验证已完成，等待 Orchestrator 向用户报告并获取门禁确认。**
