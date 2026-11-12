# 工作日志

> 由 Orchestrator 维护。记录项目开发、测试、修复和 blocked 状态。

---

## 2026-11-05 — 源码恢复与 P0 整改

### 起点

发行物只有 PyInstaller 单文件 exe（Python 3.8）+ workspace + 两份文档，
仓库内无源码、无依赖清单、无测试、无版本历史。

### 源码恢复

- 从 exe 归档提取 22 个模块的 3.8 pyc，重建成可维护源码（`app/`）。
- 装配工具链：`tools/recover/assemble.py`（反编译 + 手写片段覆盖）。
- 疑难函数逐条对拍原始字节码，修正反编译缺陷（not/and 混淆、return 与 append 错误缩进、
  `continue` 被拍平成 `pass` 等），手写片段在 `tools/recover/manual/`。
- 最终 `verify_bytecode.py`：623 个函数，exact 372 / near 19 / diff 232 / missing 0。
- 核心函数（parse_result、comparison.compare、_metrics_single、normalize_config 等）
  已用同类输入对原始 pyc 与恢复源码做行为差分，结果一致。

### P0 整改

1. **工程化**：新增 `requirements.txt`、`requirements-dev.txt`、`pyproject.toml`、
   `multimodaltest.spec`、`.gitignore`、`README.md`；`git init` 并首次提交。
   PyInstaller 实际构建成功，`dist/多模态测试平台.exe` 启动后首页 200。
2. **测试**：新增 5 个测试文件 + conftest，`pytest` 结果 **73 passed**。
3. **安全**：`app/security.py` 提供 Host 白名单、CSP、nosniff、Referrer-Policy；
   前端移除 7 处内联 onclick、4 处内联 onerror、3 处 `javascript:` URL。
   源码与打包 exe 均实测：正常 Host 200 且三头齐全，`Host: evil.com` 返回 400。

### 顺带修复的真实缺陷

- `app.main.api_extract_fields`：调用 `flatten_paths(d)` 缺参、`return` 缩进错误。
  原始字节码确认签名为 `(obj, max_depth=4, max_items=300)`，已补手写片段并回归验证。

### 未完成（P1 / 需业务确认）

- `workflow._execute`、`judge_one` 等长流程为手写重建（near 0.95–0.99），需原厂或业务方确认。
- 前端单文件 3,900 行、107 处 `innerHTML`、19 处 `confirm()`；无障碍、移动端、骨架屏。
- 后端 72 组路由无鉴权（本地单机场景，风险可控，但不是零风险）。

## 2026-11-05 — P1 整改（可访问性 / 交互 / 反编译缺陷）

### 目标

P0 已让项目「可构建、可测试、有安全底线」。P1 处理可用性与恢复质量：
前端无障碍与原生弹窗、长任务进度，以及恢复源码中残留的反编译控制流缺陷。

### P1 前端可访问性与交互

- 原生弹窗全部替换：`confirm()` 19 处、`prompt()` 5 处清零，改为 `confirmDlg()` / `promptDlg()`
  （Promise 形式，站内样式，危险操作二次确认）。
- `openDlg()` 重写：`role="dialog" aria-modal="true"`、`aria-labelledby` 指向标题、
  Tab 焦点陷阱（`trapDlgFocus`）、Esc 关闭、关闭后焦点归还触发元素。
- 控件命名：页面几乎全部由模板字符串渲染，逐处补 `for/id` 不现实，改为渲染后调用
  `enhanceA11y()` + `MutationObserver` 兜底——把相邻 `<label class="f">` 与控件建立 `for/id`，
  无名控件按 placeholder/title/所属卡片标题生成 `aria-label`。
  期间发现并修正一个自身缺陷：会误把包裹复选框的 label 绑定给旁边的输入框。
- 新增「跳到主要内容」`.skip-link`、`<main id="app" tabindex="-1">`、全局 `:focus-visible`、
  `prefers-reduced-motion`、窄屏表格滚动容器；toast 补 `role=status|alert` + `aria-live`。
- 长任务进度：`progressBar()` 输出 `role="progressbar"` + 百分比文案 + 失败数，
  运行列表与裁判面板均已接入。

### P1 反编译缺陷修复（对照原始 Python 3.8 字节码）

先修对拍工具：`verify_bytecode.py` / `check_module.py` 原先有 `from __future__ import annotations`，
`compile()` 继承该 flag 会把注解读成字符串制造假差异，改为 `dont_inherit=True` 后
exact 从 545 提升到 591，证明大量「差异」只是工具噪声。

随后逐个函数修复真实缺陷（每项均对拍到 1.0000）：

