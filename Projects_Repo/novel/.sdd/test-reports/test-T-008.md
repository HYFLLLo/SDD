# 测试报告：T-008 主题基础设施与切换机制

**测试时间**：2026-10-29 10:24–11:05（Asia/Shanghai）
**Tester Agent ID**：tester（SDD Harness V7.1）
**验证方式**：静态代码/哈希核验 + 独立重跑 `npm run lint` / `npm run build` + 真实 Chrome（Playwright channel=chrome）在 dev（localhost:1024）与 prod（dist 静态服务 127.0.0.1:1031）双环境实测
**独立复验脚本**：`.sdd/tmp/t008-tester-basic.js`、`t008-tester-states.js`、`t008-tester-prod.js`、`t008-tester-resilience.js`、`t008-tester-final.js`、`t008-tester-recheck.js`、`t008-tester-webpack/run.js`、`t008-tester-filescan.py`（均为本次自行编写，未直接采信 Developer 脚本断言）

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 独立证据 |
|---|------|------|---------|
| 1 | theme.css 同时存在 `:root` 与 `html.dark` 两套取值，变量统一 `--nv-` 前缀，同名语义只有一个变量 | PASS | 脚本解析：`:root` 25 个、`html.dark` 25 个，两段**集合完全相等**（`only in root = ∅`、`only in dark = ∅`），各段内重复名 = ∅；全文件无任何非 `--nv-` 自定义属性。浅色值逐项对照改造前 CSS 实证：`#f5f5f5`(base.css:8 body)、`#333`、`#404040`、`#666`、`#999`、`#e0e0e0`/`#eaeaea`/`#eee`、`#f80`(base.css:104)、`#f70`、`#ff7800`、`#ff4040`/`#ed4259`/`#f65167`、`#66d65e`(Menu.vue:213)、`#f6f6f6` 均在源码中存在原始出处。深色段采用 EP 官方色阶 `#141414`/`#1d1e1f`/`#e5eaf3`/`#cfd3dc`/`#4c4d4f`/`#414243`/`#363637`，与 `node_modules/element-plus/theme-chalk/dark/css-vars.css` 逐值一致 |
| 2 | 清空存储首次打开无 `dark` class，外观与改造前一致（默认浅色、不跟随系统） | PASS | dev：`localStorage.clear()` + reload 后 `documentElement.className=""`、`novel-theme=null`。`body` 底色实测 `rgb(245, 245, 245)`、`.topMain` 背景白 + 高度 92px、`.mainNav` 背景 `rgb(255,136,0)` 白字、`.user_link` `rgb(64,64,64)` —— 均为改造前硬编码基线。另建 `colorScheme:'dark'` 的浏览器上下文，OS 深色偏好下 `className` 仍为 `""`，确认**不跟随系统** |
| 3 | 点击导航栏图标 `<html>` 立即增加 `dark`，图标换反向；再点移除并换回 | PASS | dev：点击后 `className: "" → "dark"`，SVG path 由 Moon `M240.448 240.448a384...` 切为 Sunny `M512 704a192 192 0 1 0...`；`style.colorScheme` 变 `dark`；`title`/`aria-label` 由「切换为深色主题」变「切换为浅色主题」。再点：`className=""`、图标回 Moon。二次点击后 `localStorage` 写回 `"light"`（`t008-tester-final.log`：`{"cls":"","stored":"light","cs":"light"}`） |
| 4 | 主题写入本地存储；刷新后图标与 class 一致，且不先浅后深 | PASS | 写入：切深色后 `novel-theme="dark"`；reload 后 `className="dark"`、图标仍 Sunny、`novel-theme="dark"`。首帧量化（dev）：`first-paint=208ms`，`dark` class 在 **182.6ms** 生效（领先 25.4ms），DCL 快照(189.7ms)已含 dark；`#app` children=0 的最早快照(33.3ms)之前无可见内容。prod 同样：`first-paint=128ms`，dark 于 **97.4ms** 生效 |
| 5 | 三种登录态都有入口、不挤压文字、顶栏高度不变 | PASS | 未登录：`text="登录注册"`；普通用户（真实 token，去掉 admin 标记，Navbar 无「书籍管理」佐证状态区分）：`text="普通测试用户退出"`；管理员（**真实 UI 登录 admin/admin，后端返回 code=00000**，Navbar 出现「书籍管理/我的上传」）：`text="admin退出"`。三态 `.topMain` 高度均 = 92px、`.theme_switch` count=1、DOM 顺序在 `.user_link` 之前、同排居中差 < 4px、无横向溢出。位移量化：隐藏图标后原文字宽度 110px → 110px **不变**，整体右移 40px（= 图标 20px + margin-left 20px），仅为图标预留位，未挤压文字 |
| 6 | 深色态 Element Plus 组件（el-dialog / el-message）底色为深色系，证明官方深色变量生效 | PASS | dev：`el-message` 底色 `rgb(254,240,240)` → 深色态 `rgb(43,29,29)`（EP `--el-color-danger-light-9` 深色阶）；`:root` 上 `--el-bg-color=#141414`、`--el-color-primary-light-7=#213d5b`、`--el-text-color-primary=#e5eaf3`。真实 admin 登录后打开「我的上传 → 改作者」`el-dialog`：`background rgb(20,20,20)`、标题 `rgb(229,234,243)`（截图 `.sdd/tmp/t008-tester-myupload-dark.png`）。prod 复验 `el-dialog`/`el-input`/`el-form label`/`el-button` 同样正确 |

