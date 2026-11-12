# 测试报告：T-013 深色全站走查与收口

**测试时间**：2026-10-29 23:26
**Tester Agent ID**：claude-code/tester（独立复验，不采信 Developer 任何声明；本轮为全站门禁任务）
**user_gate**：true

## 结果：PASS

环境核验（独立）：`http://localhost:1024` PID 23564（Vue CLI dev server）、`http://localhost:8888` PID 19248（Spring 后端）、MySQL 3306 PID 28476、Redis 6379 PID 20596 全部 LISTENING。浏览器访问一律使用 `http://localhost:1024`（不使用 `127.0.0.1`）。无 BLOCKED 条件。

变更面独立核定：T-013 时间窗（2026-10-29 21:00 之后）内 `frontend/src` 下仅 2 个文件被写：

```
2026-10-29 21:31:26  src/components/common/Top.vue
2026-10-29 21:32:13  src/assets/styles/theme.css
```

`find frontend/src -newermt "2026-10-29 21:00" | wc -l` → `2`。`backend/src` 时间窗内 0 文件（仅 `backend/logs/*.log` 运行日志滚动）。与任务申报的变更面完全一致。

## 验收标准逐条验证

| # | 标准 | 结果 | 独立证据 |
|---|------|------|----------|
| 1 | 未登录、普通用户、管理员三种状态下，任意页面顶部导航栏右上角都能看到主题切换图标；点击后当前页面立即变色，无需刷新 | PASS | 三态各 8 条前台路由全部 `present=true, visible=true, inHeaderRight=true`，几何一致 `rect=[1210,27,20,38]`，`title/aria-label="切换为深色主题"`，含图标。未登录态另测 `/home /bookclass /book_rank /login /register /book_upload /book/:id /book/:id/:chapterId`；登录态与管理员态另加 `/user/setup /user/comment /user/history /my_upload`（管理员另含 `/book_manage`）全部命中。**点击立即变色无刷新**：`navMark=12345`（导航计数器）前后不变、`urlSame=true`、`noReload=true`，`class` `""→"dark"→""`，`bodyBg` `rgb(245,245,245)→rgb(20,20,20)→rgb(245,245,245)`，`localStorage.novel-theme` `null→"dark"→"light"`。三态结果完全一致。 |
| 2 | 深色下依次访问并确认无不可读区域：首页、全部作品、排行榜、书籍详情、正文阅读、登录、注册、用户设置、我的评论、阅读历史、上传图书、我的上传、书籍管理 | PASS | 13 路由逐页实测：`html.class` 均为 `dark`、`bodyBg` 均为 `rgb(20,20,20)`、`whiteBlockCount=0`（宽度>20 且高度>20 的白色/半透明白色块为 0）。**全站 `<2.0` 极低对比扫描**（逐叶子文本节点，含半透明底色叠加计算）：深色 13/13 页面 `badCount=0`（元素数 60–1095）。对照浅色：仅 2 处历史遗留低对比（书籍详情「暂无评论」1.61、阅读历史 `update_time` 1.76），深色无新增。 |
| 3 | 深色下页面内的下拉选择框、消息提示、确认/编辑对话框、分页器、空数据提示、加载遮罩均为深色系，与页面整体协调，不出现白底弹层 | PASS | teleport 组件逐个实测 computed（均 `inBody=true`）：**下拉** `.el-select__popper`（实际承载底色的元素）`backgroundColor=rgb(29,30,31)`、文字 `rgb(229,234,243)`、边框 `rgb(65,66,67)`；下拉项 `rgb(207,211,220)`。**ElMessage** `rgb(43,29,29)` + 文字 `rgb(229,234,243)` + 图标 `rgb(245,108,108)`（浅色对照 `rgb(254,240,240)`）。**MessageBox** `.el-message-box` `rgb(20,20,20)`、边框 `rgb(54,54,55)`、内容 `rgb(207,211,220)`、取消钮透明+`rgb(207,211,220)`（浅色对照 `rgb(255,255,255)`）。**编辑对话框** `.el-dialog` `rgb(20,20,20)`、标题 `rgb(229,234,243)`、遮罩 `rgba(0,0,0,0.5)`。**分页器** 容器透明、页码 `rgb(229,234,243)`、当前页 `rgb(255,136,0)` 白字（与浅色同值）。**空数据提示** 有效底 `rgb(29,30,31)`、文字 `rgb(163,166,173)`。**加载遮罩** `rgba(0,0,0,0.8)`（浅色对照 `rgba(255,255,255,0.9)`），几何同为 `[552,208,396,15]`。全站无白底弹层。 |
| 4 | 深色下正文阅读页可长时间阅读：正文区域底色为深色、文字为浅色，顶部工具栏与章节导航同为深色系，页面上无白色或半透明白色块残留 | PASS | 正文 `.textbox` 有效底 `rgba(29,30,31,0.9)`、文字 `rgb(207,211,220)`、字号 16px/行高 32px（`#showReading` 实占 `[323,275,794,4934]`，未变）。顶部工具栏 `.topMain` `rgba(29,30,31,0.85)`；章节导航 `.nextPageBox a`（上一章/目录/下一章）`rgba(29,30,31,0.9)`；目录 `.read_menu li a` 文字 `rgb(229,234,243)`。**白块扫描**：深色阅读页 `whiteBlocks=[]`（0 个；浅色同页有 6 个 `rgba(255,255,255,0.4~0.45)` 块，说明扫描器有效）。 |
| 5 | 刷新任意处于深色的页面时直接呈现深色，不出现先浅后深的闪动；首次访问（清空浏览器存储）默认浅色 | PASS | 首帧时序（MutationObserver on document subtree + PerformanceObserver，6 路由）：单次 class 变更为 `dark`，`mutations[0].t ≤ DCL ≤ firstPaint` 恒成立（home 946.8 ≤ 948.9 ≤ 964；bookclass 1080.8/1082.4/1100；login 1031.6/1034.2/1056；book_upload 998.2/999.7/1020；bookcontent 1173.8/1175.1/1204；book_manage 1045.3/1046.8/1072）。`clsAtDCL='dark'`、`bgAtDCL=rgb(20,20,20)`、`csAtDCL='dark'` 全部满足 DOMContentLoaded 时刻已深色。**首次访问对照**：清空 storage 且 OS 为 `prefers-color-scheme: dark` 时 `mutations=[]`、`clsAtDCL=''`、`bgAtDCL=rgb(245,245,245)`、`stored=null` —— 默认浅色，不受系统深色偏好影响。 |
| 6 | 切换主题后业务功能不受影响：登录与退出、搜索、列表分页、正文上下章、我的上传的筛选与翻页、书籍管理列表与编辑对话框打开均正常 | PASS | 真实交互逐项执行（深色下）：**登录** `#/login`→填表→`#/home`，token/nick/isAdmin 正确写入；**退出** 清空 token/nick/isAdmin 回 `#/home`，`hasLogin=true`。**搜索** 「战神」→ `#/bookclass?key=战神`、15 行、当前页 1。**分页** 页 1→页 2，`active` 由 `" 1 "`→`"2"`。**书籍详情** 标题「我给战神王爷寄刀片」、3 章。**正文上下章** 第1章→点「下一章」→`#/.../1334318186313654272`「第2章  解毒」→点「上一章」→回第1章（`nextChanged=true`、`prevReturned=true`）。**我的上传** 筛选「连载中」→ 0 行 + 空提示「暂无上传图书」；分页器 `Total 1`。**书籍管理** 10 行、分页器在、编辑对话框打开标题「编辑书籍信息」+ 3 个输入框、取消后 `messageBoxDismissed=true`、第 2 页 10 行。控制台：`84 × 404`（全部为 `/localPic/**`、`/images/default.gif` 等既有书籍封面缺失，浅色同样存在，非本任务引入）；`pageErrors=null`，无 JS 异常。 |
| 7 | 浅色主题下各页面观感与改造前一致，首次访问默认浅色的表现与改动前相同 | PASS | 见「浅色等价性的可证明构建」：**静态证明为主**（theme.css 注释剥离后逐字节相同；Top.vue 差异仅 logo 绑定且浅色分支取原 `logo.png`）+ **像素证明为辅**（Developer A/B：13 路由中 11 条 `changed_px=0`，唯二非零页的差异区域经正/负对照证明为动态内容）。首次访问默认浅色见 AC5 的 `B_clearedSystemDark`。 |
| 8 | 整个页面在两种主题下布局一致，无因改色引起的错位、遮挡、换行或滚动条异常 | PASS | 13 路由浅 vs 深逐元素 `getBoundingClientRect` 几何快照：`geometryDiffs=0` 于 12/13（home/全部作品/排行榜/正文/登录/注册/用户设置/我的评论/阅读历史/上传图书/我的上传/书籍管理）；元素数两主题完全相等（如 home 827/827、book_manage 436/436、bookcontent 166/166）；`docH` 两主题相等（home 4134/4134、bookcontent 5369/5369、book_manage 1340/1340）。**唯一非零页为书籍详情 `geometryDiffs=4`**，全部落在右侧「同类推荐」栏 `x=1074`，为书名宽度差异；已用**同主题对照证明其为随机内容**：同一主题两次独立加载同样 `geometryDiffs=4`，且两次书名列表完全不同（run1 `烽烟满袖花满襟/中国敢死军/檀香刑/千古第一圣贤` vs run2 `谍战/北国谍影/从今天开始做藩王/亭长小武`）；`docH` 该页 1428/1428 相等。横向溢出 `overflow=[0,0]` 于全 13 页。文本裁切属既有省略号/多行截断设计，两主题分类一致（home 5/5、book 4/4、book_manage 3/3、bookcontent 0/0）。 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 独立证据 |
|---|--------|------|----------|
| 1 | `npm run lint` 本次修改文件 ESLint delta = 0；`npm run build` 通过 | PASS | **lint**：自跑 `npx vue-cli-service lint --no-fix` → `115 problems (115 errors, 0 warnings)`。Top.vue 的 2 条均为历史遗留（`59:28 'onMounted' is defined but never used`、`65:9 Component name "Top" should always be multi-word`）。**delta 精确核对**：对「当前版」与「T-013 前基线副本 `.sdd/tmp/t013-baseline/Top.vue`」分别 `npx eslint --stdin --stdin-filename src/components/common/Top.vue` → 两者均 `2 problems (2 errors)`，规则名与数量完全相同，仅行号由 58/64 偏移到 59/65（因新增 1 行 import + 2 行注释）。**delta = 0**。theme.css 为纯 CSS，不参与 ESLint。**build**：我独立执行 `npm run build` → `DONE Build complete`，`BUILD_EXIT=0`（`Hash: efd62a97824e9934`，45874ms）。允许的既有体积告警不影响 exit code。 |
| 2 | 残余色值扫描：排除 theme.css / easyui.css / layer.css 后逐条列出并给出结论；不允许未说明残余 | PASS | 按 TC 原命令执行：`grep -rn -E '#[0-9a-fA-F]{3,8}\b|rgba?\(' --include=*.vue --include=*.css src` 原始 608 行（其中 546 行属三个被排除文件）→ **排除后 62 行 / 69 个色值 token**。逐 token 分类（CSS 注释感知解析）：**注释内 31 行 / 33 token**（base.css 7 行、main.css 9 行、book.css 1 行、BookContent.vue 14 行）；**生效代码 31 行 / 36 token**，按来源归类：① HTML 实体 2 token —— `Header.vue:5`、`author/Register.vue:3` 的 `&#8249;`（`‹` 字符，非颜色值）；② IE `progid:DXImageTransform` 滤镜 5 行 / 10 token（`BookContent.vue:397,403,1063,1074,1082`）；③ `filter: alpha(...)` 5 行（`1006,1012,1016,1054,1144`，IE 私有透明度，Chrome 下 inert）；④ 半透明 `rgba(255,255,255,α)` 5 行（`404,466,484,490,503`）；⑤ 死亡选择器 `.read_style_1..6` 内的调色板 20 token（`402,409,412,415,418,421,424,430,436,442,448,454,460,502,526,533,771,931,1078`）。**全部 69 token 已逐条说明，无未说明残余**。运行时反证死亡性：`document.querySelectorAll('[class*="read_style_"]').length = 0`（浅/深两主题皆然），且 `body` 在 `<style scoped>` 内不携带 `data-v-*` 属性（`bodyAttrs=[]`），故 `body,.read_style_1{background-color:#ebe5d8}` 该条规则不生效——实测 body 取主题值 `rgb(20,20,20)`/`rgb(245,245,245)`。 |
| 3 | EP teleport 实测：深色下打开状态筛选下拉与编辑对话框，读取挂载在 body 下 computed backgroundColor 为深色 | PASS | 见 AC3 的逐组件数据。补充关键点：Element Plus 2.2.0 的 `.el-select-dropdown` 自身 `backgroundColor` 为 `rgba(0,0,0,0)`（透明），真正承载底色的是其祖先 `.el-select__popper`（同为 `body` 子节点）`rgb(29,30,31)`；判定以 popper 为准，深色成立。编辑对话框 `.el-dialog` `rgb(20,20,20)`。两者 `inBody=true`。 |
| 4 | 对比度抽样：正文阅读区、管理表格行、登录表单、用户中心列表各 1 处，正文 ≥ 4.5、辅助文字 ≥ 3 | PASS | 用相对亮度公式独立计算（深色）：**正文阅读区** `.textbox` 文字 `rgb(207,211,220)` on `rgba(29,30,31,0.9)` → **11.13**；**管理表格行** `.el-table__body td .cell` `rgb(207,211,220)` on `rgb(29,30,31)` → **11.13**；**登录表单** `.loginTitle/.loginBody` → **13.83 / 15.26**；**用户中心列表** `.menu`/列表项 → **13.83**。辅助文字：阅读区元信息 `.textinfo span` → **6.85**、表格表头 `th .cell` → **7.56**（均 ≥ 3）。达标。 |
| 5 | 首帧无闪烁：localStorage 预置 dark 后加载页面，`domcontentloaded` 时刻 `document.documentElement` 已含 dark class | PASS | 6 路由全部 `clsAtDCL='dark'`（见 AC5 明细）。另附 `bgAtDCL=rgb(20,20,20)`、`csAtDCL='dark'` 佐证不只是 class 位、样式已生效。首帧绝对毫秒不作为基线（按 Pitfall #4 的口径，仅取值序：class 变更 ≤ DCL ≤ 首次绘制）。 |
| 6 | 全路由截图：13 前台 + 5 作者后台路由，light/dark 各一套（1440x900） | PASS | 前台 13 路由 × 2 主题 = 26 张，均由我独立采集：`.sdd/tmp/t013-tester/light/p-light-{home,bookclass,book_rank,book,bookcontent,login,register,user_setup,user_comment,user_history,book_upload,my_upload,book_manage}.png` 与 `.sdd/tmp/t013-tester/dark/p-dark-*.png`（视口 1440×900，`channel:'chrome'`）。**作者后台 5 路由未标 BLOCKED(账号)**：以管理员身份直接可达（无需作者账号）`/author/book_list`、`/author/book_add`、`/author/chapter_list`、`/author/chapter_add`、`/author/chapter_update`，另含 `/author/register`，共 6 页 × 2 主题 = 12 张：`.sdd/tmp/t013-tester/{light,dark}-author-*.png`。故 TC6 实际交付 38 张，超出要求的 36 张。 |
| 7 | 功能回归：登录/退出、搜索、分页、正文上下章、我的上传筛选与翻页、书籍管理对话框打开全部真实执行，无控制台报错、无新增失败请求 | PASS | 详见 AC6。控制台仅 84 条 `Failed to load resource: 404`，全部指向 `/localPic/**` 与 `/images/default.gif`（既有封面图片缺失，浅色下同样出现，不属于本任务新增）。无 JS 运行时异常（`pageErrors=null`），无接口 5xx，无新增失败请求类型。 |
| 8 | 未改动项核对：`easyui.css`/`layer.css` sha256 与改造前一致；`frontend/package.json` 逐字未变；`backend/` 下无文件改动；`docs/api-contracts.md` 未改 | PASS | `git status --porcelain src/assets/styles/easyui.css src/assets/styles/layer.css package.json` → **空输出**（未改动）；三者 mtime 均 `2026-09-04 14:45`，远早于本任务。`backend/src` 时间窗内 0 文件（`find backend/src -newermt "2026-10-29 00:00"` 无输出）。`docs/api-contracts.md` mtime `2026-10-21 14:40`（早于 T-013，为 T-011 期文件）。 |
| 9 | 浏览器实测在 `http://localhost:1024` 进行（不使用 127.0.0.1） | PASS | 全部 Playwright 会话 base 均为 `http://localhost:1024`，`channel:'chrome'`，viewport 1440×900。无任何 `127.0.0.1:1024` 访问。（`127.0.0.1:8888` 仅出现在后端返回的图片 URL 中，属既有封面路径，非本次页面访问。） |

