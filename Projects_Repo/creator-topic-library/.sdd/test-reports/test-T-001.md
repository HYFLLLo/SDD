# 测试报告：T-001 前端工程脚手架

- 项目：creator-topic-library（创作者选题灵感库）
- 任务：T-001 前端工程脚手架（Vite + React + TS + AntD + Zustand + 路由 + 持久化适配层 + 演示数据）
- 结论：**PASS**
- 验证方式：独立运行命令 + 无头浏览器（系统 Chrome via playwright-core）运行时验证；不采信 Developer 声明
- 环境：Node v24.14.0 / npm 11.9.0；dev server 端口 5199（strictPort）

## 验收标准逐条结果

| 标准 | 结果 | 证据 |
| --- | --- | --- |
| AC1 前端工程可启动，5199 端口正常打开，严格端口模式，占用时报错而非换端口 | PASS | `npm run dev` 启动输出 `http://localhost:5199/`，`netstat` 显示 127.0.0.1:5199 LISTENING；`GET /` 返回 200。占用 5199 再启动第二实例：`Error: Port 5199 is already in use`，进程退出码 1，未静默换端口 |
| AC2 package.json 提供 lint / type-check / build 三脚本且全部通过 | PASS | `npm run type-check` 退出 0；`npm run lint` 退出 0；`npm run build` 退出 0（1510 modules transformed，产物写入 dist/） |
| AC3 应用外壳：顶部栏含应用名称占位 + 主体区域 + 路由骨架（主页、标签管理两条路由） | PASS | 运行时顶部栏渲染应用名“创作者选题灵感库”，菜单“选题库 / 标签管理”；`/` 渲染 HomePage（h2 选题库主页），`/tags` 渲染 TagManagementPage（h2 标签管理，path=/tags）；`src/router/index.tsx` 定义 index 与 `tags` 两条路由 |
| AC4 首次打开可见演示数据：≥6 选题、4 标签，刷新后仍在 | PASS | 首屏 DOM 6 条选题、4 个标签；localStorage 键 `creator-topic-library.topics.v1`（6 条）、`.tags.v1`（4 条）；`page.reload()` 后 DOM 仍为 6 条 / 4 个，localStorage 计数不变 |
| AC5 界面暖纸色调，AntD 主题 token 已定制，非默认蓝 | PASS | `styles/theme.ts` colorPrimary/colorInfo = `#B85C38`，colorBgBase `#FBF4E8`；运行时 body background = `rgb(246, 236, 220)`，选中菜单项颜色 = `rgb(184, 92, 56)`；截图为暖纸色，非 AntD 默认蓝 |

## technicalChecks 逐条结果

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| npm run type-check 通过 | PASS | `tsc --noEmit` 退出码 0 |
| npm run lint 通过 | PASS | `eslint .` 退出码 0，无告警 |
| npm run build 通过 | PASS | `tsc --noEmit && vite build` 退出码 0 |
| frontend/.env 配置 VITE_API_BASE_URL=/api，服务层无写死完整 URL | PASS | `.env` 内容 `VITE_API_BASE_URL=/api`；`services/httpClient.ts` 使用 `import.meta.env.VITE_API_BASE_URL`；服务层无 http(s) 写死 URL。全库唯一完整 URL 为 `vite.config.ts` 的代理默认目标 `http://localhost:8099`（构建配置，非服务层，且经 `VITE_BACKEND_PROXY_TARGET` 可覆写） |
| dev server 使用 --strictPort，端口被占不静默换端口 | PASS | `package.json` dev = `vite --strictPort --port 5199`，`vite.config.ts` server.strictPort = true；端口占用时直接报错退出（见 AC1） |
| 服务层响应结构 {code, message, data}，演示数据字段与 Topic/Tag 契约一致 | PASS | `topicService.listTopics` 返回 `{code:200, message:'success', data:{items,total,page,page_size}}`；`tagService.listTags` 返回 `{code:200, message:'success', data:{items}}`。演示选题字段 = id,title,content,notes,source,tag_ids,status,priority,created_at,updated_at；标签字段 = id,name,color,created_at,usage_count；status/priority 枚举与契约一致 |
| 持久化适配层独立：store 经 service 读写，组件不直接调用 localStorage | PASS | 全库 localStorage 调用仅出现在 `src/adapters/persistence/localStorageAdapter.ts`；`services/*` 调用 adapter；`stores/useTopicLibraryStore.ts` 调用 services；`pages/*`、`components/*` 仅使用 store，无 localStorage 直接调用 |

## 范围外附加说明（不影响本任务判定）

- 浏览器控制台存在 1 条 404（`/favicon.ico`）：项目未在 `index.html` 声明 favicon，属浏览器默认请求；T-001 验收标准未要求 favicon，不判定 FAIL，可在后续任务补充。
- V1 无后端确认：`frontend/` 内无 pycore / fastapi / 数据库相关文件或依赖，符合“V1 无后端”约束。

## 执行命令（关键）

```powershell
# 脚本
cd Projects_Repo/creator-topic-library/frontend
npm run type-check   # exit 0
npm run lint         # exit 0
npm run build        # exit 0

# dev server（5199 strictPort）
npm run dev          # VITE ready, http://localhost:5199/
netstat -ano | Select-String ':5199'   # 127.0.0.1:5199 LISTENING
# 占用时二次启动：Error: Port 5199 is already in use（exit 1）

# 运行时验证（无头 Chrome）
node verify.cjs      # 首屏 6 选题/4 标签；reload 后仍 6/4；/tags 路由正常；theme token 生效
```

## 修复建议

无（全部通过）。