# 测试报告：T-011 账号中心与内容管理页变量化（登录 / 注册 / 用户中心 / 上传图书 / 我的上传 / 书籍管理）

**测试时间**：2026-10-29 19:30
**Tester Agent ID**：claude-code/tester（独立复验，不采信 Developer 声明）
**user_gate**：true

## 结果：PASS

检测环境：`http://localhost:1024`（Vue CLI dev server，PID 23564）、`http://localhost:8888`（Spring 后端，PID 19248）、MySQL 3306 / Redis 6379 均在监听；`GET http://localhost:1024/` 返回 200；登录 `admin/admin` 成功（`token: True`、`isAdmin: true`）。无 BLOCKED 条件。全程只读，未执行删除书籍 / 替换内容等破坏性操作；未关闭环境（T-012 仍需使用）。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 深色下登录/注册页表单卡片、输入框、占位符、按钮、错误提示清晰可读，无白卡压深色割裂感 | PASS | 实测浅/深两主题：卡片 `--nv-bg-container` 由 `#fff`→`#1d1e1f`（截图 `dark-login.png` / `dark-register.png`、容器 computed `rgb(29,30,31)`）；输入框正文深色 `rgb(229,234,243)` 比 13.83；占位符深色 `rgb(141,144,149)` 比 5.21（≥4.5）；错误提示 `--nv-danger-soft` 深色 `#f78989`。深色下「白卡压深色」现象不存在：8 个页面深色扫描未发现任何 `#fff` 级卡片底色（`round6.json`）。|
| 2 | 深色下用户设置/我的评论/阅读历史三页（含左侧用户中心菜单）卡片、菜单文字、分隔线为深色系，当前选中项一眼可辨 | PASS | 三页均实测（`round7.json`）：卡片 `rgb(29,30,31)`；菜单未选中 `rgb(163,166,173)` 比 6.85、选中项文字 `rgb(255,255,255)` 底色 `rgb(38,39,39)` 比 14.98 且左侧保留 2px 橙色高亮条（`rgb(255,136,0)`），选中态在三页分别正确落在「账号设置 / 我的评论 / 阅读历史」；分隔线 `--nv-border-lighter` 深色 `#363637`。截图 `dark-user_setup.png`、`dark-user_comment.png`、`dark-user_history.png`。|
| 3 | 深色下上传图书页文件选择框、表单、提交按钮、结果提示可读；选中文件后文件名不消失 | PASS | `dark-book_upload-selected.png` 实测：选中 `sample-t011.txt` 后文件名前景 `rgb(207,211,220)` on `rgb(29,30,31)` 比 11.13，`nameVisible: True`（浅色同位置为 `rgb(96,98,102)` 比 6.11）；表单标签深色 `rgb(207,211,220)` 比 11.13；提示文案 `rgb(141,144,149)` 比 5.21；`el-button--primary` 蓝底白字两主题一致（2.78，见「超出范围」说明）。|
| 4 | 深色下我的上传页表头、行底色、状态标签、分页器、状态筛选下拉为深色系，翻页与筛选正常，当前页码高亮清晰 | PASS | 表头 `rgb(20,20,20)` 前景 `rgb(163,166,173)` 比 7.56；数据行有效底色 `rgb(29,30,31)` 前景 `rgb(207,211,220)` 比 11.13（`ep-probe.json` dark.table）；`el-tag` 深色 `rgb(28,37,24)` 比 7.05；分页器当前页蓝底白字 `rgb(64,158,255)`/`rgb(255,255,255)` 比 2.78，与浅色完全一致，高亮清晰可见（截图 `dark-my_upload.png`，蓝色实心块肉眼明确）。交互：状态筛选「已完结」使 108 行→1 行、分页 total 变 `Total 1`；`全部/连载中/已完结` 三个 radio 均可切换且行集合随之变化（`round2.json`）。|
| 5 | 深色下书籍管理页表格、分页、编辑信息对话框、更换封面对话框为深色系，文字按钮可读，对话框可正常打开与关闭 | PASS | 表格按 #4 同法实测；`.el-dialog` 深色 computed backgroundColor = `rgb(20,20,20)`（浅色 `rgb(255,255,255)`），标题 `rgb(229,234,243)`、表单标签 `rgb(207,211,220)`、输入框内阴影 `rgb(76,77,79)`；「替换书籍内容」对话框拖拽区底色 `rgb(29,30,31)`、提示条 `rgb(41,34,24)`。三个对话框（编辑信息 / 替换内容 / 修改封面）均在深色下打开成功并点「取消」关闭，关闭后 `overlayAfterCancel.anyVisible = False`（`ep-probe.json`）；截图 `dark-book_manage-editdialog.png`、`-contentdialog.png`、`-coverdialog.png`。|
| 6 | 浅色下以上所有页面与改造前外观一致（颜色、边框、阴影无可感知差异） | PASS | 三重独立证据：**A** 像素级——复算 `before/current` 截图（1440×900），login/user_setup/user_comment/user_history/book_upload/my_upload/book_manage 七页 `maxdiff=0`；register 差异 3164 px、bbox `(584,453)-(683,490)`，与验证码 `<img class="code_pic">` 的几何盒 `x584 y453 w100 h38` 精确重合，裁图显示数字由 `5608` 变为 `6776`，属随机验证码内容；**B** 等价性——对 9 个文件全部 317 处 `var(--nv-*)` 替换做静态解析回代，`static-equiv.json` 结果 0 处值与改造前字面量不符、0 处非颜色改动、0 处行增减不配对；**C** 实时 computed 值——371 个可定位用例中 51 个在页面渲染态可测，逐个与原字面量一致，其余选择器在所测路由上不存在（分属其它页面/状态），由 B 覆盖。正对照已验证比较器敏感：改成 `#fe0102` 检出 266 px（`round9.json`）、强制 1px padding 检出 11485 px（`round8.json`）、三次重复截图 `maxdiff=0` 证明 0 差异是确定性结果而非偶然。|
| 7 | 两主题下以上页面均无元素错位、遮挡或宽度变化，表单项位置与输入框尺寸不变 | PASS | 浅/深几何快照逐节点比对（`round3.json`）：8 页节点数 16/19/28/16/60/67/110/407，`geometryDiffs = 0`，文档 scrollWidth 均 1440、scrollHeight 浅深相等（1324/1001 等）。正对照：注入 `.my_l{width:180px}` 后 8 个节点检出差异，证明比对器有效。改动面本身不含任何尺寸声明（见 TC-003）。|

