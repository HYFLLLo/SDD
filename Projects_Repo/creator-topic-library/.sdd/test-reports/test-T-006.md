# T-006 测试报告 — 随机选题

## 结论

**PASS**

- 任务：T-006「随机选题：基于当前筛选结果的随机抽取 + 换一个 + 空状态」
- 验证日期：2026-10-20
- 验证方式：源码静态审查 + 实际执行 `npm run type-check` / `npm run lint` / `npm run build` + 5199 端口真实 dev server + Playwright 1.55.0（Chrome channel，1440×900）
- 依据：`.sdd/tasks.json` T-006 acceptanceCriteria / technicalChecks、`docs/api-contracts.md`、`docs/PRD.md` F-01-07 / P01、`docs/prototypes/README.md`、`docs/prototypes/01-选题库主页.png`、`.sdd/experience.md`、`harness-core/dev-standards/frontend.md`
- 范围：仅 T-006 的 5 条 acceptanceCriteria 与 6 条 technicalChecks；范围外问题只列入“超出范围发现”。

## 验收标准逐条结果

| # | 验收标准 | 结果 | 证据 |
|---|---|---|---|
| 1 | 主页点击“随机选题”，弹窗展示一条符合当前列表的随机选题（含标题、标签、状态） | **PASS** | 点击后 `.random-picker` 弹窗出现，展示标题“创作者如何建立自己的选题库”、标签“小红书/方法”、状态“创作中”；标题属于默认候选池，状态为待验证/创作中，未抽到已发布/已放弃 |
| 2 | 点击“换一个”展示另一条 | **PASS** | 连续点击 4 次后标题集合为“创作者如何建立自己的选题库 / 新手做小红书的第一周踩坑 / 从零开始做一个内容日历”，至少 2 条；代码在候选 >1 时排除当前 id 再抽取 |
| 3 | 先筛选缩小范围，随机结果符合该筛选 | **PASS** | 标签“小红书”筛选后列表 2 条，随机结果标题为“新手做小红书的第一周踩坑”、标签含“小红书”；状态“创作中”筛选后列表 2 条，随机结果状态为“创作中” |
| 4 | 候选池为空（如全部已发布）时显示空状态 | **PASS** | 状态筛选“已发布”后列表 1 条但随机候选为空；弹窗显示 `Empty`，文案“没有符合条件的选题，试试调整搜索或筛选条件”，无结果卡、无报错 |
| 5 | 弹窗中点击该选题可打开 P02 详情抽屉 | **PASS** | 点击“查看详情”后 `.topic-detail-drawer` 可见，抽屉标题与抽中标题一致（“新手做小红书的第一周踩坑”） |

## technicalChecks 结果

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1 | `npm run type-check` 通过 | **PASS** | `tsc --noEmit` 退出码 0 |
| 2 | `npm run lint` 通过 | **PASS** | `eslint .` 退出码 0，无告警 |
| 3 | `npm run build` 通过 | **PASS** | `tsc --noEmit && vite build` 成功，1519 modules，产物 `dist/assets/index-BDAhqusI.js`；仅有 chunk >500 kB 的非阻断提示 |
| 4 | 候选池 = 当前筛选结果 ∩ 排除 published/abandoned，等概率抽取，多次调用分布合理 | **PASS** | `randomCandidates = filteredTopics.filter(status !== 'published' && status !== 'abandoned')`；`Math.random()` 仅在打开/换一个事件处理器调用；24 次抽样分布为 4 个候选各 5/5/5/9，非固定值 |
| 5 | 与列表筛选共用同一管道，不重复实现 | **PASS** | `randomCandidates` 直接基于 `filteredTopics` 再过滤状态，搜索/标签/状态/优先级/时间筛选均复用同一 `useMemo` 管道 |
| 6 | 5199 端口启动 dev server 自动验证 | **PASS** | 启动前 `PORT_5199_FREE`；`npm run dev -- --host 127.0.0.1`（脚本含 `--strictPort --port 5199`）监听成功；验证后按 OwningProcess 清理，复查 `PORT_5199_CLEAN` |

## 静态逻辑确认

- `HomePage.tsx` 中 `randomCandidates` 基于已计算的 `filteredTopics`，未重写筛选逻辑。
- `Math.random()` 出现在 `handleOpenRandomPicker` / `handleNextRandom` 事件处理器内，render 与 `useMemo` 未调用非确定性逻辑，避免 `react-hooks/purity` 告警。
- 单候选时“换一个”回退原池，避免死循环；当前默认数据 4 个候选，可正常换到不同结果。

## 运行时证据

- 截图：`%TEMP%\t006-evidence\01-open.png`、`02-next.png`、`03-detail.png`、`04-tag-filter.png`、`05-status-filter.png`、`06-empty.png`
- 日志：`%TEMP%\t006-evidence\log.txt`
- Playwright 断言：10 条（AC/逻辑），全部 PASS；AC5 首次因选择器写成 `.topic-drawer`（实际为 `.topic-detail-drawer`）误报，已用正确选择器复验通过。

## 超出范围发现

- 构建产物 chunk 959 kB > 500 kB 警告：工程优化项，非 T-006 验收范围。
- AntD 控制台告警：`[antd: Card] 'bordered' is deprecated. Please use 'variant' instead.` 与一次 404 资源请求，非阻断、不在 T-006 验收范围。
- 随机弹窗没有独立原型 PNG，本次按 README 交互说明与 PRD F-01-07 文案验收；弹窗标题“随机选题”、按钮“换一个”、空状态文案与 PRD/README 一致。

## 判定

- acceptanceCriteria：5/5 **PASS**
- technicalChecks：6/6 **PASS**
- 任务状态：`passed`