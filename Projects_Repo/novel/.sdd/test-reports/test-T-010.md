# 测试报告：T-010 前台浏览与阅读页变量化

**测试时间**：2026-10-29 14:15–16:10（Asia/Shanghai）
**Tester Agent ID**：tester（SDD Harness V7.1）
**验证方式**：独立重写注释感知/块级分类色值扫描 + `git show HEAD:` 原文取回 + `@vue/compiler-sfc` 编译 HEAD/现行样式 + 浏览器运行期原地替换 `<style>` 做浅色基线（含阳性对照与活性探针）+ 真实 Chrome（Playwright `channel='chrome'`）在 `http://localhost:1024` 实测深浅两主题
**独立复验脚本**（本次全部自行编写，未执行 Developer 的任何脚本；共 57 个 `.js` + 16 个 `.py`）：
`.sdd/tmp/t010-tester-scan/`（含 `reconcile.py`、`varequiv.py`、`compile.js`、`baseline9.js`、`pixdiff9.py`、`probe.js`、`whitemask2.js`、`homeac1.js`、`readac4.js`、`setupbox.js`、`cover.js`、`progid.js`、`disputeA.js`、`ranks_rt.js`、`readstyle_verify.py`、`lintparse.py`、`lintdelta2.py`）
**证据产物**（298 个文件，其中 257 张截图）：`.sdd/tmp/t010-tester-evidence/`

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 独立证据 |
|---|------|------|---------|
| 1 | 深色下首页（推荐位、三档排行榜区块、最新新闻、友情链接）底色/文字/卡片边框均为深色系，无「深底深字」「浅底浅字」 | **PASS** | 真实点击 `.theme_switch` 后 `html.className='dark'`、`localStorage['novel-theme']='dark'`；刷新后保持 `dark`（持久化无闪烁）。首页 8 个推荐/排行榜挂件中 4 个外层 `channelWrap` 的 computed `background-color` 为 `rgb(29,30,31)`（lum 0.0129），另外 4 个内层 `rightBox` 为 `rgba(0,0,0,0)`（alpha 合成后由祖先 `rgb(29,30,31)` 承接，最终 painted 背景同为深色系）。对比度（alpha 合成后）：本周强推标题 13.83、榜单条目 13.83、书名 13.83、最新更新表 5.21、表头 6.14、表格单元格 5.21、最新新闻条目 13.83、分类标签 6.14、友情链接 15.26/15.26/15.26。**无任一条目 < 4.5**，无深底深字。白蒙层扫描：深色 **0 处**，同页浅色 **126 处**（阳性对照）。证据：`v12-home-ac1.json`、`v13-rank-rt.json`、`v10-whitemask.json`、`v12-home-ac1-{light,dark}.png` |
| 2 | 深色下全部作品页与排行榜页的列表/筛选条/分页文字可读，当前选中项高亮清晰可辨 | **PASS** | 全部作品：筛选标签 5.21、选中标签 6.31、未选中标签 13.83、表格头 5.78、单元格 5.21、书名链接 6.14、分页区域文字 13.83、非当前页码 8.80、翻页按钮 4.68 —— 全部 ≥ 4.5。排行榜：选中榜 tab 6.31、未选中 13.83、单元格 5.21、类别链接 6.14、表头 5.78。**选中项可辨**：分页当前页 `白字/rgb(255,136,0)` vs 其他页 `rgb(207,211,220)/rgb(48,48,48)`（深浅主题均 DIFF）；筛选标签选中 `rgb(255,120,0)` vs 未选中 `rgb(229,234,243)`（DIFF）；榜 tab 同理。浅色对应值 2.66（选中）/2.85（单元格）→ 深色 6.31/5.21，深色**优于**浅色。证据：`v11-ac-probe.json`（`bookclass-pager/*`、`book_rank-tabs/*`）、`v4-ac-probe.json`（`bookclass-filter/*`、`book_rank-filter/*`）、`v11-bookclass-pager-{light,dark}.png`、`v11-book_rank-tabs-{light,dark}.png` |
| 3 | 深色下书籍详情页封面占位/简介/章节入口/评分评论入口可读，封面与文字不粘连 | **PASS** | 封面占位 12.41（`fg rgb(229,234,243)` on `bg rgb(38,39,39)`，`--nv-image-placeholder` 深色 `#262727`）；简介 13.83；章节目录入口 13.83；全部目录 13.83；评论入口 13.83。**不粘连**：`getBoundingClientRect` 实测封面右缘 x=430（230+200）、`.book_info` 左缘 x=455 → **间距 25px**；封面 `box-shadow` 深色 `rgba(0,0,0,0.8) 0 1px 6px, rgb(42,39,36) 0 0 5px inset`，与页面 `rgb(20,20,20)` 有明确分离；浅色/深色 rect **逐项相同**（封面 200×271、图片 200×267、info 755×249、wrap 980×271）。证据：`v11-ac-probe.json`（`book_detail-ac3/*`）、`v4-ac-probe.json`、`v15-cover.json`、`v11-book_detail-ac3-{light,dark}.png` |
| 4 | 深色下阅读页正文底色深/文字浅，工具栏、目录/设置入口、上下章按钮同为深色系且可读，无白色或半透明白色蒙层残留 | **PASS（口径裁定见 A 段）** | 正文容器 `#showReading` 11.26（`rgb(207,211,220)` on `rgb(28,29,30)`）；正文段落/`.textbox` 面板同为 11.26；章节标题 13.98；章节元信息 6.93；`.menu_left` 工具栏 13.98；工具栏文字 6.93；`.menu_right` 文字 5.75；顶部工具栏 14.06；上一章/目录/下一章按钮均 13.98；阅读设置入口 6.31；页面 `body` 底色 `rgb(20,20,20)`。**白蒙层扫描深色 0 处**（同页浅色阳性对照 33 处）。蒙层来源已变量化：`--nv-reader-panel-bg` 浅 `rgba(255,255,255,0.45)` / 深 `rgba(29,30,31,0.9)`，模板内联蒙层 0 处。证据：`v12-read-ac4.json`、`v11-ac-probe.json`（`read-ac4/*`）、`v10-whitemask.json`、`v11-read-ac4-{light,dark}.png` |
| 5 | 深色下章节目录页与新闻详情页标题/正文/时间可读 | **PASS** | 目录页：标题 13.01、章节链接 13.83、书名 13.83、作者等元信息 5.21、VIP 标记 6.31。新闻页：标题 13.83、正文 13.83、来源 5.21、时间 5.21。均 ≥ 4.5；浅色对应 12.00/12.63/2.85，深色不低于浅色。证据：`v4-ac-probe.json`（`chapter_list-ac5/*`、`news-ac5/*`） |
| 6 | 切回浅色后与改造前浅色外观一致（颜色/边框/阴影无可感知差异） | **PASS（7/8 路由 0 像素差异，news 仅 1 像素抗锯齿）** | `git show HEAD:` 取 4 个 `.vue` 原文 → `@vue/compiler-sfc` 编译为 HEAD CSS；运行期原地替换已加载的同名 `<style>`（保持级联位置），并把 5 条 HEAD 内联蒙层逐个还原（read 路由 `injected:5`）；`theme.css` 按「删除 T-010 新增的 25 个变量」独立重建为 pre-T010 版本（重建结果与 Developer 快照 `:root` 93/93、`html.dark` 93/93 声明**顺序与取值完全一致**）。8 条路由 1440×900 逐像素比对：**home / bookclass / book_rank / book_detail / read / chapter_list / feadback 全部 `px=0 / maxdiff=0 / mean=0.0000`**；`base vs base2`、`cur vs cur2`、`cur vs cur3` 在全部路由上均为 0（无动态噪声）。**阳性对照全部触发**：home 463216 px、bookclass 399932、book_rank 505757、book_detail 205594、read 503570、chapter_list 136005、news 345465、feadback 288857，且每条路由都记录了替换前后 computed style 的真实翻转（如 home `.mainNav` `rgb(51,51,51)/rgb(255,136,0)` → `rgb(0,200,255)/rgb(255,0,0)`）—— 证明比对管线能测出差异，「0 差异」不是空转。**活性探针**：向 `theme.css` 追加 `--nv-probe-liveness: rgb(1,2,3)` 后 `getComputedStyle(document.documentElement)` 读回 `rgb(1,2,3)`，同时 `--nv-reader-panel-bg` 由 `rgba(255,255,255,0.45)` 变为空（HEAD 无该变量）→ 证明替换目标确实是生效的样式表而不是未被使用的副本。截图：`v9-{route}-{cur,cur2,cur3,ctl,base,base2}.png`。**唯一 1 像素差（news）已定位为抗锯齿**：位于面包屑 `span` 字符边缘 (413,174)，该元素及其祖先在替换前后 computed color/bg/fontSize/rect/opacity/fontFamily **全部逐项相同**，仅绿通道差 1（`[119,167,158]` vs `[119,166,158]`），且 `cur vs cur2`、`base vs base2` 均为 0 → 属渲染噪声，在「抗锯齿级」容许范围内 |
| 7 | 两种主题下无元素被遮挡、错位或宽度变化（只变颜色不变布局） | **PASS** | 全量 `getBoundingClientRect` + 排版/盒模型指纹（x/y/w/h + fontSize/fontWeight/lineHeight + padding/margin 四边 + display/position/borderWidth/borderRadius/overflow/textAlign/whiteSpace/letterSpacing/float/flexDirection/zIndex）light vs dark：**8 条路由 diff = 0**，节点数相同（home 738、bookclass 230、book_rank 419、book_detail 121、read 199、chapter_list 305、news 68、feadback 54），`docH` 完全相同（4134/1395/2543/1428/5369/1207/1671/900）。同主题连拍噪声基线 `noise=0`（已排除后端随机推荐子树 `.tj_bar/#recBookList/.book_intro/.relateBook/.wrap_right_cont` 与主题图标 `path`）。证据：`v6-layout.json` |