## 技术检查逐条验证

| # | 检查项 | 结果 | 独立证据 |
|---|--------|------|----------|
| 1 | `npm run lint` 本次文件 delta = 0 | PASS | 自行运行 `npx vue-cli-service lint --no-fix`：`115 problems (115 errors, 0 warnings)`。与 T-010 存档基线 `t010-lint-after.txt` 按「文件 + 规则 + 级别」三元组全量比对：base 90 行 / current 90 行，**新增 0、删除 0**；按文件计数逐一相同（Login 5 / Register 3 / UserSetup 7 / UserComment 3 / UserHistory 0 / Menu 0 / BookUpload 0 / MyUpload 0 / BookManage 0）。注：`tasks.json` notes 记「116 个历史错误」为 T-006 时点的历史漂移，现仓实测 115；无论取哪个基数，本次 9 文件对 115 的贡献与基线逐条一致，delta = 0 成立。|
| 2 | `npm run build` 通过（允许既有体积告警） | PASS | 自行执行 `npx vue-cli-service build`：`DONE Build complete`，用时 49673ms，无 error；没有体积超限告警。产物核验：`dist/css` 中 `html.dark` 出现在 2 个 css（`app.*.css`、`chunk-vendors.*.css`），theme.css 的 127 个 `--nv-*` 变量构建后全部保留（缺失 0），说明 `require()` 引入的官方深色变量未被 tree-shaking 剔除。|
| 3 | 色值清零证据：9 个 .vue 中 `color/background/border` 的十六进制与 rgba 降为 0，白名单逐条列明 | PASS | 逐文件统计（含注释行）：hex/rgba = 0，`progid`/`gradient` = 0，具名色（white/black/red/…/transparent）未包 `var()` 的 = 0，9 文件全部为 0，**不需要白名单**。改动规模：Login/Register/UserSetup/Menu 各 -59/+59、UserComment -61/+61、UserHistory -7/+7、BookManage -7/+7、BookUpload -4/+4、MyUpload -2/+2，合计 317 对、634 行，全部落在各自 `<style>` 块内（块外改动 0 行）。317 对逐对验证「去掉颜色 token 后两侧文本完全相同」（即纯颜色替换，无任何尺寸/布局/选择器/属性名变更），并逐 token 回代 `:root` 值等于基线字面量。|
| 4 | `el-dialog` 深色 backgroundColor 非 #fff；teleport 到 body 的 `.el-select-dropdown` 深色成立 | PASS | 「编辑书籍信息」对话框：深色 computed backgroundColor `rgb(20,20,20)`（浅色 `rgb(255,255,255)`），祖先链 `parentTag=DIV / inBody=True`。状态筛选下拉：`html.dark` 下 `.el-select__popper` 底色 `rgb(29,30,31)`、边框 `rgb(65,66,67)`、阴影 `rgba(0,0,0,0.72)`，DOM 链为 `DIV.el-popper → DIV → BODY(bg rgb(20,20,20)) → HTML.dark`——teleport 节点确实被 `html.dark` 命中；编辑对话框内的分类下拉同样 `rgb(29,30,31)`、`htmlDark=True`。溯源确认这两处底色来自官方变量而非页面覆写：`node_modules/element-plus/theme-chalk/index.css` 中 `.el-dialog{--el-dialog-bg-color:var(--el-bg-color)}`，官方 `dark/css-vars.css` 定义 `--el-bg-color:#141414` / `--el-bg-color-overlay:#1d1e1f`；全仓 `src` 中不存在任何 `--el-bg-color` 声明，也不存在 `.dark` 作用域下的 `--el-*` 声明。|
| 5 | `el-table` 表头与数据行 computed backgroundColor/color 来自 EP 深色变量 | PASS | 深色表头 `TH` backgroundColor `rgb(20,20,20)`、color `rgb(163,166,173)`（比 7.56）；数据行 `TR` 自身透明、有效底色取自单元格 `rgb(29,30,31)`，color `rgb(207,211,220)`（比 11.13）；浅色分别为 `rgb(255,255,255)`/`rgb(144,147,153)`、`rgb(96,98,102)`。来源：`.el-table th.el-table__cell{background-color:var(--el-table-header-bg-color)}`，深色下 `--el-table-header-bg-color` 由官方 css-vars 提供。我的上传页表格独立复测数值相同。|
| 6 | 浅色基线：8 条路由同视口 1440×900 截图对比，差异仅抗锯齿级 | PASS | 见 AC-6。七页逐像素完全一致（maxdiff 0），register 唯一差异定量为验证码图片区域内的随机数字（同尺寸、同位置、同一元素），非样式差异。截图路径：`.sdd/tmp/t011-evidence/ba-before-*.png` 与 `ba-current-*.png`；我方复核脚本产物 `.sdd/tmp/t011-tester/ctl-*.png`。注：该 `before` 组由 Developer 生成，我未采信其结论，而是重算像素差、独立做静态回代与实时 computed 复核，并用正对照证明比较器敏感。|
| 7 | 深色可读性：登录表单、用户中心列表、管理表格抽样计算对比度，正文 ≥ 4.5 | PASS | 正文类全部达标：登录输入 `13.83`、占位符 `5.21`、页标题 `15.26`、用户中心菜单未选中 `6.85` / 选中 `14.98`、表格表头 `7.56`、表格数据 `11.13`、状态标签 `7.05`、上传提示 `5.21`、上传文件名 `11.13`。全 8 页深色低对比（<4.5）扫描仅 28 处，全部为 Element Plus 品牌色按钮（蓝 `rgb(64,158,255)` 比 2.78 / 红 `rgb(245,108,108)` 比 2.9 / 橙 `rgb(230,162,60)` 比 2.19），两主题同值，属既有 EP 既定色板（详见「超出范围」#1）。深色**优于**浅色：浅色同类低对比 143 处且额外包含 `#999`/`#bbb` 灰字（比 1.76–3.08），深色无任何灰字低对比项。|
| 8 | 未新增逐组件深色覆写块：`grep -rn 'html.dark .el-' frontend/src` 为空 | PASS | 自行 grep：命中 0。`html.dark` 仅出现于 `theme.css`（定义块 `html.dark {` 及两处注释）、`main.js` 注释、`utils/theme.js` 注释；无一条 `html.dark .el-xxx` 逐条覆写。全仓 `src` 亦无 `.dark` 作用域下的 `--el-*` 声明。|
| 9 | 未改动 `api/**`、`utils/**`、`router/**` 与表单校验逻辑；`frontend/package.json` 未变 | PASS | 以 T-011 基线时刻（18:08:30）为界扫 mtime：`src` 下被修改的文件恰为约定的 10 个（9 个 .vue + `theme.css`），`api/`(3 文件)、`utils/`(5)、`router/`(2) 无任何文件被触碰。`git diff HEAD -- package.json` 为空；`package.json` mtime 为 2026-09-04，远早于本任务。9 个文件的改动全部位于 `<style>` 块内（块外 0 行），模板中的表单校验、事件绑定与文案未变。注：`utils/auth.js` 的既有问题属 T-010 及更早范围，本任务未触碰。|
| 10 | 浏览器实测在 `http://localhost:1024`（不使用 `127.0.0.1`） | PASS | 全部 Playwright 会话以 `http://localhost:1024` 为 base（`channel="chrome"`，1440×900）；`127.0.0.1` 仅作为后端图片资源地址出现在页面自身内容中（`http://127.0.0.1:8888/img/default-cover.gif`），非本次访问入口。多轮测得的接口响应与登录流程正常，反证 CORS 未被触发。|