## 浅色等价性的可证明构建（AC7 / AC5 详述）

这是本任务最容易「看起来对了其实没证明」的一条。我采用**静态证明为主、像素证明为辅**的双轨，并且构造了正/负对照。

### 1. 静态证明（决定性）

**theme.css**（对比 T-013 前的基线副本 `.sdd/tmp/t013-baseline/theme.css`，该副本 sha256 前缀 `5006dfc3`，与本轮 `t008-final.sha256` 的 T-008 收口态一致）：

- 注释剥离后两版**逐字节相同**：基线 8654 字节 / 现行 8654 字节，sha256 前缀同为 `2b5ce61e3f780601040cba22`，`STRIPPED IDENTICAL: True`。
- `:root` 块 134 个声明、`html.dark` 块 134 个声明，两块的**变量名、顺序、取值**与基线完全相同（`names_equal=True`、`values_equal=True`）。
- 文件字节数 12830→14187 的增量全部为注释（本任务新增的变量批次登记注释），**零变量值变化**。这与 Pitfall 声明一致，且我已独立复核而非采信。

**Top.vue**（`diff -u .sdd/tmp/t013-baseline/Top.vue frontend/src/components/common/Top.vue`）：差异恰为 4 处 hunk，语义仅为 logo 绑定：

```js
+import logoWhite from "@/assets/images/logo_white.png";
+    // 深色下顶栏为深底，深色字 logo 不可读，切换为同源白字版本（其余尺寸不变）
+    const logoUrl = computed(() => (dark.value ? logoWhite : logo));
-      logo,
+      logoUrl,
```

