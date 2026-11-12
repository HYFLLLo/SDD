# T-005 测试报告 — P04 标签管理页（复验）

## 结论

**PASS**

- 任务：T-005「P04 标签管理页：标签列表 + 新建 + 编辑 + 删除（联动选题）」
- 轮次：第 2 轮（Developer 修复 3 个原型偏差后复验）
- 验证日期：2026-10-20
- 验证方式：源码静态审查 + 实际执行 `npm run type-check` / `npm run lint` / `npm run build` + 5199 端口真实 dev server + Playwright 1.55.0（Chrome channel，1440×900）
- 依据：`.sdd/tasks.json` T-005 acceptanceCriteria / technicalChecks、`docs/api-contracts.md`、`docs/prototypes/04-标签管理页.png`、`docs/PRD.md` P04、`.sdd/experience.md`、`harness-core/dev-standards/frontend.md`
- 范围：仅 T-005 的 5 条 acceptanceCriteria 与 7 条 technicalChecks；范围外问题只列入“超出范围发现”。

## 上一轮 FAIL 项复核

| # | 上一轮问题 | 复核结果 | 证据 |
|---|---|---|---|
| 1 | P04 缺少原型「返回选题库」描边按钮 | **已修复 PASS** | `TagManager.tsx` 页头左侧新增 `<Button onClick={() => navigate('/')}>返回选题库</Button>`；运行时 `count=1`，class 含 `ant-btn-default` 且无 `ant-btn-link`，边框 `1px solid rgb(231, 213, 191)`；几何位置 btn.x=112 < title.x=226；点击后 URL 变为 `http://127.0.0.1:5199/` |
| 2 | 「全部标签」被做成下拉筛选而非分区标题 | **已修复 PASS** | 已改为 `<Typography.Title level={3} className="tag-manager__section-title">全部标签</Typography.Title>`，渲染为 `H3`，`font-size:24px`、`font-weight:700`；`.tag-manager__filter` 数量为 0，标签页 `.ant-select` 数量为 0；「共 7 个」文字右缘 1328 = 网格右缘 1328，与标题分列两侧（title.x=112 / textLeft≈1283） |
| 3 | 卡片「编辑/删除」为纯 `ant-btn-link` 文本链接 | **已修复 PASS** | 编辑：`ant-btn-default ... ant-btn-sm`，边框 `1px solid rgb(231, 213, 191)`，背景 `rgb(255, 249, 239)`；删除：`ant-btn-default ant-btn-dangerous ... ant-btn-sm`，边框 `1px solid rgb(212, 173, 171)`，文字 `rgb(169, 93, 93)`（浅红，非默认鲜红），均为 24px 小号描边按钮 |

## 验收标准逐条结果

| # | 验收标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | 从顶部导航点击标签管理，进入标签管理页，可以看到全部标签的名称、颜色和使用次数 | **PASS** | P01「标签管理」→ `/tags`；7 张卡片文本为“小红书 / 使用 2 次”“公众号 / 使用 2 次”“B站 / 使用 1 次”“抖音 / 使用 1 次”“生活 / 使用 1 次”“方法 / 使用 1 次”“效率 / 使用 1 次”；7 个色点均渲染非透明颜色 |
| 2 | 新建标签（名称 + 颜色）保存后出现在列表；重名给出提示且不创建 | **PASS** | 重名“小红书”提示“标签名称已存在”，卡片保持 7 张；新建“测试标签”并选 `#4F6F8F` 后卡片 7→8，新行“测试标签 / 使用 0 次”，色点 `rgb(79, 111, 143)` |
| 3 | 编辑名称/颜色后列表更新，回主页相关选题同步 | **PASS** | 改为“小红书改”+ `#D98A4A` 后列表显示“小红书改 / 使用 2 次”；回 P01 后卡片 chip 文本“小红书改”、颜色 `rgb(217, 138, 74)` |
| 4 | 删除二次确认后从列表消失，主页不再显示，刷新后仍生效 | **PASS** | 确认框“删除标签 / 确定要删除“测试标签”吗？删除后无法恢复。/ 取消 / 删除”；取消后仍保留 1 张；确认后 8→7 且该标签 0 张；刷新后仍 7 张。删除被引用标签“公众号”后主页正文无该标签，`tag_ids` 无悬空 id |
| 5 | 点击返回或主页入口可回到选题库主页 | **PASS** | 新增「返回选题库」按钮点击回到 `/`；顶部导航「选题库」链接同样可返回 |

