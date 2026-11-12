# 测试报告：T-004 P03 快速录入弹窗：新建选题 + 标题必填校验 + 内联新建标签

- 项目：creator-topic-library（创作者选题灵感库）
- 任务类型：frontend（`frontendIntegration.required=false`，V1 纯前端 localStorage，无后端）
- 测试时间：2026-10-16 15:25（Asia/Shanghai）
- 验证方式：独立运行命令 + 服务层/Store 运行时验证（Node + Vite SSR bundle）+ 无头 Chrome 运行时交互验证（playwright 1.55.x，`channel=chrome`）；不采信 Developer 声明
- 环境：Node v24.14.0 / npm 11.9.0；dev server `http://127.0.0.1:5199`（`vite --strictPort --port 5199`），验证完成后已关闭并确认端口释放
- 被测文件：`frontend/src/components/QuickCreateModal.tsx`、`components/HomeHeader.tsx`、`pages/HomePage.tsx`、`stores/useTopicLibraryStore.ts`、`services/tagService.ts`、`services/topicService.ts`、`services/index.ts`、`adapters/persistence/localStorageAdapter.ts`、`types/topic.ts`、`types/tag.ts`、`types/api.ts`

## 结果：PASS

全部 5 条 acceptanceCriteria 与 6 条 technicalChecks 均通过；发现 1 项非阻塞潜在缺陷（见「超出范围发现」第 1 条），不影响本任务 AC 判定。

## 验收标准逐条验证（acceptanceCriteria）

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| AC1 | 在主页点击快速记录按钮，弹出快速录入弹窗 | PASS | 初始 `.quick-create-modal` 不可见；点击顶部「快速记录」（`HomeHeader.tsx` 绑定 `onQuickCreate` → `HomePage` `setQuickCreateOpen(true)`）后弹窗可见。弹窗标题 `.ant-modal-title` 实测 = `快速灵感`；表单字段顺序实测 = `标题,内容,来源,标签,状态,优先级`（与任务 description 一致）；主按钮实测 = `保存选题` |
| AC2 | 填写标题、内容、来源、标签、状态、优先级并保存后，弹窗关闭，新选题出现在主页列表顶部；刷新后仍存在 | PASS | 填写 标题/内容/来源 并保留默认标签后点「保存选题」：弹窗关闭（`.quick-create-modal` 不可见）；localStorage `creator-topic-library.topics.v1` 计数 6→7；记录字段键集 = `content,created_at,id,notes,priority,source,status,tag_ids,title,updated_at`（与 api-contracts.md Topic 契约一致）；首张卡片标题 = 新标题（列表顶部）；`page.reload()` 后新选题仍在且仍在列表顶部、新标签仍在标签池。另验证显式改选状态=创作中/优先级=高时落盘值分别为 `working`/`high`，改选生效 |
| AC3 | 不填标题直接点保存时，页面给出明确的标题必填提示，选题未被创建 | PASS | 空标题点「保存选题」：`.ant-form-item-explain-error` 实测 = `标题不能为空`（来源 `Form.Item rules=[{required:true, whitespace:true, message:'标题不能为空'}]`）；弹窗保持打开；localStorage 选题数 6→6（未创建） |
| AC4 | 新建选题时状态默认显示为'待验证'，优先级默认显示为'中' | PASS | 弹窗打开后状态 Select 显示文本实测 = `待验证`，优先级 Select 显示文本实测 = `中`（`initialValues` = `status: 'pending'`、`priority: 'medium'`；`priorityQuickOptions` 文案 高/中/低）。服务层兜底：`createTopic` 未传 status/priority 时落盘 `pending`/`medium` |
| AC5 | 在弹窗标签选择中内联新建标签（输入名称并选择颜色）后，新标签立即出现在可选标签列表；保存选题后该选题带上新标签，主页筛选标签条件也能看到该新标签 | PASS | 点「新建标签」展开内联面板 → 填入名称并选择第 3 个色板 → 点「添加」：① 标签池持久化（localStorage `...tags.v1` 7→8，新标签 `color` 与所选色板一致）；② 弹窗标签 Select 立即自动选中新标签；③ 重开下拉，选项列表实测含新标签（`小红书,公众号,B站,抖音,生活,方法,效率,浏览器新标签`）；④ 保存选题后落盘 `tag_ids` 含新标签 id；⑤ 刷新后主页筛选栏标签列表实测含新标签，点选后列表仅剩带该标签的选题（1 条） |

## technicalChecks 逐条结果

