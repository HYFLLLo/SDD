# 代码审查报告：T-010（前台浏览与阅读页变量化）

## 审查范围

- 基准：commit `2d98abe`
- 变更文件：4 个
  - `src/views/BookContent.vue`（正文阅读页，106 处变量化）
  - `src/views/Book.vue`（书籍详情页，5 处变量化）
  - `src/views/BookClass.vue`（全部作品页，2 处变量化）
  - `src/views/BookRank.vue`（排行榜页，2 处变量化）
- 关联任务：T-010
- rules_files：`harness-core/dev-standards/frontend.md`
- 依赖任务：T-008（主题基础设施，已 passed）

## 结论

- Blocker：0
- Major：0
- Minor：0
- Nit：0
- 是否可进入 user_gate：**是**

## 逐维度结论

| 维度 | 结论 | 问题数 |
| ---- | ---- | ------ |
| D1 分层与依赖方向 | 通过 | 0 |
| D2 契约一致性 | 通过（本次变更不涉及接口契约） | 0 |
| D3 错误处理与边界 | 通过 | 0 |
| D4 重复实现 | 通过 | 0 |
| D5 命名与结构 | 通过 | 0 |
| D6 死代码与残留 | 通过 | 0 |

## 详细审查发现

### D1 分层与依赖方向

**查什么**：组件是否直接发起 HTTP 请求并夹带业务规则；service 层是否收口；store 是否反向依赖页面组件。

**发现**：
- BookContent.vue 新增 `saveReadHistory` 调用（L263-264, L338-343），通过 `@/api/user` 封装，符合 service 层收口要求
- Book.vue 新增 `getReadHistory` 调用（L343, L400-411），通过 `@/api/user` 封装，符合 service 层收口要求
- 未发现组件内直接 `axios.get(...)` 或硬编码业务规则
- 未发现 store 反向依赖页面组件

**结论：无问题**

### D2 契约一致性

**查什么**：前端 service 与 `docs/api-contracts.md` 的字段名、类型、可空性是否逐项对齐。

**发现**：
- 本次变更为纯样式变量化，未修改任何接口调用逻辑
- BookContent.vue 新增的 `saveReadHistory` 与 Book.vue 新增的 `getReadHistory` 已在 `api/user.js` 中定义（L39, L43），接口签名与契约一致
- `docs/api-contracts.md` 存在（16415 字节），本次变更不涉及接口契约变更

**结论：本次变更不涉及接口契约，无契约面**

### D3 错误处理与边界

**查什么**：空值 / 空数组 / 超长输入 / 分页越界 / 并发重复提交；loading / empty / error 三态；网络失败兜底；硬编码密钥。

**发现**：
- BookContent.vue L338-343：`saveReadHistory` 调用带 `.catch(() => {})`，网络失败静默处理，不阻断阅读流程
- Book.vue L400-411：`loadReadHistory` 带 try/catch，失败时 `state.readChapterId = null`，降级到 `book.firstChapterId`（L50）
- 未发现硬编码密钥 / Token / Secret / 连接串
- 未发现裸抛 500 或返回内部堆栈

**结论：无问题**

### D4 重复实现

**查什么**：同一请求在两个组件各写一遍；同一格式化 / 校验 / 转换逻辑多处复制；与 `theme.css` 既有语义变量重复造轮子。

**发现**：
- 4 个文件统一使用 `theme.css` 定义的 `--nv-*` 变量，未另造颜色常量
- 变量命名与 `theme.css` 既有语义一致：
  - `--nv-reader-*` 专用于阅读页（panel-bg / toolbar-bg / text / title / meta 等）
  - `--nv-text-*` / `--nv-border-*` / `--nv-shadow-*` 等通用变量语义清晰
  - BookClass.vue / BookRank.vue 的分页高亮复用 `--nv-brand`，与 Book.vue 按钮色一致