模板 `<img :src="logo"` → `<img :src="logoUrl"`。浅色分支 `logoUrl` 求值为**原 `logo.png`**，故浅色路径与改造前逐像素等价（已由浏览器实测确认渲染的是 `logo.png`，见下）。`logo_white.png` 非本任务新增资产：`git ls-tree -r HEAD` 中存在 `src/assets/images/logo_white.png`，`git cat-file -s` = 6045 字节，磁盘 mtime `2026-09-04 14:45:53`，均早于本任务。

### 2. 像素证明（辅助）与其可信度边界

Developer 在 `.sdd/tmp/t013-evidence/` 下提供了 `pre-edit/`（26 张）与 post 版（26 张）的 A/B。**我复核发现基线时序存疑**：`pre-edit` 截图 mtime `21:32:24`，晚于 `Top.vue` 的 `21:31:26` 与 `theme.css` 的 `21:32:13`；dev server 最后一次重编译为 `21:32:14`（`frontend-run.log` 的 `DONE Compiled successfully in 686ms21:32:14`）。也就是说该 A/B 的「前」是**在源码改完之后、依赖 21:32:14 之前产物**的快照，而不是严格意义的改造前快照。

但**该前置状态仍然可证为「logo 未切换」的旧行为**，因为深色截图能直接读出这一点：`pre-edit/p-dark-home.png` 的 logo 区域 `(261,35)-(412,59)` 平均亮度 **22.7**、最大 31、亮像素 0（尚未换成白色 logo）；post 版同区域平均 **82.5**、最大 255、亮像素 446（白色 logo 已出现）。我在自己独立采集的深色截图上量得 **83.1 / 255 / 453**，与 post 版一致。因此该 A/B 的「前」确实处于「改完源码、尚未用新产物」的中间态，其**浅色结论仍然有效**（浅色下 logo 分支未变，新产物与旧产物浅色表现相同），但我不把它当作唯一的浅色证据。

