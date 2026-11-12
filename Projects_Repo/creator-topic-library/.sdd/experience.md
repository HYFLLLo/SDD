# 项目经验

> 当前项目长期有效的经验。  
> Developer / Tester / Bugfix 在任务完成后维护本文件。

---

## Harness 系统经验摘要

新项目开始时，Developer / Tester / Bugfix 需要同时参考：

- 当前项目经验：`.sdd/experience.md`
- 系统级经验：`<Harness 根目录>/memory/harness-experience.md`

---

（项目经验将在开发过程中追加）


## 2026-10-16｜T-001 前端工程脚手架经验

- 包管理器选用 npm（Node v24.14.0、npm 11.9.0）；依赖安装全部在 `frontend/` 内完成。
- `typescript-eslint@8.x` 的 peer 要求 `typescript <6.1.0`，因此不能直接使用 npm `typescript@latest`（当前为 7.x），本项目固定 `typescript@6.0.3`，避免安装/类型检查兼容风险。
- Windows PowerShell 使用 `Set-Content -Encoding utf8` 写 JSON 文件会带 BOM；Vite/PostCSS 读取 `package.json`、`tsconfig.json` 时会把 BOM 当成 JSON 语法错误。TS/JSON 配置建议用 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)` 写。
- Ant Design 6.6 已弃用 `Space direction` 和 `List`：`Space` 改用 `orientation="vertical"`，演示列表改为普通 div + Typography，避免控制台警告。
- 5199 端口纪律已验证：`npm run dev -- --host 127.0.0.1 --port 5199` 使用 `--strictPort`；端口被占用时 Vite 直接报错退出，不静默换端口。清理进程先 `netstat -ano | Select-String ':5199'` 定位 PID，再用 `Stop-Process -Id <PID> -Force`。
- 无 Playwright 测试依赖时，可用已安装 Chrome 做运行时验证：`npx --yes playwright@1.55.0 screenshot --browser=chromium --channel=chrome --wait-for-selector="text=<页面文案>" http://127.0.0.1:5199/ <截图>`；selector 找不到会超时失败，可作为轻量视觉/渲染验证。

## 2026-10-16｜T-002 P01 选题库主页核心功能经验
- 默认排序按 P01 原型视觉对齐使用 `updated_desc`；卡片列表初始顺序为更新时间倒序，排序选项中另提供“创建时间/优先级”。后续若要与 `api-contracts.md` 的默认 `created_desc` 完全一致，需 Planner/用户确认并统一。
- `TopicCard` 固定高度采用 288px；长标题 2 行截断、摘要 3 行截断，`bodyScrollHeight === bodyClientHeight`。Playwright 抽测前 3 张卡片内容高度/卡片高度约 0.44~0.52，满足 `< 0.85` 的 20% 缓冲验收。
- React hooks purity 规则禁止在 render 期间调用 `Date.now()`；时间筛选的“当前时间”用 `useState(() => Date.now())` 惰性初始化，避免直接触发 `react-hooks/purity`。
- Ant Design 6.6 的 `modal.confirm` 中“删除”确认按钮在 Playwright 可访问名里可能是“删 除”（带空格），定位用正则 `/删\s*除/`，且必须限定在 `.ant-modal` 内，避免命中卡片上的删除按钮。
- 本机 PowerShell 直接以参数调 `codex.exe --codex-run-as-apply-patch` 会丢失 JSX 属性双引号；改用临时 patch 文件 + Node `child_process.spawnSync(exe, ['--codex-run-as-apply-patch', patch])` 可保留 UTF-8 与双引号。
- 5199 端口验证：`npm run dev -- --host 127.0.0.1` 已带 `--strictPort`；结束验证后按 `Get-NetTCPConnection -LocalPort 5199` 定位并 `Stop-Process` 清理监听进程。
- 响应式抽测 1280/1440/1920：列表 3 列、看板 4 列，`scrollWidth <= innerWidth`，无横向错位。

## 2026-10-16｜T-003 P02 选题详情抽屉经验
- 抽屉内编辑与查看分离：查看态展示全部字段，编辑态使用 `Form` 只允许修改 `title/content/notes/source/tag_ids/status/priority`，`created_at/updated_at` 保持只读；保存后由 store 用 service 返回的完整 Topic 覆盖原项，列表与抽屉同步更新。
- 标题必填用 `Form.Item rules=[{ required: true, whitespace: true, message: '标题不能为空' }]`，`validateFields()` 失败时直接返回，避免在校验失败时误提交。
- 编辑态保存后不要依赖 `message.success` 做自动化定位：AntD message 渲染在 Drawer 外层的 portal，scoped drawer locator 找不到；Playwright 验证改用视图态更新后的标题文本或“编辑”按钮重新出现作为成功信号。
- Ant Design 6.6 Drawer 的 `width` 已弃用，改用 `size={560}`；`Input.TextArea autoSize={{ minRows, maxRows }}` 可满足长文本不溢出，长文本抽测 `scrollWidth <= clientWidth`。
- 主题卡片改为整卡可点击后，删除按钮必须 `event.stopPropagation()`，否则会同时触发抽屉打开和删除确认。
- 5199 运行验证继续遵循系统经验：先查 `Get-NetTCPConnection -LocalPort 5199` 确认无陈旧监听，再启动 `npm run dev -- --host 127.0.0.1`，验证后按 OwningProcess 清理端口，避免旧进程占用端口导致误验证旧代码。

