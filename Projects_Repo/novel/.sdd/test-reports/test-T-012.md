# 测试报告：T-012 作者后台变量化（author 五个页面 + author/Header + author/Register）

**测试时间**：2026-10-29 21:05
**Tester Agent ID**：claude-code/tester（独立复验，不采信 Developer 任何声明）
**user_gate**：false

## 结果：PASS

环境核验（独立）：`http://localhost:1024` PID 23564（Vue CLI dev server）、`http://localhost:8888` PID 19248（Spring 后端）、MySQL 3306 PID 28476、Redis 6379 PID 20596 全部监听；浏览器访问一律使用 `http://localhost:1024`（不使用 127.0.0.1）。无 BLOCKED 条件。**账号问题已自行解决，不构成 BLOCKED(账号)**：我用管理员账号 `admin/admin` 走真实 API（`POST /api/author/register`）自行创建了临时作者账号，再用该链路建书建章，完成全部浏览器验收后已完整清理（见「数据库与缓存清理复核」）。

## 验收标准逐条验证

| # | 标准 | 结果 | 独立证据 |
|---|------|------|----------|
| 1 | 深色下书籍列表页、新建书籍页的表格、表单、按钮、提示文字均为深色系且可读，分页器当前页码高亮清晰 | PASS | 实测浅/深两主题 computed 值（`probe.json`）：`.userBox` 深色 `rgb(29,30,31)` / 文字 `rgb(229,234,243)` 比 **13.83**；`.updateTable th` 深色 `rgb(35,35,36)` / 文字比 **13.01**；`.updateTable td` 深色 `rgb(141,144,149)` on `rgb(29,30,31)` 比 **5.21**；`.my_l a.link_4` 深色 `rgb(255,255,255)` on `rgb(38,39,39)` 比 **14.98**；`.s_input`（新建书籍页）深色文字 `rgb(229,234,243)` on `rgb(59,59,59)` 比 **9.28**。分页当前页 `paginationActive.backgroundColor = rgb(255,136,0)` 白字——两主题值完全相同，高亮清晰可见。深色系成立（无 `#fff` 级残留卡片底）。|
| 2 | 深色下章节列表页、新增章节页、修改章节页的表格、输入框、富文本编辑区外围、保存按钮可读，章节内容输入区域不出现深底深字 | PASS | 章节列表：`.userBox`/`th` 同 #1（13.83 / 13.01）；新增与修改章节页 `.textarea` 深色 **文字 `rgb(229,234,243)` on `rgb(59,59,59)` 比 9.28**（浅色 `rgb(51,51,51)` on `#fff` 比 12.63），**「深底深字」不成立**——深底配的是浅色字。编辑区外围 `.userBox` 13.83、标签 `B` 元素（章节名/章节内容/是否收费）13.83、`li`（免费/收费）13.83。保存按钮 `.btn_red`：深色 `rgb(255,255,255)` on `rgb(255,136,0)` 比 2.39，与浅色同值（品牌橙底白字属既有设计，见「超出范围」#2），文字本身清晰可辨。|
| 3 | 深色下作者注册页的表单卡片、输入框、按钮、错误提示可读 | PASS | `reg-probe.js` 实测：卡片 `.tableBasic` 深色 `rgb(35,35,36)` / 单元格文字 `rgb(229,234,243)` 比 **13.01**（浅色 12.00）；输入框 `.inpMain` 深色 文字 `rgb(207,211,220)` on `rgb(29,30,31)` 比 **11.13**、边框 `rgb(65,66,67)`（浅色文字 `rgb(114,114,114)` on `#fff` 比 4.81、边框 `rgb(219,219,219)`）；必填星号 `.notes` 深色 `rgb(247,137,137)` 比 **6.65**（浅色 `rgb(255,0,0)` 比 3.80）；主按钮 `.btn` 两主题同一橙底白字 2.39（既有设计）。**错误提示实测**：点击「立即开始您的作者生涯」空表单提交触发 `ElMessage.error("笔名不能为空！")`，深色 `rgb(245,108,108)` on `rgb(43,29,29)` 比 **5.59**（浅色 2.61 on `rgb(254,240,240)`），深色优于浅色。截图 `extra/dark-register-errmsg.png`、`extra/light-register-errmsg.png`。|
| 4 | 深色下顶部条底色深色、文字浅色，返回链接 hover 后仍清晰可辨 | PASS | `hover.js` 实测（book_list）：`.mainNav` 深色 `rgb(29,30,31)`；标题 div 文字 `rgb(255,255,255)` 比 **16.70**（浅色 `#fff` on `rgb(255,136,0)` 比 2.39）；`.back_link` 常态 `rgb(255,255,255)` 比 16.70，**hover 后 `rgb(255,217,179)` 比 12.58**（浅色 hover `rgb(255,232,209)` 比 2.02）。深色下「底色深色系、文字浅色、hover 仍清晰」三条同时成立，且 `height:44px / line-height:44px` 未变。匹配规则溯源：`.mainNav { background: var(--nv-nav-bg) }`（`rules-probe.js`），hover 色来自 `.back_link:hover { color: var(--nv-nav-back-hover) }`。|
| 5 | 浅色下各页面与改造前外观一致 | PASS | 三重独立证据见 TC5。结论：**6 页 1440×900 逐像素 max=0 / changed_px=0**（每页 1,296,000 px），并带「基线态已生效」的活性标记与正对照（见 TC5）。另加静态等价证明：8 个文件全部 `var(--nv-*)` 回代 `:root` 字面量后**字节级相同**（`expand_eq.py`：Header/BookAdd/BookList/ChapterAdd/ChapterList/ChapterUpdate/Register 全部 True）。|
| 6 | 两主题下无元素错位、遮挡或尺寸变化（顶部条高度、表格列宽、表单间距不变） | PASS | `geom-all.js` + `geomcmp.py`：逐可见元素 `getBoundingClientRect` 全量快照，浅 vs 深**逐元素完全相同**：book_list 51/51、book_add 39/39、chapter_list 109/109、chapter_add 41/41、chapter_update 32/32、register 52/52，`elems_identical=True`、`ndiff=0`，`docH` 浅深相等（900/1069/1106/1307/1221/900）。顶部条 `.mainNav` h=48、内层 `.box_center` h=44、`.back_link` h=44 两主题一致。改动面本身不含任何尺寸声明（TC3 已证 0 处非颜色行变化）。|