**我独立重算 Developer A/B 的结果（不采信其结论）**：

- 浅色：13 路由中 **11 条 `changed_px=0`**（home、bookclass、book_rank、bookcontent、login、user_setup、user_comment、user_history、book_upload、my_upload、book_manage）。非零 2 条为 `book`（14997 px，bbox `(1073,827)-(1206,1262)`）与 `register`（3312 px，bbox `(584,453)-(683,490)`）。
- 深色：13 路由中 **11 条 bbox 精确等于 `(261,35)-(411,58)`、`changed_px=1876`**，即 logo 区域；`book`（15542 px，bbox 含 logo + 右栏 `(261,35)-(1206,1262)`）与 `register`（4992 px，bbox `(261,35)-(683,490)`）为 logo + 动态区。

**对两条非零页做正/负对照（必须的活性证明）**：

- **负对照（同状态重复截图）**：`noise-register-1/2.png` 两次同状态截图区域 sha 完全相同（`387366a6781f81c8`），`noise-book-1/2` 亦相同 —— 截图管线本身确定性，噪声为 0。
- **正对照（浅 vs 深）**：我用同一套采集流程拍浅/深两版，13 路由差异 1,276,140 – 7,728,666 px（bbox 覆盖全页），证明比较器灵敏度充足、绝不会「什么都没比出来却说 0」。
- **证明 book/register 的非零来自动态内容而非主题回归**：`register` 的验证码区域 `(584,453)-(683,490)` 在 pre/post/reload1/reload2 四次加载里 sha 两两不同（`e7ac3ea7`/`40c9b7f9`/`6df70423`/`465cc03d`）；`book` 的「同类推荐」区域 `(1073,827)-(1207,1263)` 在 pre/post/noise-b1/noise-b2 四次加载 sha 亦两两不同（`87667b31`/`256aec6f`/`f1eee698`/…）。同主题连续两次加载这些区域本来就变，故其像素差**不可归因于主题改造**。
- **另有口径证据**：`captchaAcross3Loads` 三次加载验证码图 base64 尾部三次不同；`bookRightListAcross3Loads` 三次加载的推荐书名集合不同。