## technicalChecks 逐条验证

| # | 检查项 | 结果 | 独立证据 |
|---|--------|------|---------|
| 1 | `npm run lint` 通过口径「本次新增/修改文件 ESLint 错误数 = 0」，需 delta 证据 | PASS | 自行全量跑 `npx vue-cli-service lint`：**115 errors**（Developer 记录的 116 是含已删 `yarn.lock.bak` 前后的口径差异，本次实测基线=115）。单独跑本次 3 个 JS/Vue 文件得 3 errors，全部为**改造前就存在**的同名同位置错误：`Top.vue:58 'onMounted' 未使用`、`Top.vue:64 'Top' 非多词`、`main.js:28 'Loading' 非多词`。用 `git show HEAD:` 取改造前版本放入临时目录单独 lint，得到**完全相同的 3 条**——即本次 delta = 0。`theme.js` 与 `theme.css` 零错误 |
| 2 | `npm run build` 通过 | PASS | 自行 `rm -rf dist && npm run build`：exit=0，`DONE Build complete`，仅既有 chunk 体积告警。**我的 dist 与 Developer 的 dist `diff -r` 零差异**（逐字节一致，`t008-tester-dist-diff.txt` 0 行） |
| 3 | `npm run serve` 后 localhost:1024 可访问（非 127.0.0.1） | PASS | 自行启动 dev server，`curl http://localhost:1024/` → 200；全程浏览器只访问 `http://localhost:1024` |
| 4 | 真实浏览器：清空→无 dark→点击→含 dark→刷新→仍含且存储=dark→再点→light | PASS | `t008-tester-basic.js` / `t008-tester-final.js` 全链路实测，21/21 + 相关项全 PASS；日志与断言逐条见上表 #2#3#4 |
| 5 | 首帧无闪烁：预置 dark 后加载，`domcontentloaded` 时刻已带 dark | PASS | dev DCL 快照 `{t:189.7, cls:"dark"}`；更强判据（dark 生效时刻 ≤ first-paint）也满足：dev 182.6ms ≤ 208ms、prod 97.4ms ≤ 128ms |
| 6 | 构建产物 CSS 含 `html.dark` 深色变量，证明 `theme-chalk/dark/css-vars.css` 进入产物 | PASS（并纠正证据口径） | **不采信「grep html.dark」**——`theme.css` 自己也有该选择器。改用 EP 独有值：`chunk-vendors.ee4b1701.css` 含 `--el-color-primary-light-7:#213d5b`、`--el-bg-color:#141414`、`--el-text-color-primary:#e5eaf3`、`--el-bg-color-overlay:#1d1e1f`、`--el-border-color:#4C4D4F`，以及 `html.dark .el-card`/`.el-button`/`.el-empty` 规则；sourcemap `sources` 明确列出 `webpack://novel-front-web/./node_modules/element-plus/theme-chalk/dark/css-vars.css`。同时 `app.b5830e0f.css` 只含 `--nv-*` 版本，两者清晰可分 |
| 7 | `frontend/package.json` dependencies/devDependencies 未新增条目（逐字一致） | PASS | 自行 `sha256sum package.json` = `3728bb18...d9706c`，与改造前快照 `t008-before.sha256` 同值；`git diff HEAD -- package.json` 为空。`package-lock.json` 也不在快照中（未新增） |
| 8 | 改动文件仅 theme.css(新)、theme.js(新)、main.js、Top.vue；`views/**`、`api/**`、`router/**`、`utils/auth.js` 未改 | PASS | 自行重算 `sha256sum -c t008-before.sha256`：**只有 `Top.vue`、`main.js` 两个 FAILED（即被改）**，其余 77 个基线文件全部 OK（含全部 `views/**`、`api/**`、`router/index.js`、`utils/auth.js`、`utils/index.js`、`easyui.css`、`layer.css`、base/main/book/read/user/about.css）。目录比对新增文件仅 `theme.css`、`theme.js`（其余为 `.env.*`/`vue.config.js` 等 9/4 创建且未改动的历史文件）。mtime 复核：受保护文件最近修改时间为 2026-10-21，均早于 T-008（10-29） |

## 对 Developer 声明的采信情况

