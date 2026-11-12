# 测试报告：T-009 全局 CSS 变量化（base/main/book/about/user/read）

**测试时间**：2026-10-29 11:52–12:40（Asia/Shanghai）
**Tester Agent ID**：tester（SDD Harness V7.1）
**验证方式**：静态源码/哈希核验 + 独立重写注释感知色值扫描 + 变量等价性展开比对 + 真实 Chrome（Playwright channel=chrome）在 `http://localhost:1024` 实测
**独立复验脚本**（本次自行编写，未执行 Developer 的任何脚本）：`.sdd/tmp/t009-tester-scan/{colorscan2.py, varcheck.py, skeleton.py, colorequiv.py, commentcheck.py, propcheck.py, baseline2.js, pixdiff.py, dark.js, abtest.js, admin.js, layout.js, homefreeze.js}`
**证据产物**（日志 / JSON / 截图共 140 件）：`.sdd/tmp/t009-tester-evidence/`

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 独立证据 |
|---|------|------|---------|
| 1 | 浅色主题下首页、全部作品、排行榜、书籍详情、正文阅读、登录、注册、用户中心、上传图书、我的上传、书籍管理的观感与改造前一致：底色、文字色、边框、表头、按钮颜色均无可感知变化 | **PASS** | 基线对比零风险方案：不碰工作区，用 `git show HEAD:` 取 6 个 CSS 原文，在浏览器内**原地替换**已加载的同名 `<style>`（保持级联顺序），dev server 已把 `url(../images/*)` 重写为绝对/`base64`，我按 `url()` **出现位置**做同位置替换，避免资源失效干扰。10 条路由 `1440x900` 逐像素比对：**px=0 / max=0 / mean=0.0000，全部完全一致**（`.sdd/tmp/t009-tester-evidence/t009-pixel-diff.json`）。同时 `getComputedStyle` 26 个探针项（bg/fg/border/boxShadow/opacity）零差异（`t009-baseline-report.json`）。管理员三页独立实测浅色基线：`bodyBg=rgb(245,245,245)`、`.topMain=rgb(255,255,255)`、`el-table th=rgb(255,255,255)`、`el-table td=rgb(96,98,102)`（`t009-final-layout.json`） |
| 2 | 6 个全局样式文件中不再出现十六进制或 rgba 色彩值，色彩声明全部引用 `--nv-*` 变量（`transparent` 与背景图除外） | **PASS** | 自写 `/* */` 感知扫描（`colorscan2.py`）：在**注释剥离后**仅扫描声明值，含 CSS 命名色（`black/white/gray/…`，用 `(?<![\w-])` 尖括号边界避免误匹配 `--nv-accent-cyan`）。结果：**base/main/book/about/user/read 有效色值全部 = 0**；`var(--nv-*)` 引用数 100/84/58/13/2/0。残余 19 处字面量全部位于 `/* */` 内，并用 HEAD 对比验证「注释内色值多重集完全相等」（`commentcheck.py`：`ALL_COMMENT_LITERALS_PRESERVED = True`），即全是改造前就存在的历史注释，非 Developer 新增 |
| 3 | 深色态下，纯由全局样式驱动的区域（顶部搜索栏与顶栏底色、主导航条、页脚版权栏、页面外层底色、书籍卡片边框与文字）变为深色系且文字可读 | **PASS** | 真实点击 `.theme_switch` 后 `className=""→"dark"`。computed backgroundColor：`body=rgb(20,20,20)` lum=0.0070、`.topMain=rgb(29,30,31)` lum=0.0129、`.mainNav=rgb(29,30,31)` lum=0.0129、`.footer=rgb(29,30,31)` lum=0.0129 —— **均 < 0.3**。文字可读性（WCAG 相对亮度对比度）：顶栏文字 13.83、导航链接 16.70、页脚版权 5.21、搜索输入 13.83、书籍卡片标题 15.26、卡片简介 6.78 —— **全部 ≥ 3**。书籍卡片边框 `borderTopColor` 随主题由白转容器色。10 条路由深色均正常渲染（`t009-dark-routes.json`），管理员三页深色 `bodyBg=rgb(20,20,20)`、`topMain=rgb(29,30,31)` |
| 4 | 两种主题下所有页面的元素位置、间距、字号、滚动行为均未改变（只变颜色，不变布局） | **PASS** | `getBoundingClientRect()` 全量指纹（x/y/w/h + fontSize/fontWeight/lineHeight/padding/margin/display/position/borderWidth/borderRadius/overflow/textOverflow/whiteSpace）对比 light vs dark，13 条路由（含管理员三页）**diffRows=0、docH 相同、节点数相同**。首页唯一非零来源为轮播自动切换：定位到差异行全部是 `.scBigImg dd.on` / `.scSmallImg li.on` 的类名迁移（`inSlider=true` 6/6），**冻结定时器后 diffRows=0**（`homefreeze.js`：`RESULT: PASS home layout identical when carousel frozen`）。另：属性序列与 HEAD 逐条比对完全一致（base 418 / main 551 / book 393 / about 65 / user 14 / read 1 条声明），无尺寸/布局属性增删 |
| 5 | `easyui.css` 与 `layer.css` 的内容未被改动 | **PASS** | `git diff --numstat HEAD` 对 `easyui.css`/`layer.css`/`read.css` **均为空**；LF 归一化 sha256 与 `git show HEAD:` 完全相等（`easyui 55c3508…`、`layer 7ef256f…`、`read c53f5dc…`）。与 T-008 基线快照 `t008-before.sha256`/`t008-final.sha256` 逐字节一致（`e065aec…`/`7ef256f…`）。工作区 sha256 差异仅为 `core.autocrlf=true` 的 CRLF 换行，`git diff` 无内容变化 |