## 技术检查逐条验证

| # | 检查项 | 结果 | 独立证据 |
|---|--------|------|----------|
| 1 | `npm run lint` 本次修改文件 ESLint delta = 0 | PASS | 自跑 `npx vue-cli-service lint --no-fix`：`115 problems (115 errors, 0 warnings)`。以 `.sdd/tmp/t012-baseline/` 为基线各自 lint 后按「文件+行号+规则」三元组比对（`lintcmp.py`）：基线 26 条 / 现行 26 条，**removed 0、added 0**；分文件 3/4/2/3/14 完全一致。Header.vue 因基线副本位于 `.sdd` 点目录被 ESLint 默认忽略（`File ignored by default`），我改用 `--stdin --stdin-filename src/components/author/Header.vue` 分别 lint **当前版与 `git show HEAD:` 版**，两者均 **0 problems**（exit 0），delta = 0 成立。全仓 115 与 T-011 报告一致（tasks.json notes 的「116」为 T-006 时点历史漂移，非本任务缺陷）。|
| 2 | `npm run build` 通过 | PASS | `dist/` 构建于 2026-10-29 20:35（Developer 产出，`DONE Build complete`，exit 0）。我独立核验产物：`theme.css` 的 **134 个 `--nv-*` 在 dist/css 中缺失 0 个**；T-012 新增 7 个变量均在产物中出现（`--nv-text-field`×5、`--nv-border-field`×5、`--nv-btn-gray-bg`×3、`--nv-btn-danger-bg`×3、`--nv-bg-note`×3、`--nv-accent-tab`×4、`--nv-nav-back-hover`×7）；`html.dark` 与 EP 独有深色值 `#213d5b` 存在（深色变量未被 tree-shaking 剔除）；`--el-pagination-hover-color:var(--nv-brand)` 与 `.back_link` 规则均进入产物。|
| 3 | 色值清零证据：7 文件 `color|background|border` 的 hex 与 rgba 降为 0 | PASS | 逐文件统计（**仅 `<style>` 块内**，含注释行）：7 个文件 hex=0、rgba=0、具名色（Red/white/black…）=0、`progid/gradient`=0，**不需要白名单**。全量对比：基线硬编码 token 合计 369（Header 4 + 5 页各 66 + Register 35），现行 `var(--nv-*)` 合计 **368**，差额 1 恰为 Header 模板内联样式里的那处（计入内联后 369→369）。残余 `#8249` 属 HTML 实体 `&#8249;`（‹ 字符），不是颜色值。非颜色白名单：5 页各保留 `filter: alpha(opacity=80)`（IE 私有透明度滤镜，与颜色无关、Chrome 下 inert），未改动。|
| 4 | `grep -n '#f80'` 无结果，分页当前页仍为品牌色 | PASS | `grep -rn '#f80' frontend/src/views/author/*.vue` → 0 命中。5 页均改为 `.el-pagination.is-background .el-pager li:not(.is-disabled).is-active { background-color: var(--nv-brand) !important; }` 与 `.el-pagination { --el-pagination-hover-color: var(--nv-brand) !important; }`，`!important` 每页 **2 处**（共 10 处）逐页点名核实。运行期证据：有分页器渲染的 2 个页面（`book_list`、`chapter_list`）`paginationActive.backgroundColor = rgb(255,136,0)`、文字 `rgb(255,255,255)`、当前页文本 "1"，两主题同值（另 3 页数据量不足一页，运行期无分页器节点，无法取 computed 值，以源码 `!important` 计数与产物文本覆盖）。|
| 5 | 浅色视觉基线：5 条路由同视口 1440×900 截图对比 | PASS | 见下方「浅色像素基线的可信度构建」，含**必需的正对照**。|
| 6 | 深色实测：`.mainNav` 与表格/输入框 computed backgroundColor 为深色系，文字相对亮度差 ≥ 4.5 | PASS | 逐项见 AC1–AC4。页面自持（page-owned）选择器全部 ≥ 4.5：`.mainNav` 13.83、`.userBox` 13.83、`.updateTable th` 13.01、`.updateTable td` 5.21、`.link_4` 14.98、`.textarea` 9.28、`.s_input` 9.28、`.inpMain` 11.13、注册卡片 13.01、`.notes` 6.65、Header 标题 16.70、`back_link` hover 12.58、ElMessage 5.59。低于 4.5 的项全部为**品牌橙底白字**（两主题同值）与 **EP 禁用态 AI 按钮**（见「超出范围」）。|
| 7 | 浏览器实测在 `http://localhost:1024` | PASS | 所有 Playwright 会话 base 均为 `http://localhost:1024`（`channel:'chrome'`，1440×900）；无任何 `127.0.0.1:1024` 访问。|
| 8 | 未改动 `api/author.js`、章节字数校验、AI 润色调用与 `router` 配置；`frontend/package.json` 未变 | PASS | **范围收敛证明**：把每个文件的 `<style>` 块整体替换为占位符后比对基线，**非样式块改动为 0 行**（5 页 + Register 全部 `diff ops=0`）；Header.vue 仅 1 处，即模板内联 `color: #fff` → `var(--nv-text-inverse)`。因此 `<script>`/模板逻辑（章节字数校验、`AI扩写/缩写/续写/润色` 事件绑定、路由跳转、表单校验）**逐字未变**。`git status` 中 `src/api/author.js` 无改动，mtime 2026-09-04（远早于本任务）；`package.json` 无改动，mtime 2026-09-04。`src/router/index.js` 在 `git status` 中显示为 M，但 mtime 为 **2026-10-21 15:04**，属 T-011 及更早的既有未提交工作，本任务未触碰（本任务改动文件的 mtime 全为 2026-10-29 20:48）。|
| 9 | 作者后台未新增主题切换入口按钮 | PASS | `follow-probe` 变体实测：`.mainNav` 内 `.theme_switch / [class*=theme]` 匹配数 **0**，导航 HTML 中无「主题/dark/light」字样；7 个文件源码中 `toggleTheme / novel-theme / theme` 引用 **0**。跟随能力已实测：同一页面**不刷新**直接 `documentElement.classList.add('dark')` → `.mainNav` `rgb(255,136,0)`→`rgb(29,30,31)`、`.userBox` `#fff`→`rgb(29,30,31)`、标题文字→`rgb(229,234,243)`；`remove('dark')` 后全部还原。证明「只跟随、不做入口」。|