| # | 检查 | 结果 | 说明 |
|---|------|------|------|
| TC1 | npm run type-check 通过 | PASS | `tsc --noEmit` 独立全量执行，退出码 0，无输出 |
| TC2 | npm run lint 通过 | PASS | `eslint .` 独立全量执行，退出码 0，无告警 |
| TC3 | npm run build 通过 | PASS | `tsc --noEmit && vite build` 退出码 0，1517 modules，dist/ 输出（仅 chunk>500kB 常规提示，非错误） |
| TC4 | 内联新建标签调用标签服务方法并持久化，标签名唯一规则在服务层校验（重名返回错误响应，data 为 null） | PASS | 组件经 `store.createTag` → `tagService.createTag` 落盘，组件未直接读写 localStorage。服务层运行时验证：首次 `createTag({name:'独立标签'})` → `{code:200,...}` 且落盘；重名（含前后空格 trim 后同名）→ `{code:400, message:'标签名称已存在', data:null}`；标签池未重复增长。UI 层同名校验实测显示服务层错误文案 `标签名称已存在`，且未重复落盘（同名标签数 = 1） |
| TC5 | 新建选题的默认值：status=pending、priority=medium，字段结构与 api-contracts.md Topic 契约一致 | PASS | 服务层直接调用 `createTopic` 不传 status/priority → 落盘 `status=pending`、`priority=medium`；记录键集 = `content,created_at,id,notes,priority,source,status,tag_ids,title,updated_at`（与契约 10 字段完全一致，无多余/缺失字段）。UI 默认显示 待验证/中（见 AC4） |
| TC6 | 在 5199 端口启动 dev server 完成自动验证 | PASS | `npm run dev`（= `vite --strictPort --port 5199`）启动于 `http://127.0.0.1:5199/`，本任务全部 AC/TC 均在该端口完成自动验证；验证完成后关闭进程，确认 5199 监听数 = 0；全程未占用 5175（验证前后 5175 监听数均为 0） |

## 端口纪律

- 验证前：5199 无监听。
- 启动：`cd frontend && npm run dev -- --host 127.0.0.1`（脚本已含 `--strictPort --port 5199`），Vite ready。
- strictPort 复验：在 5199 被占用时再次启动 `npm run dev`，stderr 直接报 `Error: Port 5199 is already in use` 并退出，未静默换端口（未回退 5200）。
- 验证后：按 `Get-NetTCPConnection -LocalPort 5199` 定位 OwningProcess（vite 与 npm 两进程）并 `Stop-Process -Force` 清理；确认 `5199 listen = 0`、`5175 listen = 0`，无残留 node 进程。

## 分层与静态检查

| 检查 | 结果 | 说明 |
|------|------|------|
| 数据经 Zustand + service 层读写 localStorage，组件不直接访问 localStorage | PASS | 全 `src/` 内 `localStorage` 调用仅存在于 `adapters/persistence/localStorageAdapter.ts`（4 处）；`services/*` 调 adapter；`stores/useTopicLibraryStore.ts` 调 services；`QuickCreateModal.tsx`/`HomePage.tsx`/`HomeHeader.tsx` 无 localStorage、无 axios 直连 |
| 硬编码 URL / 密钥 / 标记 | PASS | `src/` 内无 `http://` / `https://` / `localhost:<port>` 字面量（rg 退出码 1=无匹配）；无 TODO/FIXME/HACK；无硬编码密钥 |
| 敏感信息泄露 | PASS | `.md`/`.json`/`.sdd/**`/`docs/**` 未发现真实 API Key/Token/Secret（本项目 V1 无外部服务） |
| 服务层响应契约 | PASS | 服务方法统一返回 `{code, message, data}`；错误响应 `data` 为 `null`（`title 不能为空` / `标签名称已存在` 均实测 code=400、data=null） |

## 执行命令（关键）

```powershell
cd Projects_Repo/creator-topic-library/frontend
npm run type-check   # exit 0
npm run lint         # exit 0
npm run build        # exit 0 (1517 modules)

# 服务层 / Store 运行时验证（临时 bundle，未改动业务代码）
npx vite build --config .tmp-verify/vite.verify.config.ts   # SSR bundle 业务模块
node .tmp-verify/dist/harness.mjs                           # 28/28 断言 PASS

# dev server（5199 strictPort）
npm run dev -- --host 127.0.0.1

# 无头 Chrome 交互验证（临时脚本，未改动业务代码）
node .tmp-verify/browser.cjs    # AC1/AC2/AC3/AC4/AC5 全 PASS
```

关键输出（节选）：
- 服务层：`empty title code=400 | code=400 msg=标题不能为空`、`empty title not persisted | 6->6`、`duplicate tag message | 标签名称已存在`、`duplicate tag data=null`、`Topic keys match api-contracts | content,created_at,id,notes,priority,source,status,tag_ids,title,updated_at`、`refresh: new tag visible in tag pool`。
- 浏览器（AC 全通过）：`AC4 default status shows 待验证 | 待验证`、`AC4 default priority shows 中 | 中`、`AC3 empty title shows 标题不能为空`、`AC5 duplicate tag shows service error 标签名称已存在`、`AC2 new topic appears at top of home list | 浏览器端新建选题`、`AC2 new topic survives page refresh`、`AC5 filtering by new tag returns the new topic only`。