## technicalChecks 逐条验证

| # | 检查项 | 结果 | 独立证据 |
|---|--------|------|---------|
| 1 | `npm run lint`：本次修改文件 ESLint delta = 0 | **PASS** | 自行全量 `npx vue-cli-service lint --no-fix`：**115 errors / 0 warnings**（27 个文件），与 T-008/T-009 实测基线 115 一致；`tasks.json` 旧 notes 里的「116」是历史口径。对 4 个被改文件，把 HEAD 原文复制到 `src/__t010probe__/` 下单独 lint（该临时目录已清理）再与现行版本对比错误集：**逐条同文案、同规则、同条数**（Book 17、BookClass 3、BookContent 3、BookRank 3，合计 26），仅行号因插入变量而平移 → **delta = 0**。证据：`t010-lint-after2.txt`、`t010-lint-head.txt`、`lintparse.py` / `lintdelta2.py` 输出 |
| 2 | `npm run build` 通过 | **PASS** | `npm run build` exit=0，`DONE Build complete.`，Hash `cc741ec29407a149`，44449 ms，无 error/failed，仅有既有 chunk 体积列表。产物校验（不止 grep `html.dark`）：`dist/css/app.4596e7b7.css` 内 `html.dark` 块含 **118 个 `--nv-*` 定义**（与 `:root` 118 个集合相等），其中 `--nv-reader-*` 23 个变量各出现 2 次（root+dark）；Element Plus 深色用**独有值**校验通过 —— `chunk-vendors.ee4b1701.css` 的 `html.dark` 块（69 个变量）含 `--el-color-primary-light-7:#213d5b`、`-light-8:#1d3043`、`-light-9:#18222c`、`-dark-2:#66b1ff`、`--el-bg-color-page:#0a0a0a`、`--el-bg-color:#141414`、`--el-border-color-light:#414243`、`--el-fill-color-blank:transparent`，与 `node_modules/element-plus/theme-chalk/dark/css-vars.css` 源值逐一吻合。证据：`t010-build.log` |
| 3 | 涉及 `.vue` 文件 `color\|background\|border` 声明中十六进制与 rgba 降为 0，白名单逐条列明 | **PASS（白名单 29 条声明行，全部为任务强制保留项）** | 注释剥离 + 块级选择器感知扫描：`Book.vue` / `BookClass.vue` / `BookRank.vue` **有效色值 = 0**。`BookContent.vue` 剩 34 个色值 token 分布在 **29 条声明行**上，**全部落在白名单**：① **24 条**位于 `.read_style_1..6` 遗留规则内（任务明令「不得删除/改写/改值」），已用回溯所属选择器的脚本逐条确认这 24 条**无一例外**都在含 `read_style` 的选择器下；② **5 条**为 `filter: progid:DXImageTransform.Microsoft.gradient(...)` 的 IE 私有滤镜参数（`startColorstr/endColorstr`），已用脚本逐条确认 `prop == 'filter'`，并在 Chrome 实测为 **inert**（`.topMain` computed `filter:none`、`backgroundImage:none`；合成 `progid:` 元素 computed `filter:none`、`style` 属性被丢弃）。**非遗留、非 filter 的存活色值 = 0**（已用「回溯所属选择器」脚本逐条确认：现行 BookContent 的 24 条非 progid 色值声明**全部**位于含 `read_style` 的选择器内，0 条在普通选择器内）。另扫描 CSS 命名色：按**声明值**位置统计，现行 `BookContent.vue` 命名色 = **0**（HEAD 为 1 处，即已变量化为 `var(--nv-scrim)` 的 `background: black`）；按全文 token 统计的 12 处全在**选择器**里（`.readTheme .white/.green/.pink/.yellow/.gray`、`.order_zj .price .red`、`.order_allzj .red` 等类名），不构成色值 |
| 4 | `grep -n 'background-color: rgba(255' frontend/src/views/BookContent.vue` 无结果 | **PASS（按意图降级验证，口径变更已独立裁定，见 A 段）** | 原口径实际命中 **4 行**（L466 `.read_style_1 .textbox/.read_menu li a/.haveRead/.nextPageBox a` 组、L484 `.read_style_4 + .read_style_5` 组、L490 `.read_style_6` 组的 `background-color: rgba(255,…)`，以及 L502-503 `.read_style_5 .orderBox` 组的 `rgba(255,255,255,0.75)`），**全部位于 `.read_style_*` 遗留规则内**——而任务 notes 同时明令该类规则「不得删除」。**内联属性口径** `grep -n 'style="background-color: rgba(255'` = **0 命中**（rc=1）。HEAD 原文含 5 条内联蒙层（L11/93/124/131/138），且 `grep -c 'background-color: rgba(255'` 在 HEAD 为 **9**（5 条内联 + 4 条 CSS 遗留），现行降到 **4**（全部为遗留）。裁定理由与运行期不可达证明见 A 段 |
| 5 | 浅色视觉基线：5 条指定路由 1440×900 截图对比，差异仅抗锯齿级，截图路径附报告 | **PASS（5 条指定路由全部 0 像素差异，另附 3 条路由）** | `/home`、`/bookclass`、`/book_rank`、`/book/1334318182169681920`、`/book/1334318182169681920/1334318184854036480` 逐像素 **px=0**；另附 `/chapter_list`、`/news`、`/feadback` 亦为 0（news 有 1 px 抗锯齿，已定位说明）。基线构建含阳性对照与活性探针（见 AC6）。截图路径：<br>`.sdd/tmp/t010-tester-evidence/v9-home-{cur,base,base2,ctl}.png`<br>`v9-bookclass-{cur,base,ctl}.png`<br>`v9-book_rank-{cur,base,ctl}.png`<br>`v9-book_detail-{cur,base,ctl}.png`<br>`v9-read-{cur,base,ctl}.png`<br>`v9-chapter_list-*`、`v9-news-*`、`v9-feadback-*`<br>对照 JSON：`v9-pixdiff.json`、`v9-swap-report.json`；活性证据：`v7-diag.json` 的 `themeLiveness` 字段（`probe: "rgb(1,2,3)"`、`beforeReaderVar: "rgba(255, 255, 255, 0.45)"`、`afterReaderVar: ""`） |
| 6 | 深色可读性量化：读取 computed color/backgroundColor，正文区亮度差 ≥ 4.5，给出数值 | **PASS** | 用自写 `probe.js`：`parse` → 沿祖先链 **alpha 合成**出实际 painted 背景 → WCAG 相对亮度 → 对比度。**正文区 `#showReading` = 11.26**（`rgb(207,211,220)` on `rgb(28,29,30)`），正文段落 11.26，正文标题 13.98；工具栏 14.06 / 13.98 / 6.93；上下章按钮 13.98/13.98/13.98；列表卡片 5.21~13.83。**全部 ≥ 4.5**，无一例外（详见 AC1–AC5）。证据：`v12-read-ac4.json`、`v12-home-ac1.json`、`v11-ac-probe.json`、`v4-ac-probe.json` |
| 7 | 深色实测在 `http://localhost:1024`（不用 127.0.0.1） | **PASS** | 本轮全部脚本 `BASE = 'http://localhost:1024'`，对 `.sdd/tmp/t010-tester-scan/*.js` 执行 `grep -l '127.0.0.1'` 命中文件数 = **0**（`localhost:1024` 出现在 50 个脚本里）。服务端实测：1024 由 PID 24836 监听（拉起的 `app.js` 含 `nv-reader-panel-bg` ×4、内联 `background-color: rgba(255,255,255,0.45)` ×0 → 服务的是当前代码） |
| 8 | 未修改 `read_style_*` CSS 规则集合（diff 证明未删/未改写），未新增阅读主题切换逻辑 | **PASS** | 自行写脚本做**深度感知**的顶层规则切分（`git show HEAD:` 原文 vs 现行）：`read_style_*` 顶层规则块 **23 个 / 两侧一致**（含 `read_style` 的选择器共 94 个，因多组逗号选择器共用块体）；选择器序列、出现顺序、块体（空白归一后）**完全相同**，两侧 sha256 均 `7b539151d080de2e5c35be573b8e648031f618de41fdccac960278b021f060aa`（逐选择器展开后为 `97f139803e92024f6e3655fa3b64b749389b9278713371495caa2e0839f08b4a`）。`read_style` 在 CSS 内出现 100 次（94 次在选择器、6 次在注释），模板 **0** 次、`<script>` **0** 次、全仓库其他文件 **0** 次。未新增切换逻辑：`BookDetail.*` 的 onclick 全部沿用 HEAD 原样，`utils/theme.js` mtime 10-29 09:46（T-008）且不含 read_style 写入 |
| 9 | 未改动 `router/index.js`、`api/**`、`utils/**` 及任何业务判断逻辑 | **PASS（附范围外说明）** | **T-010 自身的修改窗口 10-29 12:54–13:36 内只有 5 个文件**：`theme.css`(12:54)、`BookContent.vue`(12:59)、`Book.vue`(13:00)、`BookClass.vue`(13:36)、`BookRank.vue`(13:36)，**不含** `router/api/utils`。这些目录/文件的 mtime 均早于 T-010 开工：`router/index.js` 10-21 15:04、`api/user.js` 10-21 14:14、`api/book.js` 10-20 15:21、`api/resource.js` 10-21 14:32、`utils/auth.js` 10-20 16:55、`utils/index.js` 10-20 16:56、`utils/theme.js` 10-29 09:46、`main.js` 10-29 10:01、`main.css`/`base.css` 10-29 11:58、`components/common/Top.vue` 10-29 09:48、`Navbar.vue` 10-21 15:04。进一步用 Developer 的 pre-T010 快照做差分并逐条归类：`BookContent.vue` 快照→现行 `+67/-69`，**67 条新增全部是颜色类声明**（`color`/`background`/`background-color`/`border*`/`border-color`/`box-shadow`/`--el-*色变量`），**0 条**落在 width/height/padding/margin/font-size/flex/display/position 等尺寸与布局属性上；69 条删除中 **68 条含字面色值**，唯一例外是 `background: black;`（即已变量化为 `var(--nv-scrim)` 的那条）。`Book.vue` `+6/-6`、`BookClass.vue` `+2/-2`、`BookRank.vue` `+2/-2` 同样 100% 为颜色声明。即 T-010 在这四个文件里**只加/改了颜色声明**；业务代码（阅读历史 `getReadHistory`、续读 `readChapterId`）在快照中已存在，非本任务引入。范围外的未提交改动见「超出范围发现」 |