**关于我自己采集的截图**：我的 26 张与 Developer 的 26 张做逐像素比较时差异达数千至数百万 px。定位为**浏览器色彩配置差异**（我的 PNG 带 `sRGB` chunk，Developer 的无；同一文件的 nav 区域裁切肉眼完全一致，纯为抗锯齿/色彩转换噪声）。我因此**不以跨采集者的像素比较判定**，而以上述「静态等价 + 同采集者内 A/B + 正负对照」作为 AC7 的证据链。这一处理对结论无影响：AC7 的决定性证据是不依赖截图管线的静态证明。

### 3. 首次访问默认浅色

`B_clearedSystemDark`：清空 `localStorage` 且操作系统 `prefers-color-scheme: dark` 的环境下，`mutations=[]`（从未加 dark class）、`clsAtDCL=''`、`bgAtDCL=rgb(245,245,245)`、`stored=null`、`finalClass=''`。即首次访问默认浅色，不跟随系统偏好。与 AC5 后半句、AC7 后半句一致。

## 对 Developer 7 条「踩坑说明」的独立判断

| # | Developer 声明 | 我的判定 | 独立依据 |
|---|---------------|---------|---------|
| 1 | 路由名陷阱：应为 `/#/book_rank` 而非 `/#/bookrank` | **采纳** | `router/index.js` 中路径为 `/book_rank`（name 为 `bookRank`）。我实测 `/#/book_rank` 正常渲染（`hash="#/book_rank"`、453 个元素、`#btnSubmit` 等无异常）；而证据目录里确实同时存在 `p-light-bookrank.png` 这种命名，若按文件名去访问对应 URL 会落到兜底路由、截出错误页面。 |
| 2 | 书籍详情页跨主题几何不可靠，因右栏「同类推荐」随机 | **采纳** | 同主题两次加载 `geometryDiffs=4`，且书名列表每次不同（见 AC8）。跨主题 4 处差异全在 `x=1074` 推荐栏。这解释了为何不能把该页的 4 处差异当作布局回归。 |
| 3 | EP 下拉背景透明，需以下拉 popper 的祖先底色判定（TC3 口径修正） | **采纳** | 实测 `.el-select-dropdown` 的 `backgroundColor=rgba(0,0,0,0)`（且 `boxShadow=none`），真正承载底色的是 `.el-select__popper`（`rgb(29,30,31)`）。若按下拉节点自身判会误判为「透明/白底」，口径修正是必要的。 |
| 4 | 首帧的绝对毫秒不可作为基线，只能看时序 | **采纳** | 我 6 路由实测首帧 964–1204ms、DCL 948.9–1175.1ms，波动数十毫秒；同一路由重复加载绝对值也不稳定。只有「class 变更 ≤ DCL ≤ 首次绘制」的**相对次序**是稳定判据。 |
| 5 | EP 2.2.0 使用 `td.el-table-fixed-column--right` 而非 `.el-table__fixed-right` | **采纳** | book_manage 实测 `fixedRight(旧类名)=0`、`fixedRightV3(.el-table-fixed-column--right)=11`。证明若按旧类名定位固定列会得到 0 匹配而误判「固定列未渲染」。 |
| 6 | 深色下 `.s_input` 的 `rgb(59,59,59)` 来自 `color-scheme: dark` | **采纳** | 作者后台原生 `<input>`：深色 `rgb(59,59,59)`、浅色 `rgb(255,255,255)`；而 `.inpMain` 这类被显式设色的元素深色为 `rgb(29,30,31)`。59,59,59 是 Chrome 深色 UA 默认底色，说明该处未显式设色、由 `color-scheme` 接管——这与 `applyTheme` 里设置 `root.style.colorScheme` 的实现一致，可直接观察到。 |
| 7 | `clipped.json` 属过期/浪费 | **部分采纳（口径需修正）** | 该文件只覆盖 4 页 × 2 主题（`light_home/light_book_manage/light_my_upload/light_book` 及 dark 同名），而实际走查覆盖 13 页。就「覆盖面不足、不足以支撑全站结论」而言声明成立。但我核对其中数值并非错误：`light_book` 的 `sw/cw=136`、`sh/ch=234/54` 与 `layout-equality.json` 的 `clippedDelta` 完全一致，`home` 的 `153/153`、`216/72` 亦一致。故准确表述应为「**覆盖不全**」，而不是「数据错误」。我不以此判定任何标准 FAIL。 |