| 位置 | 缺陷 | 用户可见后果 |
|------|------|--------------|
| `prompts.create_prompt` | 默认值丢失 | 示例项目创建抛 `TypeError`，永远建不起来 |
| `prompt_profiles.save_profile` | 写盘逻辑嵌进 `else` | 新建模板必 `UnboundLocalError` |
| `annotate.draw_objects` | 标签绘制嵌进 `if show_fields` | 不显示额外字段时渲染崩溃 |
| `stats.run_stability` | 类别标签初始化在逐样本循环内 | 稳定性统计错乱 |
| `trial._pick_images` | `assert` 代替显式抛错 | 优化后 `-O` 运行丢失校验 |
| `workflow._execute` | 分支与循环尾部结构错位 | 多轮流程 `break`/重试行为错误 |
| `workflow._finish_pending_round` | 缺 `return False`，天花板检查位置错误 | 轮次无法正确结束 |
| `main._restore_masked_keys` | 控制流被拍平成顺序判断 | Key 掩码还原逻辑错误 |

最终对拍：**623 个函数，exact 591 / near 11 / diff 21 / missing 0**。
剩余 21 处经逐条核验均为「模块级 `<module>` 与 `MaaSClient` 类体只剩函数注解差异」，
另有 4 处为 P0 之前就存在的文案/缩进差异，本轮未改。

### 过程中的错误（如实记录）

本轮曾用 `git checkout --` 试图回滚一批后端模块，导致 20 个模块的当前改动被覆盖。
没有产生数据丢失：这些模块的代码可从本轮会话的写入记录与 `_src` 下的原始 pyc 重新装配恢复，
恢复后逐函数重新对拍并纳入上面的验证结果。教训：本项目禁止 `git checkout --` /
`git reset --hard` / `git clean`，任何回滚只能通过重新装配 + 对拍确认。
（`tools/recover/manual/` 中的手写片段与 `_src` 原始 pyc 是唯一可信基线。）

### 验证

- `verify_bytecode.py`：623 函数，exact 591 / near 11 / diff 21 / missing 0。
- `pytest -q`：**113 passed**（新增 `test_backend_structure`、`test_frontend_p1`、
  `test_list_aggregation`、`test_p1_control_flow`）。
- PyInstaller 重建 `dist/多模态测试平台.exe`（66.9 MB，Python 3.8）。
- 打包版实测：首页/`/static/*`/`/api/config|dashboard|prompts|datasets|runs` 均 200；
  CSP、`nosniff`、`Referrer-Policy` 齐全；`Host: evil.com` 与 `127.0.0.1.evil.com` 均 400；
  `POST /api/demo/create` 建出 20 张图 + 20 条真值；`POST /api/runs` 返回 200。
- 无头浏览器实测可访问性：config/runs/judge-iter/extract/prompts 共 72 个控件全部具备名称；
  弹窗 `role=dialog`、`aria-modal=true`、Tab 回环、Esc 关闭、焦点归还均通过。

### 遗留（未在本轮处理）

- `docs/PRD.md`、`docs/api-contracts.md`、`docs/Plan.md` 已按代码事实反向补齐（标注"未��原厂确认"，需业务口径复核）。
- 前端仍有 105 处 `innerHTML`：数据均已经 `esc()`，但未改为 DOM 构建；属 P2 结构性改造。
- 其余 P2：CSS 重复规则与 `!important`、移动端折叠菜单、暗色模式。
- 72 组路由仍无鉴权（本地单机 + Host 白名单 + 绑定 127.0.0.1，风险可控）。

## 2026-11-05 — P2 体验与结构优化

### 目标

P0/P1 解决了工程化、安全与可用性底线。P2 处理「用得舒服」与「改得下去」：
视觉主题、移动端、加载体验、渲染安全与样式可维护性。

### 设计令牌与样式分层

- `style.css` 顶部建立 tokens 层：品牌色、表面（`--surface/--surface-2/--surface-3`）、
  文字（`--text/--text2/--text3`）、状态浅底、顶栏、代码语法色、遮罩与阴影。
- 机械替换全部硬编码色值（`#fff` 33 处、`#e8f0fe` 8 处等），组件规则不再直接写颜色。
- `!important` 从 7 处降到 2 处（仅保留 `prefers-reduced-motion`，属必须覆盖）；
  `.judge-detail-cell` 与引导气泡改为提高选择器优先级，不再依赖 `!important`。
- 亮色模式截图与改造前对比：视觉一致，无回归。

### 暗色模式

- `data-theme="dark|light"` 手动切换 + `prefers-color-scheme` 跟随系统，三态循环，
  选择写入 `localStorage["mmtest.theme"]`。
- 暗色下重定义全部令牌，组件规则零改动；补 `color-scheme: dark` 让原生控件与滚动条跟随。
- 顶栏新增 `#theme-toggle`，带 `aria-label` 与动态 `title`。

### 移动端

- ≤760px 顶栏改为汉堡菜单（`#nav-toggle` + `aria-expanded`/`aria-controls`），
  点导航项、点空白、按 Esc 均自动收起。
