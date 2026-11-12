# T-007 测试报告

## 结论

**PASS**

## 验证范围

- 看板状态拖动 + 列表快捷菜单改状态。
- 验证依据：`.sdd/tasks.json` T-007、`docs/PRD.md`、`docs/Plan.md`、`docs/api-contracts.md`、`docs/prototypes/01-选题库主页.png`、`docs/prototypes/README.md`、项目级 `.sdd/experience.md`、系统级 `memory/harness-experience.md`。
- 环境：Node v24.14.0，npm 11.9.0，Chromium/Edge 真实浏览器验证，dev server 端口 5199。

## 逐项验收

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 看板按“待验证、创作中、已发布、已放弃”四列分组 | PASS | `TopicKanban.tsx` 中 `statusColumns` 固定为该顺序；浏览器实测列标题顺序一致，四列数量为 4。 |
| 拖动卡片到新状态列，状态标识立即更新，刷新后保持 | PASS | 将“一条视频如何拆成五个平台版本”从“待验证”拖到“已发布”；拖动后落列成功，刷新后仍位于“已发布”，卡片状态徽标为“已发布”。 |
| 列表卡片快捷菜单修改状态，状态标识立即更新，看板分组正确 | PASS | 将“新手做小红书的第一周踩坑”的状态下拉改为“创作中”；列表状态徽标立即变为“创作中”，切换看板后位于“创作中”列。 |
| 状态修改后，状态筛选正确 | PASS | 修改后选择状态筛选“已发布”，仅显示已改为已发布的选题；原“创作中”选题不再显示（实测目标 1、干扰项 0）。 |
| npm run type-check | PASS | 实际执行通过，无 TypeScript 错误。 |
| npm run lint | PASS | 实际执行通过，无 ESLint 错误。 |
| npm run build | PASS | 实际执行通过，Vite 完成生产构建；仅输出 chunk 大小提示，属范围外发现。 |
| 固定高度容器 20% 缓冲 | PASS | 看板卡片固定 288px；真实浏览器实测卡片内容（含子块间距）约 174px，内容/容器 = 0.604，小于 0.85 且满足 ≥1.2 倍缓冲。 |
| 1280 / 1440 / 1920 布局与滚动 | PASS | 三档宽度下均为四列、列顶一致、列高一致（640px）；列内 `overflow-y:auto`，整页 `scrollHeight=900` 等于视口高度。悬停列体滚动后 `bodyScrollTop=21`、`windowScrollY=0`，列内滚动不带动整页。 |
| 5199 端口短时启动验证 | PASS | 验证前端口无监听；`npm run dev -- --host 127.0.0.1 --port 5199` 启动成功并显示 `http://127.0.0.1:5199/`；验证完成后已终止该进程并复查端口无监听。 |
| 高保真原型文案/布局/配色对齐 | PASS | 与 `01-选题库主页.png` 比对：顶部应用名、搜索占位、列表/看板切换、快速记录、随机选题、标签管理、四状态列、暖纸色卡片与列背景、状态徽标和标签 chip 均保持一致；新增状态快捷菜单仅以现有状态徽标为触发器呈现，未引入原型外的新文案或布局元素。 |

## 技术检查

- 状态修改复用 `HomePage` 的 `handleStatusChange`，构造完整 `TopicDraft` 并调用 store 的 `updateTopic`，再经 service/persistence 层写入 localStorage；组件不直接写 localStorage。
- 看板卡片 wrapper `draggable`，drop 后调用统一状态回调；`kanban-card` 设置 `flex: 0 0 auto`，避免固定高度卡片被 flex 压缩。
- 列表状态徽标用 `Dropdown` 包裹，外层 `stopPropagation`，避免打开快捷菜单时误触详情抽屉。
- 未发现硬编码密钥、TODO/FIXME/HACK、敏感信息泄露或接口契约绕过。

## 超出范围发现

- 生产构建提示主 chunk 超过 500KB。该提示不属于 T-007 验收或技术检查范围，不影响本次结论。

## 验证时间

2026-10-20