## technicalChecks 逐条验证

| # | 检查项 | 结果 | 独立证据 |
|---|--------|------|---------|
| 1 | `npm run lint`：本次修改文件 ESLint delta = 0（附核查证据） | **PASS** | 自行全量跑 `npx vue-cli-service lint --no-fix`：**115 errors / 0 warnings**（`tasks.json` notes 里「116」是旧口径，与 T-008 实测的 115 一致；Developer 报 115 正确）。本次仅改 6 个 `.css` 文件，ESLint 配置不覆盖 CSS，**不可能产生 delta**；6 个文件对 lint 输出零贡献，delta = 0 成立 |
| 2 | `npm run build` 通过，构建产物 CSS 中 `--nv-` 变量定义与引用均存在 | **PASS** | 自行 `rm -rf dist && npm run build`：exit=0，`DONE Build complete.`，无 error/failed 关键字，仅有既有 chunk 体积列表。解析产物 `app.eb731031.css`：`:root` 内 **93 个 `--nv-*` 定义**、`html.dark` 内 **93 个定义**，集合相等（`only root=[]`、`only dark=[]`）；全 dist CSS 汇总定义 93 个、引用 88 个，**引用缺定义 = ∅**。`--nv-scrim:#000` 与 `html.dark{...--nv-scrim:#000}` 均落盘 |
| 3 | 色值清零证据：6 个文件色值 grep 从 109/92/58/13/2/0 降为 0 | **PASS** | 自写扫描（非简单 grep）：剥离注释后声明值有效色值 **0/0/0/0/0/0**。原始（含注释）计数 base=9、main=9、book=1、about=0、user=0、read=0 —— 这 19 处**全部**落在历史注释内，且与 HEAD 注释内色值多重集完全相等。注意：Developer 声称「残留 9/9/1 全在历史注释」与我的实测**一致**，已独立核实 |
| 4 | `easyui.css`、`layer.css` 的 sha256 与改造前一致 | **PASS** | 见 AC5。与 T-008 现场快照 `t008-before.sha256`（`easyui e065aec…`、`layer 7ef256f…`）逐字节相同；`git diff HEAD` 为空。`read.css` 同样零改动 |
| 5 | 浅色视觉基线：改造前后同一路由同一视口 1440x900 截图对比，允许抗锯齿级误差；截图路径附报告 | **PASS（超出要求：0 像素差异）** | 逐像素：home/bookclass/book_rank/book_detail/chapter_list/read/login/register/news/feadback **全部 px=0、max=0、mean=0.0000**，不是「抗锯齿级」而是**完全一致**。噪声基线（同一份 CSS 连拍两次）在 book_detail/chapter_list/read 存在 16716~50148 px 波动（封面/图片异步加载），说明本比对方案确实能捕捉动态噪声，而当前 vs 基线仍是 0。截图：`.sdd/tmp/t009-tester-evidence/t009-bl2-{route}-cur.png` 与 `t009-bl2-{route}-base.png`（含连拍噪声对照 `-base-t2.png`） |
| 6 | 深色实测（localhost:1024）：`.topMain`/`.mainNav`/`.footer`/`body` computed backgroundColor 相对亮度 < 0.3，文字色亮度差可读 | **PASS** | 0.0070 / 0.0129 / 0.0129 / 0.0129；文字对比度 5.21~16.70，全部 ≥ 3。证据 `.sdd/tmp/t009-tester-evidence/t009-current-dark-state.json`、`t009-dark-routes.json`、`t009-dark-evidence.json` |
| 7 | `npm run serve` 与浏览器实测均在 `http://localhost:1024`，不使用 `127.0.0.1` | **PASS** | 自行 `powershell start-novel.ps1` 起服务，`netstat` 确认 1024/8888 监听；**全部 Playwright 脚本 `BASE = 'http://localhost:1024'`**，无一处 127.0.0.1。产出截图 `.sdd/tmp/t009-tester-evidence/t009-final-dark-{route}.png` |