- 13 处数据表格包进 `.tbl-scroll`，窄屏横向滚动，页面本身不再横向溢出。
- 390×844 实测：菜单 14 项全部可达，`scrollWidth - clientWidth = 0`。

### 加载体验

- 新增 `skeleton(lines, kind)` 骨架屏组件（微光动画，尊重 reduced-motion），
  首页与帮助页接入。
- 数据集图片网格改为每帧 120 张增量插入，全部完成后再统一绑定事件，
  避免大图片集一次性重排造成白屏。

### 渲染安全

- 脚本审计 257 处模板插值：绝大多数是数字、枚举或已 `esc()` 的字段。
- 唯一直接拼接变量的是 `zoom(src)`，已改为 `createElement("img")` + 属性赋值，
  并补 `role="dialog"`、`aria-modal`、`alt`。

### 顺带发现

- 提示词库搜索使用 `.img-item` 选择器，经核对列表项确实使用该类，逻辑正确
  （审计脚本的初版规则漏判，非代码缺陷）。

### 验证

- `pytest -q`：**120 passed**（新增 7 条 P2 前端回归用例）。
- 无头浏览器逐页实测 12 个路由：全部正常渲染、无骨架屏卡死、表格容器就位、
  表单控件命名覆盖 100%。
- 暗色/亮色/390px 三种形态截图核对通过。

### 未做

- 后端列表分页：`/api/*` 列表仍全量返回。前端已用增量渲染缓解，
  服务端分页会改动 `app/main.py` 并从字节码对拍范围脱离，留待单独评估。
- 错误码化（`detail` 字符串 → 稳定 `code`）：会改变对外契约，需业务确认。

## 2026-11-06 — P3 工程增强

### 目标

P0–P2 解决了恢复正确性、安全基线与体验问题。P3 处理「长期可维护」：
单实例、日志、版本追溯、路径健壮性与自动化回归。

### 单实例

- 原实现用「端口上 /api/config 是否 200」推断本平台是否已运行，属启发式：
  端口被其他程序占用、或本平台换端口启动都会误判。
- 改为 `app/instance_lock.py`：文件字节区独占（Windows `msvcrt.locking` / POSIX `flock`）。
- Windows 下被锁字节区其他进程读不到，因此持有者信息写独立 `instance.lock.json`
  （pid / 启动时间 / 端口），锁文件只负责互斥。
- 陈旧锁按 PID 存活检测自动接管；`release()` 同时清理锁与信息文件。
- `run.py`：抢锁失败打印复用地址（含端口）后退出；成功则 `lock.update(port=...)`，
  `finally` 释放；移除无调用方的 `_is_our_app` 死代码。

### 日志

- `app/applog.py`：JSON Lines 写入 `workspace/logs/app.log`，2MB × 3 轮转。
- `sk-*` 与异常栈统一脱敏；只记录事件与耗时，不记录提示词正文、图片内容或 Key。
- 请求中间件只记 method/path/status/ms；静态资源与高频轮询降级 debug，
  慢请求（≥1s）与 4xx/5xx 保持 INFO。
- 发现并修复：日志器在切换工作区后仍写旧目录（`get_logger` 按目标路径重建 handler）。

### 版本与构建

- `app/meta.py`：版本单一来源 `VERSION=0.2.0`；`GET /api/version` 返回版本、
  构建时间、提交号、Python、frozen、平台。
- `multimodaltest.spec`：构建时生成 `build/build_info.json` 并打入产物；
  hiddenimports 补 `app.meta` / `app.applog` / `app.instance_lock`。
- 修正 `git rev-parse --short` 缺省参数失败导致提交号为空（改为显式 `HEAD`）。
- 帮助页新增版本行；`pyproject.toml` 同步 0.2.0。

### 路径健壮性

- `tests/test_paths.py`：中文 + 空格工作区、数据集上传/扫描/删除、旧版数据集兼容、
  非法名称与路径穿越拒绝、超过 260 字符的嵌套路径。
- 实测最长写入 544 字符成功。

### CI

- `.github/workflows/ci.yml`：Windows 上 pytest（3.11 / 3.12）；
  Python 3.8 跑字节码对拍，与 `bytecode_match.json` 基线比较，
  `missing > 0` 或 `diff` 增加即失败。
- `.gitignore` 为 `_src/_pyc/*.pyc` 加例外（恢复证据需入库，CI 依赖）。

### 验证

- `pytest -q`：**142 passed**。
- `verify_bytecode.py`：623 functions / exact 592 / near 10 / diff 21 / missing 0。
- 源码版实测：`/api/version` 200；第二实例复用且日志 pid 非空；停止后锁文件清理。
- 打包版实测：版本 0.2.0、build_time 与提交号 `39c998b` 均在响应中；安全头正常；
  第二实例复用；`app.log` 记录 start.listen 与 request。

### 过程记录