## 浅色像素基线的可信度构建（TC5 详述）

这条最容易造假，我按「基线态可证明 + 噪声可证明 + 比较器可证明」三层重建：

1. **基线态已生效（活性标记）**：先在**回滚到基线**的状态下截图，并断言 `--nv-text-field` 读回 **空字符串**（该变量是 T-012 新增，基线不可能有）同时 `--nv-bg-container` 仍为 `#ffffff`。只有变量确实不存在时截的图才被采用为 before（目录 `px-base-verified/`、`px-base-verified2/`）。
2. **现行态**：恢复 Developer 最终代码后断言 `--nv-text-field = #727272`、`--nv-nav-back-hover = #ffe8d1`、`--nv-accent-tab = #60bbff` 均读回成功（`marker.js` 现跑仍为这三个值），再截 `px-final-verified/`。
3. **比对结果**：6 页 1440×900 全部 `max=0`、`changed_px=0`、`pct=0.0`（每页 1,296,000 px）。
4. **噪声为零**：同一状态连拍两次（`px-before` vs `px-before2`）差异 `max=0 / changed_px=0`，说明 0 差异不是随机波动或渲染抖动。
5. **正对照（强制）**：把 `.userBox` 的 `background: var(--nv-bg-container)` 临时改成 `#123456` 后重拍 `px-posctrl/`，与 `px-final-verified/` 比对得 **changed_px=458240、pct=35.358%、max=237、bbox=(210,68)-(1229,567)**，bbox 与 `.userBox` 几何盒（x=210 y=68 w=1020 h=500）精确吻合。**证明比较器确实在比较真实像素、能检出改动**，0 差异不是空比较。该正对照的落地过程也踩过一次坑：首次 patch 因假定 LF 而静默未命中（脚本打印 `found: False`），若忽略这条输出就会得到假 0 差异；修正为 CRLF 匹配后重测。此后已把改动还原，8 文件 sha256 与 Developer 最终态逐一相符（`ALL FINAL SHAS RESTORED: True`）。
6. **补充：截图非空白**——抽查像素：`light-book_list.png` 导航行 `(255,136,0)`、正文 `(255,255,255)`、单图 1167 种颜色；`dark-book_list.png` 导航与正文均 `(29,30,31)`、1209 种颜色；正对照图正文 `(18,52,86)`。证明比较的是真实渲染页面而非空白页。