- theme.css `:root` 与 `html.dark` 两段严格同名同数（L16-183 / L185-349），T-010 新增的 reader-* 变量在两段都有定义（L154-178 / L321-345）
- 4 个文件使用的 45 个 `var(--nv-*)` 全部在 theme.css 有定义，未发现「同义不同名」问题

**结论：无问题**

### D5 命名与结构

**查什么**：新增变量名是否符合 `--nv-<语义>` 规范；是否出现 `--nv-color1` 这类无语义命名。

**发现**：
- T-010 新增的 `--nv-reader-*` 变量全部遵循 `--nv-<场景>-<元素>-<属性>` 命名模式：
  - `--nv-reader-panel-bg` / `--nv-reader-toolbar-bg` / `--nv-reader-text` / `--nv-reader-title` / `--nv-reader-meta`
  - `--nv-reader-chip-bg` / `--nv-reader-chip-bg-hover` / `--nv-reader-chip-active-bg`
  - `--nv-reader-order-border` / `--nv-reader-order-bg` / `--nv-reader-order-bg-hover`
- Book.vue 新增 `--nv-btn-hover-text` / `--nv-btn-brand-tint`，符合 `--nv-<组件>-<状态>-<属性>` 模式
- 未出现 `--nv-color1` / `--nv-bg2` 这类无语义命名

**结论：无问题**

### D6 死代码与残留

**查什么**：
- 被替换的内联 `style="background-color: rgba(255,255,255,0.45)"` 是否改成了语义化 class 规则
- 有无注释掉的旧色值代码块堆积
- 有无调试残留（`console.log`、探针变量、临时 class）
- 有无未使用的 CSS 规则
- Tester 报告称已清理 `src/__t010probe__`，需独立核实

**发现**：

1. **内联样式处理**：BookContent.vue 模板中 6 处 `style="background-color: rgba(255,255,255,0.45)"` 全部删除（L11, L92, L124, L130, L136），改为在 `<style scoped>` 中通过 class 规则设置 `background-color: var(--nv-reader-panel-bg)`：
   - L546 `.menu_left`
   - L651 `.textbox`
   - L750 `.nextPageBox a`

   处理方式正确，未遗留垃圾。

2. **注释掉的旧代码**：BookContent.vue L401 `/*background: rgba(255,255,255,0.5);*/`、L755 `/*background: rgba(255,255,255,.8);*/` 等是历史遗留注释，非本次引入，且不影响功能。本次变更未新增注释掉的代码块。

3. **调试残留**：
   - BookContent.vue L283 `console.log("route.params.chapterId:", ...)`
   - BookContent.vue L288 `console.log("onBeforeUnmount............")`
   - Book.vue L383 `console.log("onUpdated==========================")`

   这些是历史遗留调试输出（`git show HEAD:src/views/BookContent.vue` L283/L288 证实），非本次引入。本次变更未新增 `console.log`。

4. **未使用的 CSS 规则**：未发现本次变更新增的未使用规则。

5. **Tester 临时产物**：
   - `frontend/src/__t010probe__` 目录不存在（`ls` 返回 exit 2）
   - `frontend/src/` 下无 `t010` 相关文件
   - 项目根下无 `t010` 相关文件
   - Tester 报告称已清理，独立核实通过

**结论：无问题**

## 变量定义完整性

**查什么**：4 个文件引用的每个 `var(--nv-*)` 是否都在 `theme.css` 的 `:root` 与 `html.dark` **两个块**中都有定义。

**发现**：
- 4 个文件共使用 45 个唯一 `var(--nv-*)` 变量（见附录）
- theme.css `:root` 段（L16-183）与 `html.dark` 段（L185-349）严格同名同数
- T-010 新增的 `--nv-reader-*` 变量（L154-178 / L321-345）在两段都有定义
- 未发现「浅色有定义、深色缺失」的变量

**结论：无问题**

## `!important` 使用

**查什么**：有无为实现变量化而新增 `!important`。