## A / B 两点核查结论

### A. `book.css` `.maskBox`：`background: black` → `var(--nv-scrim)`（`--nv-scrim: #000000`，深浅一致）

**结论：正确且等价，深色下遮罩仍正常。**

- `black` 是 CSS 命名色，等价于 `#000`/`#000000`（`rgb(0,0,0)`），二者**完全等价**，不存在色值差。浏览器实测：light 与 dark 下 `.maskBox` computed `backgroundColor` 均为 `rgb(0, 0, 0)`，`--nv-scrim` 在 `html.dark` 中亦为 `#000000`（`t009-ab-evidence.json`）。
- 深色下遮罩是否仍「正常」：该规则依赖 `opacity: 0.3`（配合 `filter: alpha(opacity=30)` 老 IE 兜底）把黑底压成半透明，黑色遮罩叠在深色页面上仍然变暗，语义正确；若改成浅色（如深色主题换白底）反而会让遮罩「提亮页面」，视觉上错误。因此深色保持 `#000000` 是**正确选择**，与 EP 自身 `--el-mask-color: rgba(0,0,0,0.8)` 的深色取法一致。
- 补充观察：该 `.maskBox` 的**全局规则**（book.css）存在，但 `BookContent.vue` 内的同名 `.maskBox` 是 `scoped` 且模板中**无对应元素渲染**（`grep` 全仓库只有内联 `$('.maskBox,...').hide()` 与 scoped 样式，无 `class="maskBox"` 标签），因此该规则当前是**死样式**。这属于既有结构（HEAD 原样），与本次变量化无关，不作为 FAIL 依据。

### B. `main.css` `.replay_text`：`box-shadow: 0 0 4px 2px hsla(0,0%,92%,.35)` → `var(--nv-shadow-inset)`

**结论：浅色完全等价；深色变成暗色阴影不会造成可读性问题。**

- **浅色等价**：`hsla(0,0%,92%,.35)` 的浏览器 computed 值为 `rgba(235, 235, 235, 0.35)`（sRGB 92% on 0° → 235），与 theme.css `--nv-shadow-inset: hsla(0, 0%, 92%, 0.35)` 逐字一致。实测 light `boxShadow = "rgba(235, 235, 235, 0.35) 0px 0px 4px 2px"`，与改造前完全一致（也印证逐像素比对 `main.css` 零差异）。
- **深色合理性**：该属性是 textarea 的**外扩内发光**（`0 0 4px 2px`，无 inset 关键字，实际向外扩散）。深色取 `hsla(0,0%,0%,0.35)` = `rgba(0,0,0,0.35) 0px 0px 4px 2px`。在深色页面（`body=rgb(20,20,20)`，textarea 自身 `rgb(59,59,59)`）上，一个 35% 不透明度的黑色 4px 光晕是**深色界面上常见的「凹陷/聚焦」表达**，不会盖住文字：光晕位于盒子外沿 0~6px，而 padding 为 10px，文字区与光晕**不重叠**。
- **可读性实测**：深色 `.replay_text` 文字 `rgb(229,234,243)` on `rgb(59,59,59)`，**对比度 9.28**，远超 WCAG AA 4.5。浅色时为 `rgb(51,51,51)` on `rgb(255,255,255)`（对比度 12.63）。因此深色改为黑色阴影**不构成可读性风险**。
- 小提示（不影响判定）：`--nv-shadow-inset` 的命名带 "inset"，但实际语义是外发光；命名瑕疵属规范/可读性问题，应在 Tester PASS 后的 code-review 阶段评估，不构成本次 FAIL。

## 对 Developer 声明的采信情况

| Developer 声明 | Tester 结论 | 依据 |
|---|---|---|
| 「改动 base/main/book/about/user.css 五个文件 + theme.css 扩展变量；read.css 未改（0 处色值）」 | **采信** | 属性序列与 HEAD 逐条一致；`read.css` git diff 为空；变量引用数与文件体积吻合 |
| 「有效色值（注释外）清零」 | **采信并独立复现** | 自写注释感知扫描，6 个文件有效值 = 0 |
| 「残留 9/9/1 处全在历史注释内」 | **采信并加强验证** | 不仅确认在注释内，还证明与 HEAD 注释内色值多重集**完全相等**（非新增注释），且全部为旧的「注释掉规则 / 注掉的 background」 |
| 「浅色观感逐像素一致」 | **采信并强化** | 我做到 10 路由 **0 像素差异**（比「逐像素一致」更强的证据：完全相等而非近似） |
| 「全仓 115 errors（notes 中 116 为旧口径）」 | **采信** | 实测 115，与 T-008 基线一致 |
| 「skeleton diff 仅颜色不同」 | **采信并为独立结论** | 我用「展开 `var()` → 颜色规范化 → 位置/结构比对」两路独立验证：骨架串一致 + 声明属性序列一致 + 颜色 RGBA 等价 |