## 对 Developer 8 条关键声明的独立核对

| # | Developer 声明 | 我的判定 | 独立依据 |
|---|---------------|---------|---------|
| 1 | theme.css 零变量值变化 | **成立** | 注释剥离后逐字节相同（8654/8654，sha `2b5ce61e`）；`:root` 134 与 `html.dark` 134 的「名+序+值」与基线完全相同。 |
| 2 | Top.vue 仅 logo 变更；`logo_white.png` 为仓库既有资产（mtime 2026-09-04） | **成立** | `diff -u` 仅 4 处 hunk，全部围绕 logo 绑定；`git ls-tree HEAD` 含该文件，6045 字节，mtime `2026-09-04 14:45:53`。浏览器实测浅色渲染 `logo.png`（sha `78f2723a`、4972B）、深色渲染 `logo_white.png`（sha `c5d57215`、6045B），显示尺寸两主题同为 216×48、`rect=[210,23,216,48]`。 |
| 3 | 残余 69 处按类解释（read_style 24 / progid 5 行-10 token / alpha 5 行 / 注释 33 / 实体 2 / easyui+layer） | **成立（数字已独立复算一致）** | 我的复算：原始 608 行（含被排除文件 546 行）→ 排除后 62 行 / **69 token**；注释内 33 token；生效 36 token = 实体 2 + progid 10（5 行）+ alpha 5（5 行）+ 半透明白 5 + 死亡选择器调色板 20（其中 `#444/#999/#f80/#aaa` 等分散在 8 行）。分类结构与其一致，**69 这一总数我独立复现**。 |
| 4 | 浅色 11/13 页 diff=0，book 与 register 为动态内容 | **成立（但我重算了 A/B，且指出其基线时序瑕疵）** | 我重算 `changed_px` 得 11 条 0；book/register 非零区域经验证码与推荐书名四次加载皆变、同状态重复截图 sha 相同、浅深正对照 1.27M–7.73M px 三重对照证实为动态内容。**但**其 `pre-edit/` 快照 mtime（21:32:24）晚于源码写入（21:31:26/21:32:13），属「改完源码未换产物」的中间态而非严格改造前态；不影响浅色结论，但作为「改造前基线」的证据强度应打折。 |
| 5 | 深色 13 页仅在 logo bbox 差异，且 bbox 为 (261,35)-(412,59) | **成立（bbox 微差已核）** | 我重算：11 页 bbox `(261,35)-(411,58)`、1876 px。声明里的 `(412,59)` 与实测 `(411,58)` 差 1 px——`getbbox()` 返回的是排他上界（exclusive bound），两种写法指同一区域，非矛盾。book/register 两页 bbox 为「logo ∪ 动态区」，属预期。 |
| 6 | `grep -rn 'html.dark .el-' src` = 0 | **成立** | 我独立执行，命中 **0**。 |
| 7 | lint delta=0，仓库总数 115，build exit 0 | **成立** | 自跑 lint `115 problems (115 errors, 0 warnings)`；Top.vue 当前版与基线版各 2 条同规则错误、delta=0；自跑 build `BUILD_EXIT=0`、`DONE Build complete`。 |
| 8 | DB 基线在 Developer 创建作者账号后已恢复 | **成立（并附一处只读副作用）** | 我独立查询：`author_info=0`、`book_info=108`、`book_chapter=17756`、`book_content=17756`、`user_info=1`（仅 `admin`），**与给定基线逐项一致**；今日新建书籍 0、今日新建章节 0；`author_info` 无今日记录。副作用：`user_read_history` 共 6 行，其中 id=7（book_id `1334318182169681920`）的 `update_time` 为 `2026-10-29 23:18:38`，是走查阅读正文时的**只读浏览副作用**（该行 `create_time` 为 `21:46:54`，亦在本轮窗口内）。详见下方「数据库与缓存清理复核」。 |