- 清理 `.sdd/ws_p3` 时发现仍有测试实例持有锁文件，先核对端口与命令行为本项目的
  `run.py`，只停对应 PID（30108/30596），再删除工作区。
- 11/5 遗留的多个 `run.py` 实例仍在 8735/8795/8801/8802 上运行旧代码，未擅自终止，
  留待使用者确认。

## 2026-11-06 — 新手引导流转卡顿修复

### 现象

用户反馈新手引导「整个流转的状态会有操作滞后」：点「下一步」后标题与说明有时要
1.5–4.5 秒才更新，高亮框总是慢半拍才追上目标，空状态（无项目/无运行）示意图也
迟迟不出现。

### 根因

1. `renderGuideStep()` 原先是 `async`，先 `await` 目标元素再渲染：
   selector 最多 `10 × 150ms`，`entry` 再 `20 × 150ms`，无 selector 再固定等
   `450ms`。所有文案渲染都排在这段等待之后，所以点击后长时间无任何反馈。
2. 每一步都 `remove()` 旧 `#tour-root` 再重建，整棵引导 DOM 反复销毁重建，
   带来闪烁、过渡中断和状态丢失。
3. `.tour-spot` 用 `top/left/width/height` + CSS transition 定位，且
   `scrollIntoView` 之后还要 `setTimeout(..., 350)` 才落位，高亮「追不上」目标。
4. 空状态必须等满 1 秒才切到创建入口与示意图。
5. 无键盘支持；快速连点会叠加多组 pending 定时器。

### 修复

- **渲染同步化**：`renderGuideStep()` 改为同步，先立刻更新步骤号、标题、正文与
  按钮，目标定位作为异步补齐；寻找目标改为 `locateTourTarget()` 短轮询
  （`entry` 探测 400ms、总预算 2500/800ms，间隔 50/90ms），并用 `seq` 丢弃过期结果。
- **DOM 复用**：新增 `ensureTourRoot()`，`#tour-root` 只创建一次，后续仅改文本与
  显隐；`stopGuide()` 统一清定时器、解绑 scroll/resize/keydown 并移除节点。
- **定位改为合成层**：`.tour-spot` / `.tour-bubble` 用 `translate3d()` 定位，
  加 `will-change: transform`；落位后下一帧再校正，之后才加 `.smooth` 过渡，
  避免首次渲染就做补间动画。
- **空状态降级**：目标不存在时保留遮罩、显示 mock 示意图，不再白等 1 秒。
- **交互补齐**：`Esc` 关闭、`←/→` 上一步/下一步；连点以 `seq` 保证只应用最后一次。

### 验证

- 浏览器实测（headless Chrome + CDP，1440×900 与 390×844）：
  标题切换 **1–2ms**（修复前 161–1729ms），高亮就位 **57–75ms**（首屏）/ 
  **416–462ms**（空状态降级步骤，修复前固定 ≥350ms 且更晚），
  全部气泡与高亮均在视口内，无控制台错误。
- 快速连点 40ms × 6：步号 `2/8 → 7/8` 正确，DOM 始终只有 1 个 root/spot/bubble，
  `stopGuide` 后 `_tour === null` 且节点移除。
- 竞态复测发现：快速「前进 → 后退」时，排队中的 `hashchange` 晚于下一步到达，
  旧的单个 `driven` 布尔标记已被覆盖，引导被误判为用户导航而关闭。改为主记录
  引导自发跳转的次数 `hops`，每次 `hash` 赋值恰好抵消一次；用户手动导航仍正常退出。
- 输入框守卫：引导跨配置页时若正在填 Base URL / API Key，方向键只移动光标，
  不再误切步骤；`Esc` 仍可随时关闭。
- `pytest -q`：**145 passed**（新增 3 条引导静态回归用例）。
- `verify_bytecode.py`：623 functions / exact 592 / near 10 / diff 21 / missing 0，与基线一致。

### 发布产物

- 提交 `878b5a8`（`fix(web): 新手引导改为即时响应与短预算定位`）后重建：
  `dist/多模态测试平台.exe`，66,941,539 字节，构建时间 2026-11-06 09:14:26。
- 打包版实测（独立工作区 + 端口 8791）：
  - `/api/version`：version 0.2.0、git_commit `878b5a8`、git_dirty false、frozen true；
  - `/static/app.js` 含 `ensureTourRoot` / `hops` / `isTourTyping`，CSS 含 `.tour-spot.smooth`；
  - 引导 8 步实测点击响应 0.3–2.5ms，最后一步关闭并写入 `guide_done`；
  - 安全头齐全，`Host: evil.com` 返回 400；停止后实例锁清理，`app.log` 正常落盘。
- 打包解释器为 Python 3.12.8（venv 内 PyInstaller 6.22.3）；py38 环境未装 PyInstaller，
  故未用 3.8 重建，功能与对拍基线不受影响。