## 原型对齐（P03，dev-standards/frontend.md §11 + tester.md 前端高保真校验）

原型依据：`docs/prototypes/README.md`（P03 说明）+ `docs/prototypes/03-快速录入弹窗.png`（Pencil 源 `.pen` 需在编辑器中打开，本次无法直接读取，故以图片原型 + PRD 为准）。

| 检查 | 结果 | 说明 |
|------|------|------|
| 弹窗结构/字段对齐 | PASS | 原型：标题「快速灵感」、字段 标题*/内容/来源/标签（多选 chip）、底部 取消/保存选题。实现：标题「快速灵感」，字段顺序 标题/内容/来源/标签/状态/优先级（状态、优先级为 PRD F-03-01 与任务 description 明确要求，原型未画出但不冲突），底部 取消/保存选题，一致 |
| 文案对齐 | PASS（含 1 项无法逐字判定） | 原图字体缺字形导致部分文案渲染为缺字方框（如 `用一句□□下□个□□`、按钮 `快速□□`），无法逐字校验。基于可辨识字形与上下文核对：弹窗标题 4 字（快速□□）与实现「快速灵感」长度与首尾字形一致；占位符/按钮文案与实现同源、无自造；PRD 流程图 L254 出现 `F[快速记录灵感]`，佐证原型的 `快速□□` 为「快速记录灵感」类文案（该差异属标题用词演化，未造成自造文案）。实现未出现与原型/PRD 冲突的文案 |
| 视觉样式 | PASS | 暖纸色调、主按钮橙红（`#C2571B` 系）、圆角/间距与 P01/P02 同源（截图比对） |

## 超出范围发现（不影响当前任务 PASS/FAIL 判定）

| # | 问题 | 所属模块 | 影响 | 建议处理 |
|---|------|---------|------|---------|
| 1 | **弹窗打开动画期间的草稿复位竞态（潜在缺陷）**：`afterOpenChange` 内 `form.resetFields()` 在打开动画完成后执行；若用户在动画窗口内（实测约 <400ms）输入或点击保存，复位会覆盖已输入内容，甚至可把上一次「取消」的草稿（幽灵数据）当作本次表单值提交，创建出用户并未确认的选题。实测：刚打开即输入 → 4/6 次输入被清空；复现「取消草稿 → 重开立即点保存 → 生成幽灵选题」。以正常人工节奏（打开后停顿再加字段）完整流程 100% 通过，故不构成任何 AC 违反 | `frontend/src/components/QuickCreateModal.tsx`（`afterOpenChange`） | 低概率、需抢在动画窗口操作；不影响本次 AC | 建议把复位从 `afterOpenChange` 移到「打开动作」侧（例如 `HomePage` 打开前先 `form.resetFields()`，或改用 Modal `destroyOnHidden` / 受控 `open` 时以 `useEffect` 在 `open` 由 false→true 且动画开始前复位），使复位先于动画与用户输入完成 |
| 2 | `frontend/T-004-pw-fix.patch`：Developer 遗留的临时 patch 文件（530B，全仓无任何引用/导入） | `frontend/`（构建产物目录外） | 无功能影响 | 建议删除该临时文件，保持 `frontend/` 干净（`npm run build`/`lint`/`type-check` 不受影响） |
| 3 | 控制台存在 `antd: Card \`bordered\` is deprecated. Please use \`variant\` instead.`（来自 `TopicCard.tsx`，T-002 引入）与 `/favicon.ico` 404（T-001 引入） | 全局/工程 | 无功能影响，非本任务范围 | 建议后续任务统一将 `bordered` 改为 `variant`，并补 favicon |

## 阶段错配检查

任务 `type=frontend` 且 `frontendIntegration.required=false`（Mock/本地存储阶段）。本次验证遵守 Mock 阶段测试边界：未做多标签页/跨会话同步、未验证真实后端连通性、未做真实 WebSocket 验证；「刷新后数据仍存在」一项在任务 AC 中明确要求且本项目使用 localStorage 持久化，属允许验证范围。无所属验收标准超出 Mock 阶段能力边界。

## 修复建议

- 本任务无阻塞性缺陷（PASS）。
- 建议 Developer 在后续任务（或本任务修复轮）处理「超出范围发现」第 1 条（弹窗复位竞态），可显著提升快速录入体验健壮性；第 2、3 条建议一并清理。