## 数据库与缓存清理复核

- 计数复核（我直接连库查询，非读他人结论）：

```
author_info    = 0        (基线 0)
book_info      = 108      (基线 108)
book_chapter   = 17756    (基线 17756)
book_content   = 17756    (基线 17756)
user_info      = 1        (基线 1，仅 admin)
```

- 无本任务新建的业务实体：`book_info` / `book_chapter` 今日新建均为 0；`author_info` 无记录。
- **一条只读副作用需备案**：`user_read_history` id=7 的 `update_time` 被推进到 `2026-10-29 23:18:38`（`create_time` 21:46:54）。该表不是基线核对项（基线未给出其计数），且行为「访问正文即记录阅读位置」的产品逻辑，无法在不写库的前提下验证 AC6 的「正文上下章」。计数 6 行与走查前一致（未新增行），仅时间戳被刷新。**我未删除该行**（删除本身会破坏数据、且该行在走查开始前已由 Developer 的走查创建）。已在本报告显式备案，未做静默处理。
- 我本人未创建任何作者账号、书籍、章节、评论或用户；未执行任何 DELETE/UPDATE/INSERT。

## 环境关闭

验证完成后执行 `stop-novel.ps1` 关闭环境，并核对 1024 / 8888 / 3306 / 6379 四端口释放。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | 浅色主题下 2 处既有低对比（均非本任务引入，深色下反而更好）：书籍详情「暂无评论」文字对比 1.61；阅读历史 `update_time` 文字对比 1.76（深色下该页 0 处 < 2.0）。 | 前台浅色主题（T-009~T-012 既有产物） | 如后续做无障碍专项再处理；当前不阻断。 |
| 2 | `.sdd/tasks.json` 的 T-013 notes 写「116 个历史 ESLint 错误」，实测为 **115**。 | 任务元数据 | 与本轮 T-011/T-012 报告口径一致（115）。属历史漂移，建议 Orchestrator 在下一轮维护 tasks.json 时校正，不与代码质量挂钩。 |
| 3 | 书籍详情「同类推荐」每次加载随机换书（4/4 次不同），使该页无法用像素/几何做跨主题严格比对。 | 书籍详情页数据源 | 属既有产品行为，非缺陷。若后续需要可重复的视觉回归，建议为该栏提供可固定种子的调试开关。 |
| 4 | 全站书籍封面大量 404（`/localPic/**`、`/images/default.gif`），控制台 84 条 404 全来源于此，深色下封面仍为浅色图片。 | 静态资源/数据 | 既知问题，本轮不计入判定。深色下封面为浅色图属已知遗留。 |
| 5 | `frontend/src/views/BookContent.vue` 中 `.read_style_1..6` 为整套死样式（模板/脚本 0 引用，运行时 0 匹配），约 20 个硬编码色值因此「看起来该改但改了无效果」。 | 正文阅读页 | 建议后续清理死代码，可连带消除该文件大部分残余色值。不属本任务范围。 |
| 6 | Developer 的 `pre-edit/` 基线截图 mtime 晚于源码写入，且 `.sdd/tmp/t013-evidence/clipped.json` 仅覆盖 4/13 页。 | 验证证据 | 证据质量建议：基线快照应在改码**之前**采集并记录哈希；覆盖面应与走查范围一致。不影响本轮 PASS（我已用静态证明与自采数据补齐）。 |