## 2026-11-06 — 新手引导第 2 步定位回归修复

### 现象

用户反馈：引导第 2 步（配置模型）时，气泡被挤到窗口最底部，配置区内容看不到。

### 根因

第 2 步的目标是 `#c-sites`（整块站点列表）。站点一多，目标高度可达 850px 以上，
比 1366x768 / 1536x730 这类笔记本窗口的可视区还高。原来的定位逻辑有两个问题：

1. `scrollIntoView({block: "center"})` 对超高元素会把页面滚到列表中间，
   连「系统配置」标题和页签都被顶出视口；
2. 气泡兜底只有「下方放不下就改上方，再不行贴底」，没有给高亮让位的概念，
   高亮撑满整屏时气泡只能落在最底部，视觉上像是「被放到了最下面」。

### 修复

- 新增 `tourViewport()`：可视区上边界避开 sticky 顶栏。
- 新增 `scrollTourTarget()`：目标高度不超过可视区时仍居中；超过时以
  「目标 / 所属卡片 / 页面标题」里最靠上的锚点顶部对齐，保证页头始终可见。
- 重写 `positionTour()`：气泡优先占位（下方 -> 上方 -> 贴底），高亮再按气泡
  让出的空间收口，并保留至少 120px 高度。气泡与高亮不再互相遮挡。
- 高亮宽度/高度统一取「目标 ∩ 可视区」，长列表不会再画出屏。

### 验证

- headless Chrome 实测 1280x600 / 1366x650 / 1366x768 / 1440x900 / 1920x1080：
  气泡全部在视口内、与高亮零重叠，页面标题保持可见。
- 多站点（4 个）与 390x844 移动视口同样通过。
- 8 步全流程逐步检查：每步 bubbleInside=true、overlap=false。
- `pytest -q`：146 passed（新增 1 条超高目标定位回归用例）。
- `verify_bytecode.py`：623 / 592 / 10 / 21 / 0，与基线一致。

## 2026-11-06 — 引导第 2 步仍被挤到角落 + 气泡不可拖动

### 现象（用户复测）

上一版修完后用户刷新页面，仍看到引导气泡被挤到右下角，且无法拖动。

### 根因

1. **浏览器还在用旧 JS**：静态资源没有任何 `Cache-Control`，前端文件名也不带指纹。
   改完代码重启服务后，浏览器仍可能命中旧 `app.js`，所以「刷新了还是不行」。
2. **第 2 步高亮的目标太大**：目标是整块 `#c-sites`，站点越多越高；
   即使滚动与收口逻辑正确，气泡也只剩边角可放。
3. **气泡本来就不可拖动**：原实现没有任何拖动能力，位置完全由算法决定。

### 修复

- 静态资源改用 `no-cache, must-revalidate`（`app/security.py` 中间件统一加头），
  命中 ETag 时仍是 304。
- `index.html` 的 `app.js` / `style.css` 加 `?v=` 版本参数，由中间件在响应时替换为
  「版本 + 前端内容 SHA1 + 构建提交号」。内容一变 URL 就变，已缓存的旧副本自然失效。
  这一层是关键：仅靠 `no-cache` 无法让浏览器放弃已经缓存的旧 URL。
- 第 2 步的 `selector` 从 `#c-sites` 改为 `#c-sites .site-card`，只高亮第一张站点卡片；
  没有站点时回退到「添加站点」按钮。
- 新增 `bindTourDrag()`：气泡可按住拖动（指针捕获、边界夹取、按钮/输入框不触发），
  拖过之后本步位置由用户决定，滚动与缩放只挪高亮，不再抢回气泡。
- 气泡加 `cursor: grab / grabbing`，正文保持可选中。

### 验证

- `/`、`/static/app.js`、`/static/style.css` 均返回 `Cache-Control: no-cache, must-revalidate`。
- `/` 输出 `/static/app.js?v=0.2.0-d8e9c9f3-ae4ef9c`，带版本参数可直接 200 加载。
- 1366×768、4 个站点：第 2 步高亮 225–441，气泡 455–655，标题 72–96 可见，零重叠。
- 拖动测试：气泡从 (37,455) 拖到 (8,375)，仍在视口内，指针事件与边界夹取正常。
- 8 步全流程：每步 `inside=true`、`overlap=false`。
- `pytest -q`：150 passed（新增拖动、第 2 步目标、静态资源版本与缓存头用例）。
- `verify_bytecode.py`：623 / 592 / 10 / 21 / 0，与基线一致。

### 发布产物（b9f41da）

- `dist/多模态测试平台.exe` 重建于 2026-11-06 09:49:42，内嵌 `git_commit b9f41da`、`git_dirty false`。
- 打包版实测：`/`、`/static/app.js`、`/static/style.css` 均为 `no-cache, must-revalidate`；
  HTML 输出 `?v=0.2.0-d8e9c9f3-b9f41da`；带该参数可直接 200 加载。
