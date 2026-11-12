# 测试报告：T-002 P01 选题库主页：卡片列表 + 关键词搜索 + 组合筛选 + 排序 + 列表/看板视图切换 + 删除选题

- 项目：creator-topic-library（创作者选题灵感库）
- 任务类型：frontend（frontendIntegration.required=false，V1 纯前端 localStorage）
- 测试时间：2026-10-16 13:11（Asia/Shanghai）
- Tester Agent ID：codex-tester
- 验证方式：独立运行命令 + 无头 Chrome（playwright-core 1.55.0，chrome channel）运行时交互验证；不采信 Developer 声明
- 环境：Node v24.14.0 / npm 11.9.0；dev server http://127.0.0.1:5199（`vite --strictPort --port 5199`），验证完成后已关闭并释放端口

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| AC1 | 主页可见选题卡片列表，每张卡片展示标题、标签、状态、优先级和更新时间；无选题时显示空状态引导 | PASS | 首屏 6 张 .topic-card，逐卡断言字段齐全：title/tags/status/priority(优先高/中/低)/time(如 10-16 10:00)。置 topics=[] 后 reload：0 张卡片，Empty 描述为「还没有选题，点击"快速记录"开始创建第一条选题」。DOM 中 `<title>暂无数据</title>` 仅为 AntD Empty SVG 的无障碍标题，非可见文案 |
| AC2 | 搜索框输入关键词后列表实时只显示标题/内容/标签名包含该关键词的选题 | PASS | 标题搜「停更」→1 条；内容搜「意志力」→1 条（命中 content）；标签名搜「小红书」→2 条（命中 tag 名称而非正文）；子串搜「内容日历」→1 条（包含匹配，无分词）；清空 → 恢复 6 条。均在输入后即时刷新 |
| AC3 | 组合选择标签、状态、优先级、更新时间后列表同步刷新为符合全部条件；清除筛选恢复完整列表 | PASS | 状态=创作中→2 条；叠加优先级=高→1 条；再叠加标签「方法」→1 条（三条件与逻辑）。清除→6 条。时间筛选注入旧数据验证：注入 updated 100 天前/20 天前两条后共 9 条；近7天→7 条（排除 100 天，保留 20 天）；近30天→8 条（排除 100 天，保留 20 天），diff 正确 |
| AC4 | 切换排序（优先级/创建时间/更新时间）后列表顺序相应变化 | PASS | 默认(updated_desc)=[选题库/内容日历/一条视频/停更/新手/采访]；创建时间=[一条视频/停更/内容日历/新手/选题库/采访]；优先级=[选题库/一条视频/采访/内容日历/新手/停更]。三者顺序互不相同且符合各字段定义（优先级按 high>medium>low） |
| AC5 | 点击视图切换，在卡片列表与按状态分列的看板之间切换，展示内容立即变化 | PASS | 切「看板」后 .kanban-board 出现、.topic-grid 消失，4 列分组=待验证2/创作中2/已发布1/已放弃1；切「列表」后 .topic-grid 恢复、看板消失。（本任务只验展示分组，不验拖拽——拖拽属 T-007） |
| AC6 | 点击删除并在确认弹窗确认后选题从列表消失；刷新后仍未出现 | PASS | 删除首卡「创作者如何建立自己的选题库」→弹 .ant-modal 二次确认→确认后 6→5 条且该标题消失；page.reload() 后仍 5 条且不含被删标题（localStorage 已落盘） |
| AC7 | 顶部栏展示应用名、搜索框、快速记录按钮、随机选题按钮、标签管理入口和视图切换 | PASS | .home-header 实测：brand=「创作者选题灵感库」、搜索输入框存在、Segmented=[列表,看板]、按钮=[快速记录,随机选题,标签管理] |

## technicalChecks 逐条结果

| # | 检查 | 结果 | 说明 |
|---|------|------|------|
| TC1 | npm run type-check 通过 | PASS | `tsc --noEmit` 退出码 0 |
| TC2 | npm run lint 通过 | PASS | `eslint .` 退出码 0，无告警 |
| TC3 | npm run build 通过 | PASS | `tsc --noEmit && vite build` 退出码 0，1515 modules，产物写入 dist/（仅有 chunk>500kB 的常规提示） |
| TC4 | TopicCard 固定高度 ≥ 理论内容高度 × 1.2、最小 96px、justify-between | PASS | .topic-card 高度 288px（≥96px）；.ant-card-body 为 flex column + `justify-content: space-between`（见 src/styles/global.css）。20% 缓冲按实测卡片内容占位远低于上限 |
| TC5 | 浏览器抽查：实际内容高度 < 容器高度 × 0.85，长文本不溢出/不截断重叠 | PASS | 构造超长标题+超长内容卡片：标题/摘要均按 2 行/3 行 line-clamp 截断，实际占用内容高度/卡片高度 = 0.812（<0.85）；常规卡片 0.657；body/card 无溢出（scrollHeight-clientHeight=0）；全卡无重叠 |
| TC6 | 1280/1440/1920 宽度无错位 | PASS | 列表视图：三档 documentElement.scrollWidth==innerWidth（1280/1440/1920），均为 3 列；看板视图三档均为 4 列，无横向溢出 |
| TC7 | 搜索/筛选/排序均为纯前端完成，数据格式与 api-contracts.md 一致 | PASS | 过滤/排序逻辑在 pages/HomePage.tsx useMemo 内基于 store 数据纯前端完成，无网络请求。Topic/Tag 字段与 api-contracts.md 一致；服务层响应结构 {code,message,data(items,total,page,page_size)} 一致 |
| TC8 | 5199 端口 dev server 自动验证，不占用 5175 | PASS | `npm run dev` 启动于 http://localhost:5199/（strictPort），验证前后 5175 均 FREE；验证结束 Stop-Process 释放 5199（netstat 确认 RELEASED） |