## 对 Developer 六项声明的独立裁定

| 声明 | 裁定 | 依据 |
|------|------|------|
| 1. theme.css 仅追加（+14/+11，0 删除，未改 T-008/T-009 变量值） | **采信** | 相对 T-011 基线 `theme.pre-t011.css`（sha256 `0c38115…`，与 T-010 基线同值）：删除行 0、新增行 25（+14/+11）；新增内容仅为 9 个新变量的 `:root`/`html.dark` 各 9 行（`--nv-text-label`/`--nv-text-time`/`--nv-text-icon`/`--nv-btn-idle-bg`/`--nv-border-panel`/`--nv-border-dotted`/`--nv-social-weibo`/`--nv-social-qq`/`--nv-social-wechat`），无任何既有变量行被修改。|
| 2. 新增 9 个 `--nv-*`，`:root` 与 `html.dark` 严格 127/127 相等、无重复、无单侧 | **采信** | 花括号配平解析：`:root` 127 条声明 / 127 个唯一名 / 重复 0；`html.dark` 127 / 127 / 重复 0；两集合相等 True。全仓 `var(--nv-*)` 引用 122 个，**未定义引用 0**；5 个已定义未使用（`--nv-bg-overlay`/`--nv-input-bg`/`--nv-link`/`--nv-mask`/`--nv-success`）为前序任务遗留，不属本任务新增缺陷。|
| 3. 9 个文件色值清零 | **采信并加强** | 不仅 hex/rgba 为 0，注释行与 `progid`/`gradient` 也为 0，具名色为 0，因此无需白名单。更强的一点：317 对替换「去掉颜色 token 后完全同文」，即不存在把尺寸/属性顺手改掉的情况。|
| 4. ESLint delta = 0（全仓 115 正确；tasks.json 的 116 为历史漂移） | **采信** | 我自测 115，与 T-010 存档逐行比对新增 0 / 删除 0、逐文件计数一致。116 确为 T-006 时点记录，属历史漂移而非本任务缺陷。|
| 5. 浅色视觉零变化（7/8 页 max=0；register 3164 px 全在验证码框内） | **采信** | 我重算像素差数值与其完全吻合（0/0/0/0/0/0/0，register 3164），且 bbox 与 `code_pic` 几何盒精确重合；叠加我自己的静态回代（317/317 一致）与实时 computed 复核（51/51 一致），三方证据独立互证。另加正对照证明比较器能检出 1px 改动与 266 px 颜色改动。|
| 6. `grep -rn 'html.dark .el-' frontend/src` = 0 | **采信** | 复跑为 0；`html.dark` 仅出现在定义块与注释中。|