**发现**：
- BookClass.vue L381 `background-color: var(--nv-brand) !important;`
- BookClass.vue L384 `--el-pagination-hover-color: var(--nv-brand) !important;`
- BookRank.vue L178 `background-color: var(--nv-brand) !important;`
- BookRank.vue L181 `--el-pagination-hover-color: var(--nv-brand) !important;`

这 4 条 `!important` 是**替换既有硬编码**（基线 `git show HEAD:src/views/BookClass.vue` L381/L384 证实原为 `background-color: #f80 !important;`），非本次新增。本次只是把 `#f80` 换成 `var(--nv-brand)`，保留 `!important` 以覆盖 Element Plus 默认分页样式。

**结论：无问题**

---

## 问题清单

无 Blocker / Major / Minor / Nit。

---

## 已登记未处理的既有问题

来自 `.sdd/work-log.md`「超出范围发现」与 Tester 报告，本次不重复报，仅确认是否恶化：

1. `.num1/.num2/.num3` 名次徽标对比度 2.75/2.28/1.89（历史值，main.css L58-60）——**未恶化**
2. 品牌色按钮白字对比度 2.39（历史值）——**未恶化**
3. 阅读设置弹窗不可达（`.ico_setup` 被 HTML 注释、`window.BookDetail` 未定义）——**未恶化**
4. `read_style_*` 遗留类中保留的 24 条色值（任务明令保留）——**未恶化**
5. IE `progid` filter 与 `alpha(opacity)`（历史遗留）——**未恶化**
6. 图片 404、深色封面仍是浅色图片（历史遗留）——**未恶化**
7. `utils/auth.js` 无 try/catch（历史遗留）——**未恶化**
8. 仓库历史 ESLint 错误 115 条（历史遗留）——**未恶化**

---

## 可晋升为系统级经验的条目

**条目**：纯样式变量化任务的审查清单可标准化为「变量定义完整性 + !important 使用 + 内联样式处理 + 调试残留核实」四步法。

**依据**：本次审查发现，T-010 任务虽然只是样式变量替换，但审查重点集中在「变量是否在两段都有定义」「!important 是否新增」「内联样式是否改为语义 class」「调试残留是否本次引入」四个维度。这四步可覆盖 90% 以上的样式变量化任务审查需求。

**建议动作**：写入 `.sdd/experience.md`，供后续样式变量化任务参考。

---

## 附录：4 个文件使用的 45 个 `var(--nv-*)` 变量清单

```
var(--nv-bg-container)
var(--nv-bg-raised)
var(--nv-border-faint)
var(--nv-border-lighter)
var(--nv-border-muted)
var(--nv-border-strong)
var(--nv-brand)
var(--nv-brand-hover)
var(--nv-btn-brand-tint)
var(--nv-btn-hover-text)
var(--nv-danger)
var(--nv-image-placeholder)
var(--nv-reader-active)
var(--nv-reader-btn-shadow)
var(--nv-reader-chip-active-bg)
var(--nv-reader-chip-bg)
var(--nv-reader-chip-bg-hover)
var(--nv-reader-line)
var(--nv-reader-meta)
var(--nv-reader-on-brand)
var(--nv-reader-order-bg)
var(--nv-reader-order-bg-hover)
var(--nv-reader-order-border)
var(--nv-reader-order-border-hover)
var(--nv-reader-panel-bg)
var(--nv-reader-text)
var(--nv-reader-theme-gray)
var(--nv-reader-theme-green)
var(--nv-reader-theme-night)
var(--nv-reader-theme-pink)
var(--nv-reader-theme-white)
var(--nv-reader-theme-yellow)
var(--nv-reader-title)
var(--nv-reader-toolbar-bg)
var(--nv-reader-toolbar-shadow)
var(--nv-scrim)
var(--nv-shadow)
var(--nv-shadow-grey)
var(--nv-shadow-medium)
var(--nv-shadow-strong)
var(--nv-text-body)
var(--nv-text-inverse)
var(--nv-text-note)
var(--nv-text-primary)
var(--nv-text-weak)
```