- 打包版 1366x768 + 4 站点：第 2 步高亮 225-441、气泡 455-655、零重叠；
  拖动后气泡到 (8,395)，仍在视口内。

## 2026-11-06 — 新手引导第 3–7 步：高亮框贴合 + 定位滞后

用户复现：第三步「生成提示词」刚点进去仍滞后，高亮框把「提示词生成」几个字切掉一半；
第四步「运行测试」及之后每一步都有同样的滞后感。

### 根因

1. **框被拿去给气泡让位**：`positionTour()` 里 `limit = by - gap` 把高亮框上/下边界
   按气泡位置收缩，再叠一段 `MIN_SPOT` 撑高。结果框既可能切掉目标（第三步切标题），
   也可能整块落到目标外面（第六步框在「启动裁判」上方 60px，#ji-start 完全裸露）。
   实测第 6 步：框 `{t:241,b:285}`，按钮 `{t:304,b:342}`。
2. **等目标的时间白烧**：`locateTourTarget()` 里有 `entryProbe = 400`，
   selector 还没出现时一律先等 400ms 才试 entry，而实测目标 DOM 只要 30–80ms 就绪
   （`firstSel` 26–79ms、`appQuiet` 92–175ms）。于是每步框到位都要 530–560ms。
3. **切步骤先闪一下**：`renderGuideStep()` 先把高亮清空、气泡 `center` 回屏幕中央，
   等目标找到再平移过去，视觉上就是「点了没反应 → 框突然出现」。

### 修复

- `positionTour()`：高亮框改为 `目标 ∩ 可视区`，只加 6px 内边距，不撑高、不收口。
- 新增 `placeBubble()`：气泡按 下 → 右 → 左 → 上 找第一条放得下的空带；
  四条都放不下时取上下较高的一条，限高（`max-height`）后内部滚动——
  宁可气泡变小，也绝不盖住目标。CSS 加 `overflow: auto; overscroll-behavior: contain`。
- `locateTourTarget()`：删掉 `entryProbe`，selector 一出现就用、否则立刻退回 entry；
  轮询 24ms（前 200ms）/ 50ms。框到位 30–80ms。
- `renderGuideStep()`：有目标的步骤不再先居中；新增 `pinTourBubble()` 记住当前视觉位置，
  切换 center/自由定位时不跳。目标就绪前保持整屏压暗，不沿用上一页的旧框。
- 第 5 步（人工审核）补 `entry: "#r-list"`，空工作区也有锚点，不再全屏压暗。
- 目标确实找不到时（`match=null`）清掉旧框并居中，不留残影。

### 验证（CDP 实测，真实工作区）

- 第 3–7 步框到位：49–80ms（原 530–560ms）；`coversTarget=true` 全部通过。
- 第 3 步框 `{t:119,b:169}` 完整包住 `#pai-new` `{t:125,b:163}`，「提示词生成」标题 72–96 未被切。
- 第 6 步框 `{t:298,b:348}` 完整包住 `#ji-start` `{t:304,b:342}`（修复前框在其上方 60px）。
- 900×500 / 1024×600 / 1280×720 / 1366×768 / 1400×520 / 1600×900：`bubbleOverlapsSpot=false`、`bubbleOut=false`。
- `pytest -q`：152 passed（新增目标查找预算、切步不闪烁、择位降级断言）。
- `verify_bytecode.py`：623 / 592 / 10 / 21 / 0，与基线一致。

## 2026-11-06 — 主题切换：深色系统下要点两下才变亮

用户复现：日间 → 夜间正常；夜间 → 日间要点两下。

### 根因

`cycleTheme()` 是 `auto → light → dark → auto` 三态循环，`currentTheme()` 返回的是
存储值而不是实际外观。用户系统本身是深色时：

1. 第一次点击「暗」→ `auto`：`data-theme` 被移除，`@media (prefers-color-scheme: dark)`
   接管 —— 外观仍是深色，**视觉上零变化**；
2. 第二次点击 `auto` → `light` 才真正变亮。

所以感觉像「点一下没反应，得点两下」。

### 修复

- 新增 `systemTheme()` / `savedTheme()` / `currentTheme()` 三层：存储值仍是
  `auto|light|dark`，但 `currentTheme()` 返回**实际生效**的 `light|dark`。
- `toggleTheme()`：按实际外观取反（`currentTheme() === "dark" ? "light" : "dark"`），
  点一下必定翻转，不再经过 auto。
- `syncThemeButton()`：图标表示「点一下会变成什么」，title/aria-label 带当前值
  与目标值；`auto` 下监听 `matchMedia` 变化刷新提示。
- 默认仍跟随系统（首次打开不受影响），一旦点过就存显式选择。

### 验证