## 临时文件清理

`.sdd/tmp/` 下由我创建的 `t013-tester-*` 脚本、JSON/日志输出与 `t013-tester/` 截图目录已全部删除。Developer 的 `t013-evidence/`、`t013-baseline/`、`t013-dev-*.py` 等属其产物，我未删除（清理范围按指令仅限我自己创建的临时文件）。

## 环境关闭确认

执行 `powershell -NoProfile -File E:\SDD_V7_1_2\SDD_V7_1_2\Projects_Repo\novel\stop-novel.ps1`（按启动逆序：前端 → 后端 → Redis → MySQL），exit code 0。脚本输出：

```
[stop-novel] 正在关闭前端（node，PID 23564）...
[stop-novel] 前端已关闭，端口 1024 已释放。
[stop-novel] 正在关闭后端（java，PID 19248）...
[stop-novel] 后端已关闭，端口 8888 已释放。
[stop-novel] 正在通过 redis-cli 优雅关闭 Redis（会按配置落盘）...
[stop-novel] Redis 未在优雅关闭后退出，改为强制结束进程。
[stop-novel] 正在强制关闭 Redis（PID 20596）...
[stop-novel] Redis 已关闭，端口 6379 已释放。
[stop-novel] 正在通过 mysqladmin 优雅关闭 MySQL（InnoDB 正常落盘）...
[stop-novel] MySQL 已优雅关闭，端口 3306 已释放。

关闭结果：
  Frontend   port 1024   RELEASED
  Backend    port 8888   RELEASED
  Redis      port 6379   RELEASED
  MySQL      port 3306   RELEASED

[stop-novel] novel shutdown finished. 四个端口均已释放。
```

独立复核（脚本之外）：

- `netstat -ano | grep LISTENING | grep -E ':(1024|8888|3306|6379)\s'` → **0 条**监听记录。
- 四个原 PID 逐一核对全部退出：`23564 gone`、`19248 gone`、`28476 gone`、`20596 gone`。
- 备注：Redis 未响应 `redis-cli shutdown` 的优雅关闭，脚本自动降级为强制结束进程后端口释放；MySQL 走 `mysqladmin shutdown` 优雅落盘成功。两者均在脚本的正常处理路径内，不是失败。

**四端口已全部释放，环境已关闭。**