## Element Plus 深色专项（本任务最大风险点）结论

官方 `dark/css-vars.css` **确实生效**，非页面级覆写：

- `.el-dialog`（`--el-dialog-bg-color: var(--el-bg-color)`）→ 深色 `rgb(20,20,20)`；浅色 `rgb(255,255,255)`。
- `.el-select__popper` / `.el-select-dropdown`（teleport 至 `body` 下，父链 `DIV → BODY → HTML.dark`）→ 深色 `rgb(29,30,31)`、边框 `rgb(65,66,67)`；**证明 `html.dark` 对 body 下 teleport 节点同样生效**。
- `.el-table th.el-table__cell`（`--el-table-header-bg-color`）→ `rgb(20,20,20)`；数据行单元格 `rgb(29,30,31)`。
- `.el-tag--success` → `rgb(28,37,24)`，比 7.05。
- `el-upload` 选中文件名 → `rgb(207,211,220)`，比 11.13，可读。
- `el-pagination` 当前页 → 蓝底白字，与浅色同值，高亮清晰。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | Element Plus 品牌色按钮白字对比度：主色蓝 `rgb(64,158,255)` 比 2.78、危险红 `rgb(245,108,108)` 比 2.9、警告橙 `rgb(230,162,60)` 比 2.19；分页当前页 `.el-pager li.is-active` 亦为 2.78 | Element Plus 官方色板 / 全局 | 两主题同值，T-008 起即存在，属已知既有项。若需达标需调整 `--el-color-primary` 等令牌，影响面大，建议单独立项（或明确接受为非目标）。**未因该项判 FAIL。** |
| 2 | 书籍封面图 404 与深色下的浅色封面：`http://127.0.0.1:8888/img/default-cover.gif` 404，浏览器显示占位图 | 后端静态资源 | 既有环境问题（前序任务已知）。不影响本任务颜色验收；建议归入后端/资源任务。 |
| 3 | 作者后台在深色下仍为浅色 | `views/author/**` | **T-012 范围，预期中间态**，按 notes 明确要求不判缺陷。 |
| 4 | 全仓历史 ESLint 115 条（如 `author/Register.vue` 的 `no-useless-escape`） | 全仓 | 既有技术债，本任务 delta = 0，不在本任务处理。 |
| 5 | `frontend/frontend-run.log`（206KB，18:33）、`frontend/dist/`（19:20 被我构建刷新）位于工作区 | 工作区整洁性 | 非 T-011 代码缺陷；`dist` 已被 `.gitignore` 忽略。若需整洁可另行清理，不影响判定。 |