## 发现的问题

无 T-009 范围内缺陷。测试过程中我自己的探针有 4 次判 FAIL，复核后全部定性为**测试脚本缺陷**而非代码问题，已告知并修正：

1. `contrast topMain / bookShelfLink` FAIL —— 我给 `topMain` 传了 `null` 前景色，且 `.sj_link` 在 `Top.vue` 中已被 HTML 注释掉，选择器不存在。
2. `layout identical` FAIL —— 首页轮播 2s 自动切换，`dd.on`/`li.on` 类名迁移导致 6 行差异；冻结定时器后 diffRows=0。
3. `#/chapter_list/1`、`#/login` layout FAIL —— 前者为异步章节列表加载未完成，后者为上一次操作残留的 `el-message` 提示条；稳定化重试并排除 `.el-message` 后 diffRows=0。
4. `.maskBox` / `.items_txt h3` 元素缺失 —— `.maskBox` 无渲染元素（死样式，既有）；卡片标题实际是 `h4` 非 `h3`。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | `BookManage.vue` 深色下表格正文仍为白底（`.el-table` 单元格），页面内 `background: #fff` / `color: #333` 为 scoped 硬编码 | `frontend/src/views/BookManage.vue`（第 500/514/536/543/554/565 行） | 属页面级变量化，T-009 只负责全局骨架，AC3 明确限定「纯由全局样式驱动」的区域；留给 T-013 统一验收 |
| 2 | `BookContent.vue` 的 `.maskBox` 全局规则无对应 DOM，属于死样式 | `frontend/src/assets/styles/book.css` + `BookContent.vue` | HEAD 原样，非本次引入；建议 code-review 阶段评估是否保留（任务明确要求「不要删除注释掉的旧规则」） |
| 3 | `--nv-shadow-inset` 命名带 `inset` 但语义是外发光 | `frontend/src/assets/styles/theme.css:145,277` | 命名瑕疵，不影响视觉；建议 code-review 阶段评估 |
| 4 | `--nv-mask`（`rgba(0,0,0,.3)` / 深色 `.7`）在全仓库无任何引用，是 T-008 遗留的未使用变量 | `frontend/src/assets/styles/theme.css:53,187` | 不属于 T-009 改动；建议 code-review 或后续清理任务处理 |
| 5 | `utils/auth.js` 无 try/catch（改造前既有） | `frontend/src/utils/auth.js` | 已知既有问题，与 T-008 报告一致，不重复计 |
| 6 | 图片 404（`/localPic/**`、`/images/default.gif`）；深色下书籍封面仍白底（文案烧在图里） | 后端静态映射 / 图片资源 | 已知既有问题，留待 T-010~T-013 |

## 架构/结构侧额外核验（非强制，供参考）

- `theme.css`：`:root` 93 项、`html.dark` 93 项，**集合完全相等**，段内无重复名；6 个全局 CSS 引用的 88 个不同变量**全部有定义**（`undefined refs: NONE`）。
- 6 个全局 CSS **无任何 `html.dark .xxx` 局部覆写块**，主题切换完全走变量，符合任务「不得新增 html.dark 局部覆写」的约束。
- 6 个文件无任何非 `--nv-` 前缀的自定义属性，无新增颜色常量。
- 声明属性序列与 HEAD 完全一致（无 width/height/margin/font-size 等布局属性增删），证明「只变颜色，不变布局」。

## 运行与清理

- 本次临时启动：MySQL(3306)、Redis(6379)、后端 jar(8888)、dev server(1024)，验证结束已用 `stop-novel.ps1` 关闭并确认端口释放。
- 临时文件统一在 `.sdd/tmp/t009-tester-scan/`（复验脚本 + `head/` 下的 git HEAD 基线副本）与 `.sdd/tmp/t009-tester-evidence/`（日志 / JSON / 截图 140 件）；未污染项目根与 frontend 根（frontend 根下仅有改造前就存在的 `frontend-run.log` / `frontend-run.err.log`）。
- **全程未执行 `git checkout` / `git reset` / `git clean`**，工作区 T-008/T-009 改动完整保留；基线对比采用「运行期内存替换 `<style>`」的零风险方案。