## technicalChecks 结果

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | `npm run type-check` 通过 | **PASS** | `tsc --noEmit` 退出码 0，无输出 |
| 2 | `npm run lint` 通过 | **PASS** | `eslint .` 退出码 0，无告警 |
| 3 | `npm run build` 通过 | **PASS** | `tsc --noEmit && vite build` 成功，1518 modules，产物 `dist/assets/index-DC8WwOm8.js`；仅有 chunk >500 kB 的非阻断提示 |
| 4 | `usage_count` 为计算字段，实时更新且不持久化 | **PASS** | `StoredTag = Omit<Tag, 'usage_count'>`；`listTags()` 每次基于 `readTopics()` 计算；`TagManager` 用 `useMemo` 聚合。运行时 localStorage 标签对象字段仅 `id,name,color,created_at` |
| 5 | 删除标签经服务层一次性清理所有关联 `tag_ids` | **PASS** | `tagService.deleteTag()` 内 `writeTags` + `writeTopics` 同步；删除“公众号”后 `dangling=[]` |
| 6 | P01/P04 互切 key 化重挂载，无 effect 内同步 setState | **PASS** | `AppShell.tsx` 使用 `<Outlet key={location.pathname} />`；`TagManager` 无 `useEffect`。运行时 P01 搜索“视频”（1 条）→ P04 → 回 P01，搜索框为空、恢复 6 条 |
| 7 | 5199 端口启动 dev server 自动验证 | **PASS** | 启动前 `PORT_5199_FREE`；`npm run dev -- --host 127.0.0.1`（脚本含 `--strictPort --port 5199`）监听成功；验证后按 OwningProcess 清理，复查 `PORT_5199_CLEAN` |

## 复验断言统计

- Playwright 自动断言：**27 PASS / 0 FAIL**
- 覆盖：3 个修复点（8 条断言）+ 上一轮全部 PASS 项回归（19 条断言）
- 截图：`%TEMP%\t005-recheck\01-p04-fixed.png`、`02-home-linkage.png`、`03-home-reset.png`
- 日志：`%TEMP%\t005-recheck\log.txt`

## 视觉核对

- P04 截图与原型结构一致：页头左侧「返回选题库」描边按钮 + 「标签管理」标题，右侧「新建标签」主按钮；下方「全部标签」大号粗体标题与右侧「共 N 个」；三列标签卡，卡片内色点 + 名称 + 使用次数 + 小号描边「编辑」「删除」。
- 原型图中部分汉字因素材字体缺字显示为方框，本轮按可见布局、控件形态、颜色与完整可读文字（「公众号」「使用 12 次」「删除」「共 6 个」）及 PRD 文案判定；修复后实现结构与原型一致。

## 超出范围发现

- **P01「随机选题」按钮尚无行为**：`HomeHeader` 通过 `onRandomPick={() => undefined}` 传入空实现，属 T-006/T-007 范围。
- **构建 chunk 957 kB > 500 kB 警告**：工程优化项，非 T-005 验收范围。
- **AntD 控制台告警**：`[antd: Card] 'bordered' is deprecated. Please use 'variant' instead.` 与一次 404 资源请求，非阻断、不在 T-005 验收范围。
- 原型图字体缺字属原型素材问题，不是实现缺陷。

## 判定

- acceptanceCriteria：5/5 **PASS**
- technicalChecks：7/7 **PASS**
- 原型高保真强制项：3 个上一轮偏差全部修复
- 任务状态：`passed`