## A / B / C 三点裁定

### A. 内联蒙层 TC 口径变更（`grep 'background-color: rgba(255'` → `grep 'style="background-color: rgba(255'`）

**裁定：口径变更合理，TC4 判 PASS，但保留「字面口径不可达」标注，建议 Orchestrator 改词。**

事实（全部独立取得）：

1. HEAD 原文内联蒙层确为 **5 条**，且都在**活模板**中（L10-12 `<div class="menu_left">`、L92-94 `<div class="textbox cf">`、L123-125 `<a class="prev">`、L130-132 `<a class="dir">`、L137-139 `<a class="next">`），现行模板 **0 条**。Developer 的「实为 5 行不是 6」正确。
2. 原口径残留 4 行命中（L466 `.read_style_1 …`、L484 `.read_style_4/.read_style_5 …`、L490 `.read_style_6 …`、L503 `.read_style_5 .orderBox` 组）**全部位于 `.read_style_*` 遗留规则内**，而非内联样式。任务 notes 同时要求「`read_style_1..6` … 不得删除/改写/改值」，因此**原口径与 read_style 保留要求互相冲突，字面意义上不可达**。
3. **这些遗留规则在运行期确实永远不会生效**（这是判定「合理」的关键，已多路证明）：
   - 静态：`read_style` 在 `BookContent.vue` 的 CSS 中共出现 100 次，其中 **94 次在选择器内、6 次在注释内**，模板 **0** 次、`<script>` **0** 次；全仓库（`src/` + `public/`）除该文件外 **0** 次；无 `:class`/`class="...read_style..."`/`classList`/`className`/`addClass` 引用。
   - 唯一可能施加该类的入口是原生脚本 `BookDetail.SetBackUpColor(n)`（onclick 属性），但 **`window.BookDetail` 在整个 bundle 中未定义**：运行时 `typeof window.BookDetail === 'undefined'`，`window.BookDetail.SetBackUpColor(1)` 抛 `Cannot read properties of undefined`；`public/` 下无任何 `.js`。
   - 这些 onclick 所在的阅读设置弹窗 `.setupBox` 虽在 DOM 中（`display:none`），但打开它的入口 `.ico_setup` 位于 **HTML 注释块 L33–L63 内**（HEAD 与现行一致；运行时 `.ico_setup` 计数为 0），且 `.maskBox` 在 DOM 中**根本不存在**（运行时计数 0，仅 CSS 有该规则）→ 弹窗无任何可达路径。
   - 运行时实测 8 条路由（含滚动到底后）`document.querySelectorAll('[class*="read_style"]')` 均为 `[]`，`body.className` 为空，`html.className='dark'`。