- 模拟系统深色（`Emulation.setEmulatedMedia`）：`rgb(15,20,27)` → 第 1 下 →
  `rgb(244,246,250)`；第 2、3 下继续交替翻转。
- 模拟系统亮色：`rgb(244,246,250)` → 第 1 下 → `rgb(15,20,27)`，同样一次到位。
- 图标随之切换 ☾ / ☀，title 显示「主题：亮色（点击切换到暗色）」。
- `pytest -q`：153 passed（新增 `test_theme_toggle_flips_in_one_click`）。

## 2026-11-06 — 顶栏「工具」下拉按钮比其它导航项高

截图反馈：「工具」按钮比导航栏其它项高，很不协调。

### 根因

`.nav-dropbtn` 没有显式 `display`，继承了 `<a>` 的 `display: inline`；其它导航项
（`.topbar nav a`）在 flex 容器里被块级化。行内盒按基线对齐，所以「工具」整体上移。
CDP 实测：工具 `top 6 / bottom 36`，其余都是 `top 11 / bottom 41`，高度虽同为 30px，
但整体高了 5px。

### 修复

`web/style.css` 增加 `.nav-dropdown > .nav-dropbtn { display: block; }`，
让触发器与兄弟链接同为块级盒。

### 验证

- 桌面 1366×768：13 个导航项全部 `top 11 / bottom 41 / height 30`，完全对齐。
- 下拉菜单仍正常：`display:flex`，从按钮底部 41 开始展开，位置与按钮左边缘对齐。
- 移动端 390×844：8 个可见项全部 `height 41`，间距 2px 一致，纵向菜单未受影响。
- `pytest -q`：154 passed（新增 `test_nav_dropdown_trigger_matches_sibling_links`）。

## 2026-11-06 — 图片集详情「批量分组」按钮出框且高度不一致

用户反馈：示例项目 → 图片集详情里，「把当前筛选图片批量分组」比旁边的按钮矮，
文字还戳出了卡片。

### 根因

1. **出框**：按钮外包了一层 `<div style="flex:0">`，但 `.row > *` 的
   `min-width: 120px` 依然生效，把包装层压成 120px；按钮自身 `white-space: nowrap`
   且有 158px 内容宽，于是横向溢出。实测按钮右边缘 1365.5px，卡片右边界 1343px，
   溢出 22px；卡片 `scrollWidth 1342 > clientWidth 1318`。
2. **高度不一致**：按钮用了 `.btn.small`（padding 4px 10px / 12.5px），实测 29px；
   同排 `<select>` 是 8px 10px + 13.5px，实测 38px，差 9px。

### 修复

- 该行改用 `class="row batch-row"`，两个控件加 `batch-split` / `batch-apply` 类。
- `.batch-row .batch-apply { flex: 0 0 auto; min-width: 0; }`：包装层按内容宽度，
  不再被 120px 下限压扁。
- `.batch-row .batch-split select, .batch-row .batch-apply .btn { height: 38px; }`：
  与下拉框等高；按钮同时去掉 `small`，字号回到 13.5px。
- `.row > .no-flex, .row > *[data-noflex]` 留作通用逃生口，避免以后再踩同一个坑。

### 验证

- 1366×768 / 1280×720 / 1024×600 / 760×600 / 480×800 五档：
  `btnInsideCard=true`、`sameH=true`（均为 38px）、`noOverflow=true`（scrollWidth ≤ clientWidth）。
- 480px 窄屏时自动换行：下拉在上一行、按钮在下一行，仍在卡片内且等高。
- 卡片 `scrollWidth == clientWidth`（1318），不再有横向溢出。
- `pytest -q`：155 passed（新增 `test_dataset_batch_group_button_fits_and_matches_height`）。

## 2026-11-06 — 帮助页目录移出正文，改为左侧常驻栏

用户反馈：帮助页的目录和正文耦合在一起，往下滚就没了，希望目录常驻在正文左侧，
点章节能跳到对应位置。

### 根因

原实现 `renderHelpText()` 把 `/api/help` 的纯文本按 `====` 切成标题 + 段落，
直接顺序塞进同一个 `.card` 里。目录本身也是文档的一节（第三块），所以它只是
正文的一部分，滚动自然跟着走，也没有任何跳转能力。

### 修复

- `parseHelpText()` 返回结构化 `{ intro, sections[] }`，每节带稳定 `id`；
  文本自带的「目录」块跳过，不再在正文里重复一遍。
- `renderHelpPage()` 输出两棵独立子树：`aside.help-toc`（目录）+
  `div.help-body`（正文），由 `.help-layout` 用
  `grid-template-columns: 232px minmax(0, 1fr)` 并排。
- `.help-toc` 用 `position: sticky; top: 66px; max-height: calc(100vh - 82px)`，
  正文再长目录也停在视口内，超长时目录自己内部滚动。