| Developer 声明 | Tester 结论 | 依据 |
|---|---|---|
| 「Element Plus `sideEffects: "theme-chalk/*.css"` 不匹配 `theme-chalk/dark/` 子目录，生产构建会把 `import` 剔除」 | **采信并实证** | 读取 `element-plus/package.json`：`sideEffects: ["dist/*","theme-chalk/*.css","theme-chalk/src/*.scss",...]`；用 webpack 内部 `glob-to-regexp` + `SideEffectsFlagPlugin` 同参数复现：`theme-chalk/*.css` 生成 `^theme-chalk/([^/]*)\.css$`，`theme-chalk/dark/css-vars.css` **不匹配**。进一步构造最小 webpack 生产构建对照：`import` 入口产物 109 字节、无任何 EP 深色规则；`require` 入口产物 9716 字节、含 `html.dark .el-card` 与 `--el-bg-color:#141414`（脚本 `.sdd/tmp/t008-tester-webpack/run.js`）。**该说法成立** |
| 「dev 一直正常、prod 曾失效」 | 采信（改用 `require` 后 dev/prod 均已正常） | 本次 dev 与 prod 双向实测，EP 深色变量均生效，行为一致 |
| 「29/29 通过」等自测结论 | **不采信，已独立重跑** | 全部断言由我自行编写；Standard 6 的「grep `html.dark`」口径被我认为不足，已替换为 EP 独有变量值 |
| 「首帧无闪烁」 | 采信（有量化证据） | dev 182.6ms vs first-paint 208ms；prod 97.4ms vs 128ms；最早快照 `#app` children=0 时无可见内容 |
| 「`utils/auth.js` 无 try/catch 是既有缺陷，不在本次范围」 | 采信为既有缺陷 | 实测全部 localStorage 禁用时 `Top.vue` setup 抛 `SecurityError`（`[观察] ... pageErrors=["SecurityError: storage disabled"]`）；`theme.js` **自身**只对 `novel-theme` 键抛错时页面完整渲染、无未捕获异常、点击仍可切换（仅会话内生效）。该缺陷确在 T-008 允许改动文件之外，不作为 FAIL 依据 |

## 发现的问题

无 T-008 范围内的缺陷。测试过程中我自己的两条初版断言（导航链接颜色、图标颜色）被判 FAIL 后复核为**测试预期写错**而非代码问题，已排除：
- 导航链接：改造前 `base.css:106` 本就是 `.mainNav{background:#f80}` + `color:#fff`，实测 `rgb(255,136,0)`/`rgb(255,255,255)` 与基线一致；
- 图标颜色：初测因鼠标停在图标上命中 `:hover`，非 hover 态实测 `rgb(64,64,64)`（与 `.user_link` 同色），hover 态 `rgb(255,119,0)`（`--nv-brand-hover`，设计意图），深色态 `rgb(207,211,220)`（`--nv-text-regular` 深色值生效）。

## 超出范围发现（不影响当前任务判定）

| # | 问题 | 所属模块 | 建议处理方式 |
|---|------|---------|------------|
| 1 | `utils/auth.js` 的 `getToken/getNickName` 无 try/catch，全部 localStorage 禁用（隐私模式/禁用存储）时 `Top.vue` setup 抛 `SecurityError` 中断渲染 | `frontend/src/utils/auth.js` | 既有缺陷，不在 T-008 4 个允许文件内；建议单独建任务补容错 |
| 2 | `Login.vue` 深色态下 `el-message` 文字仍为 `rgb(51,51,51)`（深底深字，对比度偏低） | `frontend/src/views/Login.vue`（el-message 的 `--el-message-text-color` 未随深色覆盖，EP 2.2.0 该变量默认取 `--el-text-color-regular` 外的固定值） | 属页面/EP 组件自身样式，本任务「不验收深色全站外观」，留待 T-009~T-013 页面变量化处理 |
| 3 | 页面图片资源大量 404（`/localPic/**`、`/images/default.gif`） | 后端静态映射/种子数据 | 改造前既有，与 T-008 无关（T-006 已记录 `/localPic` 坏链） |
| 4 | `frontend/frontend-run.log` / `.err.log` 留在 frontend 根目录 | 环境产物 | 非本次引入（10-29 09:09 既有），建议加入 `.gitignore` 或清理 |

## 运行与清理

- 启动的进程：dev server(1024)、`python -m http.server` 服务 dist(1031)、MySQL(3306)、Redis(6379)、后端 jar(8888)，全部为本次测试临时启动，验证结束已全部 `taskkill` / `mysqladmin shutdown`，端口 1024/1031/8888/6379/3306 已确认释放。
- 临时脚本、日志、截图统一放 `.sdd/tmp/t008-tester-*`；`tasks.json` 改动前的备份为 `.sdd/tmp/t008-tester-tasks.bak.json`。