4. 因此「深色 + read_style_1 的半透明白蒙层」是一个**不可能发生的组合**（该组合需要阅读主题切换器，而 PRD 7.6 明确它是 T-013 范围且本任务禁止新增），**不构成 T-010 的真实深色可读性缺陷**；改判后的口径（内联属性）恰好对应本任务真正要修的缺陷，且已清零。
5. 深色下白蒙层扫描在 8 条路由全部 **0 处**（同页浅色 28–126 处为阳性对照），且 `--nv-reader-panel-bg` 深色值 `rgba(29,30,31,0.9)` 已把 3 处面板底色改为深色系 —— 缺陷本身已修好。

**遗留标注（供 Orchestrator 决定，不影响本轮判定）**：TC4 若按字面执行将永远无法通过（与 read_style 保留要求冲突），建议把措辞改为

> 内联样式证据：`grep -n 'style="background-color: rgba(255' frontend/src/views/BookContent.vue` 无结果；`.read_style_*` 遗留规则内的同类字面值按任务要求保留，不计入缺陷。

### B. 「106 处」与 Developer 实测「88 处」的对账

**裁定：实质结论（清零）成立，但 Developer 的算术口径有偏差；我的独立计数为 116（非 120/118），并且「2 处跨行」不成立。**

对 `BookContent.vue` 做注释感知 + 块级分类（HEAD 原文）：