## 2026-10-16｜T-004 P03 快速录入弹窗经验
- 快速录入复用 `TopicDraft` 时，`notes` 不在 P03 表单中展示，但 Topic 契约要求该字段；保存时显式补 `notes: ''`，避免 `undefined` 混入新建选题对象。
- 内联新建标签放在标签 `Form.Item` 正下方、作为独立可展开面板，比塞进 AntD Select `popupRender` 更稳，Playwright 可直接定位 `输入标签名称`/颜色 swatch/添加按钮；创建成功后用 `form.setFieldValue('tag_ids', [...旧值, 新标签ID])` 自动选中新标签。
- 标签唯一性必须在 `tagService.createTag` 中先 `readTags()` 再按 trim 后名称判重；重复返回 `{code:400, message:'标签名称已存在', data:null}`，组件据此显示服务层错误，不重复造状态。
- AntD `Button` 对两个汉字的按钮会自动插入空格（如“添 加”“取 消”），Playwright/自动化定位要用 `/添\s*加/` 或先 `replace(/\s+/g,'')` 规范化；这和 T-002 的“删 除”是同一坑。
- 用 CDP 手写 DOM 输入模拟 React 受控 Form 字段时，`Input.insertText`/native setter 只能改 DOM value，AntD Form store 未更新，后续组件重渲染会把输入框清空；自动化验证应优先用 Playwright `locator.fill()`，它会稳定触发 React onChange。
- 5199 短时验证继续沿用既有端口纪律：验证前查端口、`npm run dev -- --host 127.0.0.1`（已 strictPort）、验证后按 OwningProcess 清理，不留陈旧 Vite 进程。

## 2026-10-16｜T-005 P04 标签管理页经验
- `usage_count` 不做持久化：引入 `StoredTag = Omit<Tag, 'usage_count'>`，适配层只读写 `StoredTag`；`listTags()` 每次基于 `readTopics()` 实时计算 usage_count，避免 localStorage 存冗余值。
- 标签页展示使用次数时，不直接信 store 里从初始加载带回的 `tag.usage_count`，而是在 `TagManager` 内用 `useMemo` 从当前 `topics/tags` 重新聚合，保证 P01 增删选题后切到 P04 也实时正确。
- 删除标签要在一个 service 方法内同时完成两件事：`writeTags(filter)` + `writeTopics(topics.map(去掉该 tag_id))`，store 的 `deleteTag` 同步映射 topics 的 `tag_ids`，避免悬空 id 与界面不同步。
- 新建/编辑判重都按 `name.trim()` 比较，并再对存量标签 `tag.name.trim()`；编辑时必须 `tag.id !== tagId` 排除自身，否则把名字原样保存会被误判为重复。
- P01/P04 状态重置继续依赖 `AppShell` 的 `<Outlet key={location.pathname} />`，不要新增 `useEffect` 同步 `setState`，可避免 `react-hooks` lint 问题。
- 标签卡采用自适应高度布局，不设固定高度容器，因此不触发“容器高度 ≥ 内容理论高度 × 1.2”的验收约束；三列网格在 1100px/720px 断点退化为 2 列/1 列。
- P04 原型高保真修复：页头左侧必须放「返回选题库」描边按钮（`navigate('/')`），与全局导航共存；「全部标签」是分区大标题而非 `Select` 筛选，不要擅自加交互。
- 标签卡操作按钮用 `Button type="default" size="small"` 描边形态；删除按钮虽保留 `danger`，但要覆盖 AntD 默认鲜红为原型浅红描边（边框 `#d4adab`、文字 `#a95d5d`），否则 Tester 按 `rgb(255, 77, 79)` 判样式不符。

## 2026-10-16｜T-006 随机选题经验
- 随机候选池直接从 `HomePage` 已计算好的 `filteredTopics` 再 `filter(status !== 'published' && status !== 'abandoned')`，不重写搜索/标签/状态/优先级/时间筛选，确保随机与列表口径完全一致。
- 随机数只放在事件处理器（打开弹窗、点击“换一个”）里调用 `Math.random()`，禁止在 render/`useMemo` 内取随机值，避免 `react-hooks/purity` 触发非确定性告警。
- “换一个”在候选数大于 1 时先排除当前 `randomTopic?.id` 再从剩余候选等概率抽取，保证能“换成另一条”；仅 1 个候选时回退原池，避免死循环。