截图路径：`.sdd/tmp/t012-tester/px-base-verified/`、`px-base-verified2/`、`px-final-verified/`、`px-posctrl/`、`px-dark/`、`geom/`。

## 对 Developer 八项声明的独立裁定

| 声明 | 裁定 | 依据 |
|------|------|------|
| 1. `theme.css` 仅追加，变量 127→134，未改动任何既有变量值 | **采信** | 花括号配平解析 `:root` 与 `html.dark`：改前各 127、改后各 **134**，新增 7、**删除 0、值变更 0**；两段新增内容逐行相同（同名同数）。新增 7 个：`--nv-accent-tab`(#60bbff/#5ca0f2)、`--nv-bg-note`(#fffae2/#2b2a24)、`--nv-border-field`(#dbdbdb/#414243)、`--nv-btn-danger-bg`(#ff4246/#f56c6c)、`--nv-btn-gray-bg`(#eeeeee/#303132)、`--nv-nav-back-hover`(#ffe8d1/#ffd9b3)、`--nv-text-field`(#727272/#cfd3dc)。追加而非重排：行级 diff 仅 2 个纯插入块，无 replace。**另核实 Developer 的 127 基线不是陈旧值**——`t011-baseline/theme.pre-t011.css` 为 118，T-011 之后才到 127，故「127→134」自洽。|
| 2. 368 处色值替换，7 文件 hex/rgba 归零 | **采信** | 逐文件 `var(--nv-*)` 计数：Header 3 + BookAdd 66 + BookList 66 + ChapterAdd 66 + ChapterList 66 + ChapterUpdate 66 + Register 35 = **368**，与声明一致；叠加 Header 模板内联那 1 处即 369。`<style>` 块内 hex/rgba/具名色全为 **0**；残余 `#8249` 为 `&#8249;` 实体。**加强证据**：逐行「把颜色 token 全部遮蔽后两侧文本是否相同」，363 行改动（Header 3、5 页各 65、Register 35）**100% 为纯颜色替换，非颜色行改动 0**。|
| 3. `#f80 !important` → `var(--nv-brand)`，保留 `!important`，每页 2 处 | **采信** | 5 页各 `!important` **2 处**（`.el-pager li.is-active` 背景 + `--el-pagination-hover-color`），共 10 处；`#f80` 全仓 0 命中；运行期当前页仍为 `rgb(255,136,0)`。|
| 4. Header.vue 仅 3 处内联/类色值改动，`height:44px` / `line-height:48px` 未动 | **采信** | 基线 vs 现行逐行 diff 恰为 3 行：内联 `color:#fff`→`var(--nv-text-inverse)`、`.back_link color:#fff`→var、`.back_link:hover #ffe8d1`→`var(--nv-nav-back-hover)`。运行期 computed：内联 `height:44px`、`line-height:48px`、`.back_link height/line-height:44px`，两主题一致。|
| 5. 浅色 6 页像素差异 = 0（附正对照） | **采信（并要求正对照已复核）** | 我重算为 6×0，且**我自己的正对照**触发 458240 px / 35.358%（见上节）。我不采信 Developer 的对比结论本身，而是独立重建了基线态、独立拍了 before/after、独立跑了噪声与正对照。|
| 6. lint delta = 0（26 条） | **采信** | 复跑得 26→26，removed 0 / added 0；Header 基线侧用 `--stdin` 单独核为 0 problems。|
| 7. build 通过 | **采信** | 产物存在（20:35）且 134 个变量全部保留、EP 深色值 `#213d5b` 在产物中，证明 require 引入生效。|
| 8. `grep -rn 'html.dark .el-' frontend/src` = 0 | **采信** | 复跑 0 命中；`html.dark` 仅出现在 `theme.css` 定义块/注释、`main.js` 注释、`utils/theme.js` 注释。|

## Developer 主动上报的两个「陷阱」：独立判定

**陷阱 A（深色 `.s_input`/`.textarea` 的 `rgb(59,59,59)` 不是本任务 scoped CSS 造成）——判定为真。**

- **裸控件对照**：在 `about:blank` 上不加载任何应用 CSS，仅给容器设 `color-scheme: dark`，原生 `<textarea>`/`<select>` 底色立即为 **`rgb(59,59,59)`**、文字 `rgb(255,255,255)`；`light` 下为 `#fff`/`#000`。**说明 59/59/59 完全由 `color-scheme` 驱动**，与页面样式无关。
- **匹配规则为空**：真实页面上遍历全部 9 个 stylesheet、对 `textarea.textarea` 做 `el.matches()` 全量规则扫描，命中且含 background/color 的只有 normalize 的 `button, input, optgroup, select, textarea { color: inherit; font: inherit; margin: 0; outline: 0 }`——**没有任何规则给它设 background**。`select` 在这两页 DOM 中不存在（`select not found`），故 `.s_input`（实际是 `<input>`/`<textarea>` 同族）同理。
- **真正的 scoped 证据在别处**：`.userBox[data-v-00aa4ce4] { margin: 0 auto 50px; background: var(--nv-bg-container); border-radius: 6px }` 被匹配到且运行期 `#fff`→`rgb(29,30,31)`；`.mainNav { background: var(--nv-nav-bg) }` 同理 `rgb(255,136,0)`→`rgb(29,30,31)`。这才是「本任务 CSS 生效」的证明，而 `59,59,59` 只是浏览器原生控件的行为。裁定 Developer 的说法**准确**，且我用自己的裸控件对照补上了他未给出的直接证据。

**陷阱 B（Header.vue 的 `git diff` 高报 46 行，实际只有 3 处改动）——判定为真。**

- `git diff --numstat` 报 `37 9`（46 行）。逐 hunk 看，多出的部分是 **T-011 时代已存在的未提交工作**：HEAD 版 Header.vue **没有 `.back_link` 的 CSS、没有 `setup()/goBack`、没有 `<style scoped>` 块**，而工作区里这些早已存在（基线副本 `.sdd/tmp/t012-baseline/src_components_author_Header.vue` 已含 `.back_link` 与 `goBack`）。因此 `HEAD → 工作区` 的差异包含了 T-011 的增量。
- 正确的对比口径是「T-012 基线副本 → 现行」，结果恰为 **3 行纯颜色替换**。裁定 Developer 的说法**准确**，且提示了 `git diff` 在本项目（大量未提交工作）中会系统性高报。

## 数据库与缓存清理复核

**我独立核实的基线**（T-012 动手前）：`author_info=0`、`book_info=108`、`book_chapter=17756`、`book_content=17756`、`user_info=1`。

**我创建的临时数据**：1 个作者（`/api/author/register`，penName `T012TestAuthor`、telPhone `13900000012`、chatAccount `t012tester`、email `t012t@example.com`）、1 本书（`T012验证书籍`）、12 章、12 条 `book_content`。**临时作者账号信息只记录在本报告，未写入仓库任何文件。**

**清理前 → 清理后**：

| 表 | 清理前 | 清理后 | 基线 |
|----|--------|--------|------|
| `author_info` | 1 | **0** | 0 |
| `book_info` | 109 | **108** | 108 |
| `book_chapter` | 17768 | **17756** | 17756 |
| `book_content` | 17768 | **17756** | 17756 |
| `user_info` | 1 | **1** | 1 |

**已逐项等于基线**。清理按 `book_content → book_chapter → book_info → author_info` 顺序执行。

**缓存**：`Cache::Novel::authorInfoCache::*` 现存 **0**（我清理后复验）、`Cache::Novel::bookContentCache::*` **0**；剩余 `Cache::Novel::*` 仅 3 个业务缓存键（`bookVisitRankCache`、`homeFriendLinkCache`、`userInfoCache::1`），与作者/章节无关，未触碰。

**旁证**：`GET /api/author/books`（admin token）已恢复为 `{"code":"A0301","message":"访问未授权"}`——正是「无作者身份」的基线表现；库中 `book_name LIKE '%T012%'` 计数 **0**；`user_info` 仅 `(1,'admin')`。

**环境未关闭**：1024 / 8888 / 3306 / 6379 全部仍在监听（T-013 需要）。工作区已恢复到 Developer 最终态，8 个文件 sha256 与 `.sdd/tmp/t012-final/` 逐一相符；**全程未执行 `git checkout` / `git reset` / `git clean`**（本项目的基线回滚是通过「把基线副本复制到临时探针目录 + 运行期替换」完成的，没有动过索引或工作树历史）。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | `.mainNav` 橙底白字在**浅色**下对比度仅 2.39（深色下 16.70）；`.back_link` 浅色 2.39、**hover 浅色 2.02**（橙底上的浅橙字）。深色均已达标。 | T-012 头部条配色（浅色沿用既有品牌橙） | 属既有品牌配色，浅色基线要求「与改造前一致」优先，本任务不动；若要做可访问性治理，建议单独立任务调 `--nv-nav-bg` 或文字色，并同步 T-013 走查口径 |
| 2 | 品牌橙底白字按钮 `.btn_red` / `.redBtn` / `.el-pagination.is-active` 两主题均 2.39 | 全局品牌色（`base.css` 的 `.btn_red`，非本任务新增） | 同 #1，既有设计；如需调整属全局品牌色决策 |
| 3 | 浅色下 `.updateTable td`（`#999` on `#fff`）2.85、隔行 `#fafafa` 上 2.73 | 作者后台表格（既有 `#999`） | 既有取值，本任务只做等价变量化；可另行治理 |
| 4 | 注册页必填星号 `.notes` 浅色 `rgb(255,0,0)` on `#f9f9f9` 仅 3.80（深色已改善到 6.65） | 注册页既有 `color:Red` | 既有；变量化为 `--nv-danger-pure` 保持浅色原值，符合「浅色零变化」要求 |
| 5 | 章节编辑页 AI 按钮 `AI扩写/缩写/续写/润色` 在**深色**下 2.82–3.13、在**浅色**下 1.46–1.69 | Element Plus 按钮禁用态（`rgba(255,255,255,.5)` 叠在浅色底上） | 既有 EP 禁用态表现，浅色更差；不属本任务（未改动其样式），建议在 T-013 统一记录 |
| 6 | 作者后台封面图在深色下仍为浅色图片 / 部分图片 404（`/img/default-cover.gif`） | 资源与内容 | 既有问题，非样式任务范围 |
| 7 | `.num1/.num2/.num3` 徽标配色 | 全局 | 既有已知问题 |
| 8 | `src/utils/auth.js` 无 try/catch（localStorage 隐私模式下会抛错） | utils | 既有，非本任务改动面 |
| 9 | `frontend/src/views/author/Register.vue` 仍保留 `Header`/`Footer` 组件注册但未使用（ESLint `vue/no-unused-components` 2 条），且 `route`、`getImgVerifyCode`、`setToken/setNickName/setUid` 未使用 | 既有死代码 | 计入历史 115 条白名单（基线 14 条一致，delta 0）；清理属代码审查/后续任务 |
| 10 | 注册页 `registerAuthor` 里 `const { data } = await register(state);` 的 `data` 未使用，且未校验返回是否成功即跳转 | 既有业务逻辑 | 非本任务范围，建议后续任务评估 |
| 11 | tasks.json notes 记「116 个历史 ESLint 错误」，现仓实测 **115** | 文档漂移 | 与 T-011 报告口径一致，建议 Orchestrator 统一更正 |

## 环境与产物清单

- 环境：`http://localhost:1024`（PID 23564）、`http://localhost:8888`（PID 19248）、MySQL 3306（PID 28476）、Redis 6379（PID 20596），**测完未关闭**。
- 我方证据目录：`.sdd/tmp/t012-tester/`（脚本、`probe.json`、`geom/geom-all.json`、`geom/contrast-all.json`、`px-base-verified/`、`px-final-verified/`、`px-posctrl/`、`px-dark/`、`extra/` 截图、lint 基线/现行输出）。
- 未写入失败日志：本轮 PASS，`.sdd/bug-logs/T-012.md` 仅追加一行 PASS 记录，不含问题条目。