| 分类 | HEAD | 现行 | 说明 |
|---|---|---|---|
| 文件全量 token（`#hex` + `rgb/rgba`） | **116** | 48 | `#hex` 81 + `rgba(` 35 = 116，可完全对上 |
| 模板内联（非注释） | **5** | 0 | 与 A 段一致 |
| CSS 非注释 | **97** | 34 | |
| ├ `filter: progid:` 滤镜参数 | 10（5 行 × 2 个 `startColorstr/endColorstr`） | 10 | 逐条确认 `prop == 'filter'`，Chrome inert |
| └ 有效声明级字面值 | **87** | **24** | 现行 24 条**全部**经回溯选择器确认为 `.read_style_*` 遗留 |
| CSS 注释内 | **14** | 14 | 两侧多重集**完全相同**（`#4a4a4a`×1、`#e0e0e0`×1、`#fff`×2、`rgba(255,255,255,0.5)`×1 等） |
| 声明行数（现行白名单口径） | — | 29 行 = 24 + 5 | 24 行遗留 + 5 行 progid |

校验恒等式：HEAD `5 + 97 + 14 = 116` = 全量 116 ✓；现行 `0 + 34 + 14 = 48` = 全量 48 ✓。（现行 CSS 34 个 token 分布在 29 条声明行上：24 条各含 1 个 token + 5 条 progid 各含 2 个 token = 24 + 10 = 34 ✓）