## 2026-10-20｜T-007 看板状态拖动 + 列表快捷菜单改状态经验
- 状态快速修改统一复用 store 的 `updateTopic(topic.id, TopicDraft)`：从当前 `Topic` 展开完整 `TopicDraft`（含 `notes`/`source`/`tag_ids`），仅替换 `status`，不新增绕过 service 层的本地状态写入，保证 localStorage 只经 service 更新。
- 列表快捷菜单用 AntD `Dropdown` 包裹原状态 `Tag`，外层 span 的 `onClick` 只做 `stopPropagation()`，避免点开下拉时同时触发 `Card` 的详情抽屉；菜单点击后通过统一 `onStatusChange` 回调更新。
- 看板拖拽用原生 HTML5 drag/drop，不在 render 期取随机值：`onDragStart` 写 `dataTransfer.setData` 并记录 `draggedTopicId`，`onDragOver` `preventDefault()`，`onDrop` 用 state 中的 id 找到 Topic 后调用统一回调。
- 拖拽 wrapper 必须加 `flex: 0 0 auto`，否则 `.kanban-column__body` 的 flex 列布局会把固定 288px 卡片压缩，破坏 20% 高度缓冲验收。

## 2026-10-20｜T-008 E2E 回归 + 启动/走查文档经验
- **陷阱**：`npx playwright@1.55.0` 只把 CLI 放进 PATH，不会让 Node 脚本解析到 `playwright` 模块；临时 E2E 目录里应直接 `npm install playwright@1.55.0 --no-save --no-package-lock`，再用 `node_modules/.bin/playwright.cmd test` 运行。
- **陷阱**：Playwright CLI 从项目根目录执行时，`testDir: '.'` + 绝对测试文件路径会报 `No tests found`；把工作目录切到临时测试目录，传入相对文件名最稳。
- **经验**：E2E 回归要先 `localStorage.clear()` 再 `reload()`，让种子数据重新初始化，避免前序任务遗留数据污染断言；删除型回归最后再断言 localStorage 中对应 id/title 已不存在。
- **经验**：AntD Select 自动化定位优先用 `.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option`，再按文案过滤；四个筛选下拉框要按 `.topic-filter-select` 的 nth 区分。
- **经验**：HTML5 看板拖动用 Playwright `locator.dragTo()` 可稳定覆盖 React 的原生 `onDragStart/onDrop`；拖后断言目标列的 `.kanban-card` 文案比只点状态菜单更接近真实用户路径。
- **避坑**：确认 dev server 关闭时，`Get-NetTCPConnection -LocalPort 5199` 可能仍返回 `TimeWait`，这不是监听进程；必须用 `-State Listen` 判断，避免误以为端口未释放。
- **避坑**：AntD 两个汉字按钮的 accessible name 仍会被插空格（如“编 辑”“删 除”“保 存”），E2E 定位统一用 `/编\s*辑/`、`/删\s*除/`、`/保\s*存/`。
- **陷阱**：种子数据当前 `published` 仅 1 条，回归脚本若写 `共 2 条` 或 `共 [3-6] 条` 会与实际渲染不符；断言先读 `frontend/src/mocks/library.ts` 的真是状态分布，别凭历史种子猜。
- **经验**：随机选题“空池”回归不要用“已发布”筛选构造，因为随机候选本就会排除 `published/abandoned`，容易与列表口径混淆；用无结果的搜索词让 `filteredTopics` 真正为空，再断言空状态更稳定。
- **避坑**：AntD `Segmented` 的可访问角色是 radio，但真正可点击的是可见的 `.ant-segmented-item`；直接 `getByRole('radio').click()` 会命中不可见 input，触发 `element is not visible` 超时。
- **避坑**：`RandomPicker` 的 Modal 设置 `footer={null}`，没有“取消”文案按钮；回归脚本关闭弹窗应使用 `page.keyboard.press('Escape')` 或点 `.ant-modal-close`，不要等 `取 消`。
- **陷阱**：同一测试里连续成功操作会叠加多个 AntD `message` 文案，`getByText('保存成功')` 会 strict mode violation；统一用 `.last()` 或限定在最新 message notice 中。
- **避坑**：标签名有 `maxLength=20`，E2E 生成的“唯一值-标签”可能超过 20 被截断，导致后续卡片定位失败；测试内标签名要单独生成并确保不超过 20 字符。
- **陷阱**：localStorage 不是 Zustand 序列化后的 `creator-topic-library` 单 key，而是分别存储 `creator-topic-library.topics.v1` 和 `creator-topic-library.tags.v1` 两个数组；回归断言持久化必须直接读这两个 key。