- `bindHelpToc()`：点击 `preventDefault` 后 `window.scrollTo` 到
  `el.top + scrollY - stickyPad()`，**不写 `location.hash`**（会触发 SPA 重渲染）；
  滚动用 rAF 节流判定当前章节并高亮，高亮项若滚出目录可视区会自动带回。
- `stickyPad()` 按顶栏实测高度计算；860px 以下目录变成顶栏下的 sticky 横条，
  留白再叠加横条高度，保证标题不被盖住。
- 新增 `onPageLeave()` / `runPageCleanups()`，`navigate()` 开头调用，
  路由切走时摘掉帮助页挂在 `window` 上的 scroll 监听。

### 验证（CDP 实测）

- 1366×768：目录 232px、`position: sticky`、正文左边缘 269（目录右 255），
  首项「一、首次使用」、末项「十六、术语表」；点第 1/4/8/16 章标题 `top`
  为 72/101/101/101，均在顶栏 52px 之下且高亮跟随，`hash` 始终 `#/help`；
  手动滚到 6000px 目录仍 `top 66`，高亮切到「七、运行测试」。
- 900×700：仍为左侧栏（232px，正文左 266），跳转与高亮同上。
- 400×800：降级为顶栏下常驻横条（`top 52`），滚动 6000px 目录仍在视口内，
  跳转后标题 `top 149` 未被遮挡，横向无溢出。
- 路由切走再回来：目录 16 项、`.help-toc` 与 `.help-body` 各 1 个，无重复挂载。
- `pytest -q`：157 passed（新增帮助页目录与页面级监听清理两条用例）。

## 2026-11-06 — 帮助页正文排版：术语表/步骤/问答/代码块结构化

用户反馈：术语表明明是表格，正文里完全看不出是表格，其他章节也有类似问题。

### 根因

1. `renderHelpText()` 把整章按 `====` 切成"标题 + 一整段文本"，每章正文仍是一个
   `white-space: pre-wrap` 的 `div`。原文里靠缩进表达的所有结构（步骤、子步骤、
   嵌套列表、术语表的两列对齐、JSON 示例）都被当成普通文本原样输出，
   术语表因此退化成一堆用空格对齐的行。
2. `:root` 中一批设计令牌写成自引用（`--surface-2: var(--surface-2)`、
   `--surface-hover`、`--text3`、`--border-strong`、`--primary-soft`、
   `--code-*`、`--overlay` 等），CSS 解析后值为空；`--panel` 从未定义。
   于是 `.card` 的 `background: var(--panel)` 一直是透明，浅色下卡片与页面同色，
   表格即使有边框也看不出层次。

### 修复

- 新增 `parseHelpBody()`：先按缩进识别术语表区域，其余片段走常规分块。
  块类型：`sub`（小节）、`code`（JSON）、`qa`、`step`（含子块）、`bullets`、`para`、`glossary`。
- 术语表按"顶格术语 + 2 个以上空格 + 说明 + 更深缩进的续行"识别，
  续行里的 `- ` 子项归到该词条下；与术语混排的 `output_format 输出格式有问题。`
  这类单空格行，在术语表上下文中一并收进表格（第 9 章的 8 个模块枚举因此完整成表）。
- 渲染：`help-steps` / `help-ul` / `help-code` / `help-faq` / `help-table` /
  `help-sub` 六种语义结构，JSON 代码块按 token 着色，正文行内字段名做等宽高亮。
- 长行合并用 `helpJoin()` 处理中英文边界，避免 `OUTPUT FORMAT` + 中文粘连，
  也避免中文之间插入多余空格。
- 补全设计令牌：`--panel`、`--surface-2/3/hover`、`--text3`、`--border-strong`、
  四个状态浅底、`--code-*`、`--img-bg-soft`、`--overlay` 都给出具体值；
  暗色两处变量块补 `--panel`。
- 窄屏：行内标识符从 `code` 改为 `span`（`code` 不换行会把页面撑宽 136px）；
  860px 以下术语表从两列改为上下排，`thead` 隐藏、术语行加粗。

### 验证（CDP 实测）

- 结构：16 章生成 27 组步骤、47 个列表、2 个代码块、19 个问答、2 张表
  （第 9 章 8 行模块枚举、第 16 章 19 条术语），旧的 `help-pre` 为 0。
- 1366×768 / 900×700：表格两列完整，`scrollWidth == clientWidth`，无横向溢出；
  目录 16 项跳转后标题 top 72/101，hash 保持 `#/help`。
- 400×800：`scrollWidth == 400`（修复前 536，行内 `code` 撑破 136px），
  术语表自动改为上下排。
- 明暗两套：卡片 `rgb(22,29,39)` / `rgb(255,255,255)`，
  表头与代码块均有独立底色，JSON 键/值/数字着色生效。
- `pytest -q`：159 passed（新增正文结构化与设计令牌两条用例）。