- Developer 报「88 声明 + 14 注释 + 10 IE filter + 6 内联 = 118」：**声明应为 87（多算 1）、内联应为 5（多算 1）**，故 118 应为 116。（现行 `code` 侧口径「29 条声明行」= 24 遗留 + 5 progid 行，与 token 数 34 不冲突：其中 5 行各含 2 个 token。）
- Developer 报「原始正则 120，含 2 处跨行」：实测单行正则、多行正则、DOTALL 正则三种写法匹配数**均为 116**；跨行（token 内含换行）的 `rgba(` 匹配数 **= 0**。**「120 / 2 处跨行」不成立**（其自身体验记录已自我更正为「内联实为 5 行」）。
- **实质结论不受影响**：现行 `BookContent.vue` 中「非遗留、非 IE filter」的存活色值 **= 0**；剩余 24 条遗留字面值是被任务明令保留的 `read_style_*`，与 AC4 的口径裁定同源。因此 TC3 的白名单判定与 AC4 的「无白蒙层残留」均成立。

### C. 排行榜名次徽标对比度（`.num1/.num2/.num3`）

**裁定：Developer 的归类正确 —— 是历史值，不是 T-010 缺陷；但应作为范围外发现上报（建议 T-013 处理）。**

- `git show HEAD:src/assets/styles/main.css` 第 58/59/60 行**确含** `#fc7403` / `#f79415` / `#ffa95e` → 该三色在 T-010 立项前就存在。
- 现行 `main.css`（第 58–60 行）只把这三处改为 `var(--nv-rank-1/2/3)`，而 `theme.css` 中 `:root`（第 127–129 行）与 `html.dark`（第 294–296 行）**取同一组值** `#fc7403/#f79415/#ffa95e`，即深色段沿用浅色值。`main.css` mtime 10-29 11:58（T-009 窗口），**不在 T-010 的 12:54–13:36 窗口**；`theme.css` 第 230 行有注释「纯装饰性色块（名次 / 等级徽标）保持浅色值以保证白字可读」。
- 我实测的对比度与 Developer 报数**完全一致**：白字 on `rgb(252,116,3)` = **2.75**、on `rgb(247,148,21)` = **2.28**、on `rgb(255,169,94)` = **1.89**；**浅色主题下同样是 2.75/2.28/1.89**（`v11-ac-probe.json`）—— 即深色并未恶化，属改造前既有对比度问题。
- 因此不构成本任务 FAIL；作为范围外发现列出。