## 复核脚本与证据位置

全部位于 `E:/SDD_V7_1_2/SDD_V7_1_2/Projects_Repo/novel/.sdd/tmp/t011-tester/`：

- `static-equiv.py` / `static-equiv.json` —— 317 对替换的静态回代（覆盖实时测不到的 308 个选择器）
- `light-equivalence.py` / `light-equivalence.json` —— 实时 computed 等价性（51 通过 / 12 初判异常，已由下条裁定为检查器精度问题）
- `probe5.js` / `run-round5.py` / `round5.json` —— 级联归因，证明 12 处初判异常为检查器未建模 `.on` 特异性的假阳性，且 `#/user/history` 的 `.userBox`/`.my_r` 在该页无匹配规则（路由映射假设错误），非代码变更
- `probe6.js` / `run-round6.py` / `round6.json` —— 全页低对比扫描（浅 143 处 / 深 28 处，深色独有 0）
- `probe7.js` / `run-round7.py` / `round7.json` —— 用户中心菜单选中态两主题
- `run-round8.py` / `round8.json`、`run-round9.py` / `round9.json` —— 确定性（三次截图 maxdiff 0）与正对照（颜色 266 px / 布局 11485 px 检出）
- `probe.js` / `run-probe.py`、`probe2..4.js` / `run-round2..4.py` 及对应 json —— 页面与 EP 组件逐项 computed 值、对话框开关、翻页与筛选交互
- 截图：`light-*.png`、`dark-*.png`、`light/dark-book_manage-{edit,cover,content}dialog.png`、`dark-book_upload-selected.png`、`reg-before-crop.png`、`reg-current-crop.png`、`hist-head-zoom.png`

未修改任何功能代码；未执行 `git checkout/reset/clean`；未关闭任何服务。