## 路由状态封装（notes 要求）

| 检查 | 结果 | 说明 |
|------|------|------|
| P01/P04 路由切换状态用 key 封装保持路由内状态，不用 useEffect 同步 setState | PASS | src/components/AppShell.tsx 使用 `<Outlet key={location.pathname} />` 实现切换即重置；全库 useEffect 仅 AppShell loadLibrary 一处（数据加载副作用，非渲染期 setState 同步）。运行时验证：在 P01 输入关键词=「停更」(1 条) 后进入 /tags 再返回，关键词清空、列表恢复 6 条、视图=列表——状态按路由重挂载重置，符合「切换即重置」约定 |

## 代码与安全静态检查

| 检查 | 结果 | 说明 |
|------|------|------|
| 组件不直接访问 localStorage | PASS | 全库 localStorage 调用仅存在于 src/adapters/persistence/localStorageAdapter.ts；services/* 调 adapter；store 调 services；pages/components 无 localStorage。读写链 UI Page→Store(Zustand)→Service→Adapter→localStorage 与 PRD 分层一致 |
| 组件不直接请求后端 | PASS | src/components、src/pages 内无 axios/httpClient 直接调用 |
| TODO/FIXME/HACK、eslint-disable、@ts-ignore | PASS | 均未发现 |
| 硬编码密钥/Token | PASS | 未发现敏感值；theme.ts 中 token 为 AntD 主题字段名，非凭据 |

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 原型文案与本任务实现存在少量差异：品牌名原型为「选题灵感库」，实现为「创作者选题灵感库」（与 project.json 项目名一致）；清除按钮原型「清除筛选」实现为「清除」；分组标题原型「全部选题」实现为「全部」；优先级标签原型「优先级 高/中/低」实现为「优先高/中/低」；示例数据文案（原型「方法论」vs 实现「方法」；原型「采访一位全职创作者的问题清单」vs 实现「采访一位全职作者的选题清单」等） | P01 文案/示例数据 | 原型逐字一致性在 Plan.md 中归属用户门禁（"确认布局、配色、交互与 Pencil 原型一致"）；AC/TC 未把逐字文案列为验收标准，故不据此判 FAIL，交由用户门禁决策是否统一 |
| 2 | 默认排序实现为 updated_desc，api-contracts.md GET /api/topics 默认值为 created_desc；排序下拉同时存在「默认排序」与「更新时间」两个 updated_desc 选项 | P01 排序 / 契约 | 已在项目 experience.md 记录为待 Planner/用户确认项；建议明确统一默认排序口径 |
| 3 | 原型 P01 筛选栏未体现时间范围条件，实现按 PRD F-01-05/AC3 增加「全部时间/近7天/近30天」，属 AC 要求而非擅自添加 | P01 筛选 | 无需处理；仅说明原型与 AC 的覆盖差异 |
| 4 | 浏览器控制台存在 1 条 /favicon.ico 404 及 AntD「Card bordered 已弃用，建议用 variant」告警 | 全局/工程 | favicon 缺失沿自 T-001；`bordered` 弃用告警建议后续统一替换为 `variant`，均不影响本任务功能与验收 |

## 执行命令（关键）

```powershell
cd Projects_Repo/creator-topic-library/frontend
npm run type-check   # exit 0
npm run lint         # exit 0
npm run build        # exit 0 (1515 modules, dist/ 输出)

# dev server（5199 strictPort，run_in_background）
npm run dev          # VITE ready, http://localhost:5199/

# 独立浏览器验证（无头 Chrome，playwright-core 1.55.0，临时目录脚本，未改动业务代码）
node verify-t002*.cjs   # 逐条断言行结果见上表

# 端口清理
Get-NetTCPConnection -LocalPort 5199 -State Listen   # 定位 PID 后 Stop-Process；结果 5199 RELEASED
```

## 修复建议

无阻塞性缺陷（PASS）。建议在用户门禁或后续任务中处理「超出范围发现」第 1/2 条（原型文案统一、默认排序口径）。