## 对 Developer 声明的采信情况

| Developer 声明 | Tester 结论 | 依据 |
|---|---|---|
| 「内联白蒙层实为 5 行不是 6」 | **采信** | HEAD 原文逐行核对，确为 5 条（L11/93/124/131/138） |
| 「原口径残留命中在 `.read_style_*` 遗留规则内，改判为内联属性口径」 | **采信并独立论证** | 4 行命中位置逐条核实 + 运行期证明该类永不生效（A 段） |
| 「`read_style_*` 未删除/未改写」 | **采信并加强** | 不仅是 diff，做到了 23 个顶层规则块 / 94 个选择器的选择器序列、顺序、块体 sha256 两侧完全一致 |
| 「浅色观感不变」 | **采信并强化** | 我做到 8 路由 **0 像素差异** + 阳性对照 13.6 万~50.6 万 px 触发 + 样式表活性探针 |
| 「深色正文对比度达标」 | **采信并独立复算** | 自写 alpha 合成探针，正文 11.26、工具栏 14.06、按钮 13.98 等逐项给出 |
| 「名次徽标 2.75/2.28/1.89 属 T-008 历史色板、本任务禁止改」 | **采信** | `git show HEAD:` 证实存在；深色沿用浅色值；main.css 不在 T-010 窗口 |
| 「BookContent 改前 120 处 / 88 声明 / 6 内联」 | **不采信（算术）** | 实测 116 = 5 内联 + 97 CSS（含 10 filter token）+ 14 注释；跨行 0 处。实质结论仍成立（B 段） |
| 「lint 115（notes 中 116 为旧口径）」 | **采信** | 实测 115 errors / 0 warnings，与 T-008/T-009 基线一致 |

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 排行榜名次徽标白字对比度 2.75/2.28/1.89，低于 WCAG AA（浅色/深色相同） | `assets/styles/main.css` + `theme.css`（T-009 色板） | 归入 T-013 全站收口；若要修需同时给深色单独取值 |
| 2 | 品牌色实心按钮白字 on `#ff8800` 对比度 2.39（分页当前页、书籍详情「点击阅读」、顶栏「首页」），浅色/深色相同 | 品牌色设计取舍（T-008 `--nv-brand`） | T-013 评估；若改品牌色会破坏浅色基线，建议单列 |
| 3 | 书籍详情「暂无评论」深色 3.27（浅色 1.61，已被本任务改善） | `main.css .no_comment` | T-013 微调 |
| 4 | 阅读页浅色下 `textinfo` 3.94、`.menu_left` 文字 3.94、`.menu_right` 文字 2.61（深色已改善至 6.93/6.93/5.75） | `BookContent.vue` 浅色既有色阶 | T-013 视需要；不属本任务范围（本任务只做变量化，浅色值必须保持原样） |
| 5 | 阅读设置弹窗不可达：`.ico_setup` 位于 HTML 注释 L33–L63（运行时计数 0），`.maskBox` DOM 中不存在（运行时计数 0，仅 CSS 有规则），`.setupBox` `display:none` 且无任何可见入口 | `BookContent.vue` 模板（HEAD 即如此） | 与「阅读主题切换」一起归入 T-013 / PRD 7.6；本轮已强制置为可见做探针验证：深色下弹窗底色 13.83、标题 13.83、字体按钮 6.31、字号按钮 13.83、关闭按钮 13.83 均可读；仅 6 个色板圆点里的 `.white` 为 2.45（该值度量的是 `#f80` 描边与底色，不是文字） |
| 6 | `window.BookDetail` 全局未定义 → 模板内 `javascript:BookDetail.*` 的 onclick 全部为死绑定（`SetBackUpColor` / `AddFavorites` / `SetReadFont` 等） | 遗留模板（HEAD 即如此） | 记入 T-013 或技术债清单 |
| 7 | 深色下书籍封面仍是浅色图片（`default.gif` / `/localPic/**`），非 CSS 可控 | 资源层 | AC3 只要求「封面占位、文字可读、不粘连」，已满足；图片本身不做处理 |
| 8 | 图片 404（`/localPic/**`、`/images/default.gif`） | 资源层/后端静态服务 | 环境问题，非本任务 |
| 9 | `utils/auth.js` 的 localStorage 读写无 try/catch | `utils/auth.js`（10-20 改动，非 T-010） | 技术债 |
| 10 | 工作区存在多处与本任务无关的未提交改动：`router/index.js`(+38/-1)、`api/{user,book,resource}.js`、`utils/{auth,index}.js`、`views/{BookUpload,MyUpload,BookManage,UserHistory,Login,author/*}.vue`、`components/{author/Header,user/Menu,common/Navbar,common/Top}.vue`、`assets/styles/{base,main,book,about,user}.css`、删除的 `yarn.lock` | 前序任务（上传图书 / 阅读历史 / 管理员 / T-008/T-009） | 属前序任务的未提交产物；T-010 自身只碰 5 个文件（见 TC9）。建议 Orchestrator 在前台主题整轮收口后统一提交 |
| 11 | `tasks.json` T-010 notes 记「116 条历史 ESLint 错误」，实际为 115 | `.sdd/tasks.json` | 口径刷新，不影响判定 |
| 12 | `BookContent.vue` 存在 5 条 `filter: progid:DXImageTransform…`（L397/403/1063/1074/1082，各含 startColorstr+endColorstr 共 10 个色值 token）与 5 条 `filter: alpha(opacity=…)`（L1006/1012/1016/1054/1144）IE 私有滤镜声明 | `BookContent.vue`（HEAD 即如此） | 现代浏览器 inert，无功能影响；如需清理属规范化范畴（T-013 / code-review） |

## 环境与收尾

- 实测环境：1024（PID 24836）/ 8888（PID 20972）/ 3306（PID 29416）/ 6379（PID 10984），与 Developer 交付时一致；服务端 `app.js` 含 `nv-reader-panel-bg` ×4、内联蒙层 ×0，确认服务的是当前代码。
- 全程未执行 `git checkout` / `git reset` / `git clean`；未修改任何 Developer 代码；临时脚本与证据全部位于 `.sdd/tmp/t010-tester-scan/` 与 `.sdd/tmp/t010-tester-evidence/`，未污染项目根与 `frontend/` 根（`frontend/src` 下临时 HEAD 探针目录 `__t010probe__` 已清理，复核 `ls src | grep -i probe` 无结果；`git status` 中无任何 tester 产物）。
- **环境已关闭**：执行 `powershell -File ./stop-novel.ps1`，脚本按 前端→后端→Redis→MySQL 逆序关闭，输出四端口 `RELEASED`；随后独立复核 `netstat -ano | grep LISTENING | grep -E ':(1024|8888|3306|6379)\s'` → **无任何监听**，`curl http://localhost:1024/` 与 `http://localhost:8888/` 均返回 `000`（连接失败）。
