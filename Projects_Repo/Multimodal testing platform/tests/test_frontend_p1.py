import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def read(name):
    return (WEB / name).read_text(encoding="utf-8")


def test_no_native_confirm_or_prompt_left():
    app = read("app.js")
    assert not re.search(r"(?<![A-Za-z])confirm\(", app)
    assert not re.search(r"(?<![A-Za-z])prompt\(", app)
    assert "confirmDlg(" in app
    assert "promptDlg(" in app


def test_native_dialog_is_centered():
    """全局 * { margin: 0 } 覆盖了 <dialog> 的 UA margin:auto。

    实测 showModal() 后弹窗贴在视口左上角（left=0, top=0）。必须显式
    position:fixed + inset:0 + margin:auto 才能恢复水平/垂直居中，
    同时保留 max-height 让窄屏/矮窗口下弹窗自身可滚动而不是超出视口。
    """
    css = read("style.css")
    assert "* { box-sizing: border-box; margin: 0; padding: 0; }" in css
    # 规则块里带注释（注释内含 `}`），匹配前先剥掉注释
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(r"\.pai-dialog \{([^}]*)\}", plain)
    assert m, "缺少 .pai-dialog 规则"
    body = m.group(1)
    for decl in ("position: fixed;", "inset: 0;", "margin: auto;"):
        assert decl in body, decl
    assert "max-height: calc(100vh - 32px);" in body


def test_dialog_has_a11y_semantics():
    app = read("app.js")
    assert 'role="dialog"' in app
    assert 'aria-modal="true"' in app
    assert "trapDlgFocus" in app
    assert "previousFocus.focus()" in app
    assert "onClose: () => finish(allowCancel ? false : true)" in app
    assert "onClose: () => finish(null)" in app


def test_focus_visible_style_exists():
    css = read("style.css")
    assert ":focus-visible" in css
    assert re.search(r":focus-visible\s*\{[^}]*outline", css)


MAIN_NAV = chr(0x4E3B) + chr(0x5BFC) + chr(0x822A)
SEARCH_PROJECT = chr(0x641C) + chr(0x7D22) + chr(0x9879) + chr(0x76EE)
SEARCH_DATASET = chr(0x641C) + chr(0x7D22) + chr(0x56FE) + chr(0x7247) + chr(0x96C6)
SEARCH_IMAGE = chr(0x641C) + chr(0x7D22) + chr(0x56FE) + chr(0x7247) + chr(0x540D)
SEARCH_PROMPT = chr(0x641C) + chr(0x7D22) + chr(0x63D0) + chr(0x793A) + chr(0x8BCD)


def test_nav_and_search_have_accessible_names():
    html = read("index.html")
    assert f'aria-label="{MAIN_NAV}"' in html
    app = read("app.js")
    for name in (SEARCH_PROJECT, SEARCH_DATASET, SEARCH_IMAGE, SEARCH_PROMPT):
        assert f'aria-label="{name}"' in app


def test_progress_bar_shows_percentage_and_failures():
    app = read("app.js")
    assert "function progressBar(processed, total, failed, parseFailed)" in app
    assert 'role="progressbar"' in app
    assert "aria-valuenow" in app
    assert "progressBar((r.done || 0) + (r.failed || 0), r.total, r.failed, r.parse_failed)" in app
    assert "progressBar(processed, total, job.failed)" in app
    # 解析失败与调用失败必须分开标注，避免「有图没结论但失败数为 0」
    assert "调用失败 ${failed}" in app
    assert "解析失败 ${parseFailed}" in app


def test_files_are_utf8_without_bom_and_lf():
    for name in ("app.js", "style.css", "index.html"):
        raw = (WEB / name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), name
        assert b"\r\n" not in raw, name
def test_controls_get_accessible_names_after_render():
    app = read("app.js")
    assert "function enhanceA11y(root)" in app
    assert "A11Y_CTRL_SELECTOR" in app
    assert 'label.htmlFor = el.id;' in app
    assert 'el.setAttribute("aria-label"' in app
    assert "MutationObserver" in app
    assert "if (child.querySelector(A11Y_CTRL_SELECTOR)) continue;" in app
    assert "enhanceA11y(document)" in app


def test_skip_link_and_main_landmark():
    html = read("index.html")
    assert 'class="skip-link"' in html
    assert 'id="app" tabindex="-1"' in html
    assert "<main " in html
    app = read("app.js")
    assert 'e.target.closest(".skip-link")' in app


def test_toast_announces_status():
    app = read("app.js")
    assert 'd.setAttribute("role", ok === false ? "alert" : "status")' in app
    assert '"aria-live"' in app


def test_reduced_motion_and_table_scroll_style():
    css = read("style.css")
    assert "prefers-reduced-motion: reduce" in css
    assert ".skip-link:focus" in css
    assert ".tbl-scroll" in css

def test_design_tokens_and_dark_theme():
    css = read("style.css")
    assert "--surface:" in css and "--text2:" in css
    assert ':root[data-theme="dark"]' in css
    assert "prefers-color-scheme: dark" in css
    # 组件规则不应再出现硬编码的纯白/纯黑背景
    assert "background: #ffffff;" not in css
    assert "background: #fff;" not in css
    assert ".card {" in css and "background: var(--surface);" in css


def test_important_only_for_reduced_motion():
    css = read("style.css")
    bad = [ln for ln in css.split("\n") if "!important" in ln and "animation-duration" not in ln and "transition-duration" not in ln]
    assert not bad, bad


def test_narrow_breakpoint_covers_desktop_nav_overflow():
    """桌面导航（logo 192 + 9 项约 647）在 1000 以下必然溢出。

    原断点是 760，导致 761–940 的窗口里导航把整页顶宽 76–131px。
    """
    css = read("style.css")
    assert "@media (max-width: 1000px) {" in css
    # 断点块里必须有汉堡按钮的显示切换，否则窄屏没有入口
    block = css[css.index("@media (max-width: 1000px) {"):css.index("@media (max-width: 760px) {")]
    assert ".nav-toggle { display: inline-flex; }" in block
    assert ".topbar nav.open { display: flex; }" in block
    # JS 收起菜单的判据要跟着断点走
    app = read("app.js")
    assert 'matchMedia("(max-width: 1000px)").matches' in app


def test_design_tokens_define_type_scale_and_motion():
    html = read("index.html")
    assert 'id="nav-toggle"' in html
    assert 'aria-controls="nav"' in html
    assert 'id="theme-toggle"' in html
    app = read("app.js")
    assert "function setupNavToggle()" in app
    assert "function applyTheme(mode, persist)" in app
    assert "function toggleTheme()" in app
    assert 'const THEME_KEY = "mmtest.theme";' in app


def test_theme_toggle_flips_in_one_click():
    app = read("app.js")
    # 旧实现是 auto -> light -> dark -> auto 三态循环：系统本身是深色时，
    # 「暗 -> auto」视觉无变化，用户必须点两下才变亮（看起来像开关失灵）。
    assert "cycleTheme" not in app
    assert 'applyTheme(currentTheme() === "dark" ? "light" : "dark");' in app
    assert "themeBtn.onclick = toggleTheme;" in app
    # auto 仍在代码层保留（跟随系统），点过之后存的是显式选择
    assert "function systemTheme()" in app
    assert "return mode === \"auto\" ? systemTheme() : mode;" in app


def test_theme_defaults_to_light_without_persisting():
    """首次进入默认浅色，但不能把 light 写进 localStorage。

    一旦落盘，"auto 跟随系统"就再也没机会生效：用户永远被钉死在 light。
    默认值是「读不到选择时的兜底」，不是「用户已选择」。
    """
    app = read("app.js")
    assert 'const THEME_DEFAULT = "light";' in app
    assert "function savedTheme() {\n  return storedTheme() || THEME_DEFAULT;\n}" in app
    assert "function storedTheme()" in app
    # 首屏应用默认值必须显式关掉持久化
    assert "applyTheme(savedTheme(), false);" in app
    # 持久化只发生在 persist !== false 时
    assert "if (persist !== false) {" in app
    # 用户点过之后才写盘
    assert 'applyTheme(currentTheme() === "dark" ? "light" : "dark");' in app


def test_help_toc_lives_outside_the_body_and_tracks_scroll():
    app = read("app.js")
    css = read("style.css")
    # 目录要从正文里抽出来，做成左侧独立的一栏
    assert "function parseHelpText(text)" in app
    assert "function renderHelpPage(parsed)" in app
    assert 'class="card help-toc"' in app and 'class="card help-body"' in app
    assert 'if (chunk.title === "目录") return;' in app  # 正文里不再重复渲染目录块
    assert ".help-layout {" in css and "grid-template-columns: 232px minmax(0, 1fr);" in css
    # 目录常驻：sticky，且给 sticky 顶栏让出空间
    assert "position: sticky;" in css
    assert "top: 66px;" in css and "max-height: calc(100vh - 82px);" in css
    # 点击目录跳转到对应章节，但绝不能改 hash（SPA 用它做路由）
    assert "function bindHelpToc(root, sections)" in app
    assert "const scrollToSection = (el) =>" in app
    assert "window.scrollTo({ top:" in app
    assert "e.preventDefault();" in app
    assert "location.hash =" not in app[app.index("function bindHelpToc("):app.index('route("help"')]
    # scrollIntoView 的目标是 section，留白必须挂在 section 上
    assert ".help-sec {" in css
    sec = css[css.index(".help-sec {"):]
    assert "scroll-margin-top: 72px;" in sec[:200]


def test_page_level_listeners_are_cleaned_on_route_change():
    app = read("app.js")
    assert "let pageCleanups = [];" in app
    assert "function onPageLeave(fn)" in app
    assert "function runPageCleanups()" in app
    # navigate() 必须先清理上一页挂在 window 上的监听，否则旧页面回调会越积越多
    nav = app[app.index("function navigate()"):app.index('window.addEventListener("hashchange"')]
    assert "clearPageTimers();" in nav and "runPageCleanups();" in nav


def test_dataset_batch_group_button_fits_and_matches_height():
    app = read("app.js")
    css = read("style.css")
    # 外层包装曾被 .row > * 的 min-width:120px 压到 120px，而按钮本身要 158px，
    # 于是横向戳出卡片 22px；同时用了 small 尺寸，比同排的下拉框矮 9px。
    assert '<div class="batch-apply"><button class="btn" id="dd-batch-apply">' in app
    assert '<div class="batch-split"><select id="dd-batch-split">' in app
    assert 'class="row batch-row' in app
    assert ".batch-row .batch-apply { flex: 0 0 auto; min-width: 0; }" in css
    assert ".batch-row .batch-split select," in css
    assert ".batch-row .batch-apply .btn { height: var(--h-ctl); }" in css


def test_row_buttons_never_shrink_and_batch_row_stacks_on_narrow():
    """按钮不能参与 flex 收缩，否则中文标签会被压到边框上（看起来像文字出框）。

    这是两个真实缺陷的共同根因：
    - 图片集详情的「把当前筛选图片批量分组」13 个汉字正好填满内容区；
    - 帮助页的「重新观看新手引导」在 390px 被 .row > * 的 flex:1 压掉 5px。
    """
    css = read("style.css")
    assert ".row > .btn, .row > button, .row > a.btn { flex: 0 0 auto; min-width: 0; }" in css
    # 批量分组行：说明单独成类，且窄屏靠 CSS 换行，不再靠内联 flex
    app = read("app.js")
    assert 'class="muted batch-note"' in app
    assert 'style="flex:2"' not in app.split("batch-row")[1][:400]
    assert ".batch-row .batch-note { flex: 2 1 auto; min-width: 0; }" in css
    assert "@media (max-width: 1200px) {" in css
    assert ".batch-row .batch-apply .btn { flex: 0 0 auto; padding: 0 20px; }" in css


def test_nav_dropdown_trigger_matches_sibling_links():
    css = read("style.css")
    # 早期导航项没有固定高度，.nav-dropbtn 若是 inline 会按基线对齐、比兄弟链接上移，
    # 所以当时用 display:block 压掉了基线问题。现在导航项统一 height: var(--h-md)，
    # 块级盒里的行盒会贴顶（文字比其他导航项高约 6px），必须 flex + 垂直居中。
    assert ".nav-dropdown > .nav-dropbtn { display: flex; align-items: center; }" in css
    assert ".nav-dropdown > .nav-dropbtn { display: block; }" not in css


def test_project_context_is_global_and_persisted():
    """M1：当前项目必须是全局单例并可跨页保持。

    旧实现里 state.project 出现 0 次：用户在「项目 / 图片集」里认了一次项目，
    换到「运行测试」又要在全部项目的数据里重新认一遍。
    """
    app = read("app.js")
    html = read("index.html")
    # 全局状态 + 持久化键
    assert 'const PROJECT_KEY = "mmtest.project";' in app
    assert "state.project = savedProject();" in app
    assert "function setProject(" in app
    # 顶栏下方的常驻上下文条
    assert 'id="ctxbar"' in html
    assert 'id="ctx-project"' in html and 'id="ctx-crumbs"' in html


def test_project_context_scopes_list_pages():
    """列表页必须按当前项目收口，而不是把全部项目的行混在一起。"""
    app = read("app.js")
    # 运行测试 / 裁判与优化 / 真值 / 评估 都要经过项目过滤
    assert "const doneRuns = projectRuns(runs.items).filter(" in app
    assert "data.items = projectRuns(data.items);" in app
    assert 'const ts = { items: (tsAll.items || []).filter(inProject) };' in app
    assert 'const es = { items: (esAll.items || []).filter(inProject) };' in app
    assert app.count("projectDatasets(ds.items)") >= 2
    # 提示词库不能按项目过滤：/api/prompts 没有 project 字段，硬过滤会丢数据
    assert "projectPrompts" not in app


def test_deep_links_backfill_current_project():
    """从链接直达详情页时，顶部条必须显示它真实的归属项目。"""
    app = read("app.js")
    assert "function adoptProjectOf(" in app
    # 运行结果 / 真值标注 / 图片集详情 三条深链都要回填
    assert "adoptProjectOf(run)" in app
    assert "adoptProjectOf(t)" in app
    assert 'adoptProjectOf({ ref: name })' in app


def test_context_bar_hides_on_non_project_routes():
    """配置 / 帮助 / JSON 工具 / 提示词模板不属于任何项目，上下文条不显示。"""
    app = read("app.js")
    assert 'const CTX_HIDDEN_ROUTES = new Set(["config", "help", "jsontool", "profiles"]);' in app
    assert "if (CTX_HIDDEN_ROUTES.has(name)) { bar.hidden = true; return; }" in app


def test_group_input_uses_self_drawn_suggestions_not_datalist():
    """`<input list>` 的候选框由浏览器绘制：方角、无令牌，暗色下是黑块。

    提示词库的两处分组输入改成「文本输入 + 自绘建议浮层」，与全站下拉同一套
    边框/阴影/令牌。关键约束是「仍可自由输入」：分组允许新建，
    所以回车只在用户用方向键主动选择过时才采纳建议。
    """
    app = read("app.js")
    css = read("style.css")
    # 原生 datalist 必须彻底退出
    assert "<datalist" not in app
    assert "list=\"p-groups" not in app
    # 两处输入都改挂 data-suggest
    assert app.count('data-suggest="${esc(JSON.stringify(') == 2
    assert "function sugEnhance(root)" in app
    assert 'input.dataset.sugUi = "1";' in app
    # 只在用户主动移动过之后，回车才采纳第一条建议
    assert "if (_openSuggest.moved && rows[_openSuggest.active])" in app
    # 浮层复用下拉的定位与视觉
    assert "function sugReposition()" in app
    assert "selPopPosition(input, pop);" in app
    assert re.search(r"\.sug-pop \{[^}]*padding: var\(--sp-1\)", css)
    # 必须真正挂载，不只是定义
    assert app.count("sugEnhance(document);") == 2
    assert "setupSuggest();" in app


def test_context_bar_offers_way_back_to_all_projects():
    """进入某个项目后必须能一步回到「全部项目」工作台。

    只改 hash 不够：工作台会按 state.project 继续渲染单项目视图，
    所以按钮必须同时清空项目作用域。全部项目视图下按钮隐藏，
    否则它在那一屏没有意义、只是多一个可选项。
    """
    app = read("app.js")
    html = read("index.html")
    css = read("style.css")
    assert 'id="ctx-home"' in html
    assert 'href="#/home"' in html
    assert "if (homeBtn) homeBtn.hidden = !currentProject();" in app
    assert "setProject(PROJECT_ALL, { rerender: false });" in app
    # 放行默认跳转，同时用 JS 清作用域；不能 e.preventDefault() 后只清状态不跳
    assert 'btn.addEventListener("click", () => {' in app
    # 与右侧项目切换器同档高度，不制造第三个控件高度
    assert re.search(r"\.ctx-home \{[^}]*height: var\(--h-sm\)", css)
    # 窄屏只留箭头，但必须有可访问名称
    assert 'aria-label="返回工作台"' in html
    assert ".ctx-home .ctx-home-text { display: none; }" in css


def test_context_picker_scales_with_many_projects():
    """项目变多时，切换器不能退化成一条无限长的原生下拉。

    原生 <select> 有 100+ 项时既不能搜索也没有高度上限，浮层必须：
    有搜索框、限制渲染条数、列表自身滚动，键盘可选可关。
    """
    app = read("app.js")
    html = read("index.html")
    css = read("style.css")
    # 触发器是按钮 + 浮层，不再把全部项目塞进 <option>
    assert 'aria-haspopup="listbox"' in html
    assert 'id="ctx-search"' in html and 'id="ctx-list"' in html
    assert "<option" not in html
    # 上下文条自身不再拼 <option>（其它页面的原生 select 不受影响）
    assert "projects.map(p => `<option" not in app
    assert "function ctxProjects()" in app
    # 渲染上限 + 剩余提示，避免一次插上千个节点
    assert "const CTX_LIST_MAX = 50;" in app
    assert "还有 ${rest} 个，输入关键字继续筛选" in app
    # 列表自身滚动，不能把页面撑长
    assert re.search(r"\.ctx-list\s*\{[^}]*max-height", css)
    assert re.search(r"\.ctx-list\s*\{[^}]*overflow-y", css)
    # 键盘：下箭头 / 上箭头 / 回车 / Esc
    for key in ("ArrowDown", "ArrowUp", "Enter", "Escape"):
        assert '"%s"' % key in app


def test_context_picker_survives_double_render_on_same_route():
    """navigate() 对同一页会渲染两次，浮层不能被第二次渲染无条件关掉。"""
    app = read("app.js")
    assert 'const routeSig = name + "/" + (arg || "");' in app
    assert "if (routeSig !== state._ctxRoute) {" in app


def test_native_selects_are_visually_replaced():
    """全站单选框统一走自绘触发器，原生 <select> 不再直接露出系统弹层。

    原生弹层是系统绘制：方角、无阴影、与设计令牌无关，这就是"下拉框生硬"
    的来源。做法是保留原生控件（取值 / 表单 / 无障碍不变），叠一层自绘 UI。
    """
    app = read("app.js")
    css = read("style.css")
    # 保留原生控件承担语义，只是视觉隐藏
    assert "function selMount(el)" in app
    assert 'el.classList.add("sel-native");' in app
    assert 'el.dataset.selUi = "1";' in app
    assert re.search(r"\.sel > select\.sel-native\s*\{[^}]*opacity:\s*0", css)
    # 单选与多选分流：多选走「标签 + 勾选浮层」，不沿用原生列表框
    assert "if (el.multiple) mselMount(el);" in app
    assert "else selMount(el);" in app
    # 写入回到原生控件，既有 .value / change 依赖不受影响
    assert 'el.dispatchEvent(new Event("change", { bubbles: true }));' in app
    # 代码直接赋值时触发器要跟着变（否则显示旧值）
    assert 'for (const prop of ["value", "selectedIndex"])' in app
    # 浮层样式与上下文条同源：同一套令牌
    assert re.search(r"\.sel-pop\s*\{[^}]*box-shadow:\s*var\(--shadow-3\)", css)
    assert re.search(r"\.sel-trigger\s*\{[^}]*height:\s*var\(--h-ctl\)", css)


def test_multiselect_uses_tags_and_checklist_not_ctrl_click():
    """原生 <select multiple> 必须按住 Ctrl，点第二项会把第一项取消。

    改成「已选标签 + 勾选浮层」后：连续点击直接累加，不依赖修饰键；
    原生控件仍留在 DOM 里维护 selected，页面里的 option:checked 取值不变。
    """
    app = read("app.js")
    css = read("style.css")
    assert "function mselMount(el)" in app
    assert "function mselToggle(el, idx)" in app
    # 连续点选只更新那一行，重建列表会把正在点击的节点换掉、后续点击丢失
    assert 'const row = _openMulti.pop.querySelector(`.msel-opt[data-i="${idx}"]`);' in app
    assert 'opt.selected = !opt.selected;' in app
    # 用户可见文案里不该再教用户按住 Ctrl（注释保留原因说明）
    assert "选择图片（按住 Ctrl" not in app
    assert "图片（按住 Ctrl" not in app
    # 标签 / 勾选 / 浮层三件套都要有样式，且不写死色值
    for name in (".msel-trigger", ".msel-chip", ".msel-box", ".msel-opt"):
        assert re.search("\\" + name + r"\s*\{", css), name
    # 宽触发器（整行卡片）不能把浮层拉成一块白板
    assert "const isMulti = pop.classList.contains(\"msel-pop\");" in app
    assert "const cap = Math.min(420, window.innerWidth - 16);" in app


def test_scroll_reposition_covers_both_pickers():
    """多选浮层刚接入时只认 _openSel，滚动页面浮层会卡在原地。"""
    app = read("app.js")
    assert "const open = _openSel || _openMulti;" in app


def test_hide_utility_and_inline_display_do_not_fight():
    """u-hide 写成 .u-hide.u-hide（0,2,0）压过组件规则。

    因此 JS 只改 style.display 是无效的：类名还在，元素永远 display:none。
    曾经把「手动选择图片」和提示词详情三个标签页一起卡死，统一走 setShown()。
    """
    app = read("app.js")
    css = read("style.css")
    assert ".u-hide.u-hide { display: none; }" in css
    assert "function setShown(el, shown)" in app
    # setShown 必须同时摘掉类名，否则高优先级规则仍然生效
    assert 'el.classList.toggle("u-hide", !shown);' in app
    # 不允许再有绕过 setShown 的直接 display 赋值（读状态可以用 classList）
    bad = [ln.strip() for ln in app.splitlines()
           if ".style.display =" in ln and "setShown" not in ln
           and not ln.strip().startswith("//")
           and ln.strip() != 'el.style.display = shown ? "" : "none";']
    assert not bad, bad[:5]
    # 折叠态判断也读 classList，不能读 style.display（两者已不同步）
    assert 'items.classList.contains("u-hide")' in app


def test_prompt_detail_header_and_toolbar_are_aligned():
    """提示词详情头部曾有两个布局缺陷。

    1) 标题 h3 用 u-f2(flex:2) 占满整行，版本号被推到卡片右缘，看起来像悬空徽标；
    2) 编辑工具行里 .u-f0 展开成 flex:0 1 0%（基准宽 0 且可收缩），
       「五模块展开 / 原文」被压成两行（实测高 68px），与旁边 28px 按钮、
       20px 说明文字基线全错开。

    现在标题与版本标签相邻，标签条走 28px 紧凑档，三者同高同线。
    """
    app = read("app.js")
    css = read("style.css")
    assert '<div class="prompt-head">' in app
    assert 'class="tabs u-m0 tabs-inline" id="p-vtabs"' in app
    assert 'class="tabs sm u-m0 u-f0" id="p-edit-tabs"' in app
    # flex:0 会变成 0 1 0%，必须显式 0 0 auto 才能按内容取宽
    assert ".u-f0.u-f0 { flex: 0 0 auto; }" in css
    assert re.search(r"\.tabs\.sm \.tab \{[^}]*height: var\(--h-sm\)", css)
    # 标题不再靠 flex 值撑开
    assert '<h3 class="u-f2 u-m0">${esc(name)}</h3>' not in app


def test_select_picker_has_keyboard_and_viewport_guards():
    app = read("app.js")
    css = read("style.css")
    for key in ("ArrowDown", "ArrowUp", "Home", "End", "Enter", "Escape"):
        assert '"%s"' % key in app
    # 浮层固定在视口坐标里，父容器有 overflow 也不会被裁
    assert re.search(r"\.sel-pop\s*\{[^}]*position:\s*fixed", css)
    assert "function selPopPosition(btn, pop)" in app
    # 选项过多时才有搜索框，避免三个选项也让人打字
    assert "const needSearch = all.length > 8;" in app
    assert "const SEL_MAX_ITEMS = 300;" in app


def test_every_page_responds_to_project_switch():
    """切换右上角项目后，每一页都要有可感知的变化，不能只有工作台跟着变。

    列表页按当前项目收口；全局共享资源页（提示词库、提示词生成）不能过滤
    数据，但必须显式说明"这页不随项目切换"，否则用户会以为切换失效。
    """
    app = read("app.js")
    # 全局共享页：说明条而不是硬过滤
    assert "function sharedScopeBar(" in app
    assert 'sharedScopeBar("提示词库不属于单个项目' in app
    assert 'sharedScopeBar("对话与生成的提示词属于全站资源' in app
    # 列表页：作用域说明条
    assert "function projectScopeBar(" in app
    for anchor in ('projectScopeBar("新建运行只列出当前项目的图片集',
                   'projectScopeBar("可选运行、裁判任务与迭代任务都只显示当前项目的记录',
                   'projectScopeBar("标注任务按当前项目收口',
                   'projectScopeBar("只列出当前项目的运行、真值任务与评估记录',
                   'projectScopeBar("只列出当前项目的已完成运行'):
        assert anchor in app, anchor
    # 项目与图片集：选了项目就收口成该项目下的图片集，并能一键回到全部项目
    assert 'id="pj-show-all"' in app
    assert 'scoped.flatMap(p => p.datasets || [])' in app
    # 字段提取的运行下拉必须按项目收口（原来用未过滤的 runs.items）
    assert "const done = projectRuns(runs.items).filter(r => r.done + r.failed > 0);" in app
    # 裁判任务卡片与迭代任务列表都要收口
    assert "renderJudgeJobs((jobsData.items || []).filter(j => runIds.has(j.run_id)));" in app
    assert 'const items = (data.items || []).filter(job => inProject({ ref: job.dataset || "" }));' in app


def test_home_has_single_primary_action():
    """M2：工作台首屏只能有一个主行动。

    旧版首屏有 13 个并列可点入口——示例导览 4 张卡 + 使用流程 7 张卡 + 待办 2 条，
    用户不知道该点哪个。现在由一张主行动卡承担「当前该做什么」。
    """
    app = read("app.js")
    home = app[app.index("function renderHome("):app.index("// ---------------------------------------------------------------- 新手引导")]
    # 主行动卡是整页唯一的 primary。M4 把 heroAction 拆成三个运行时互斥的分支：
    # 加载失败重试 / 「继续最近项目」（带 data-open-project）/ 普通跳转。
    assert home.count('class="btn primary"') == 3
    assert "const heroAction = hero.retry" in home
    assert '? `<button class="btn primary" id="home-retry"' in home
    # 主行动永远指向流程的第一处缺口：项目视图取 entry.nextStep，全部项目视图取全局前置
    assert "(isAll ? allProjectsHero(d, entries, sitesReady) : projectFlowHero(entry))" in home
    assert 'action: "去配置", hash: "#/config"' in app
    assert "const next = entry.nextStep;" in app
    # 待办不再重复「还没有模型站点」——那已经是主行动卡的内容
    assert "还没有可用的模型站点" not in home
    # 待办按钮全部降为次级，base 类里不含 primary
    assert 'class="btn small${i === 0 ? " primary" : ""}"' not in home


def test_home_flow_rail_is_read_only_status():
    """流程 7 步是「状态」不是「入口」，不能再做成 7 张互斥的可点卡片。"""
    app = read("app.js")
    css = read("style.css")
    home = app[app.index("function renderHome("):app.index("// ---------------------------------------------------------------- 新手引导")]
    # 流程轨是胶囊，不是原来的整块卡片
    assert 'class="home-step ${s.done ? "done" : ""} ${entry.nextStep === s ? "todo" : ""}${s.shared ? " shared" : ""}"' in home
    assert 'aria-current="step"' in home
    # 单项目视图才渲染流程轨；全部项目视图由项目卡承担进度展示
    assert 'const railHtml = isAll ? "" :' in home
    # 样式：胶囊 + 窄屏横向滚动
    assert ".home-step {" in css
    assert "border-radius: 999px" in css
    assert "flex-wrap: nowrap; overflow-x: auto;" in css


def test_home_demo_is_a_single_strip_not_a_four_step_tour():
    """示例项目导览曾用 4 张卡复述一遍流程，与 7 步流程条重复。"""
    app = read("app.js")
    home = app[app.index("function renderHome("):app.index("// ---------------------------------------------------------------- 新手引导")]
    assert 'class="home-demo"' in home
    # 旧的四步导览卡必须消失
    assert 'id="demo-eval"' not in home
    assert "示例项目导览" not in home
    # 保留两个真实动作：创建 / 运行示例
    assert 'id="demo-create"' in home
    assert 'id="demo-run"' in home


def test_home_hero_reflects_real_progress():
    """主行动卡的文案必须由真实数据决定，不能写死。"""
    app = read("app.js")
    home = app[app.index("function renderHome("):app.index("// ---------------------------------------------------------------- 新手引导")]
    for guard in ("if (!sitesReady) return {", "if (!entries.length) return {"):
        assert guard in app, guard
    # 单项目视图的主行动来自该项目自己的第一步缺口
    for guard in ("const reviewDone =", "const judgeDone =", "const next = entry.nextStep;"):
        assert guard in app, guard
    # 主行动与流程轨用同一份 nextStep，避免两处状态打架
    assert "(isAll ? allProjectsHero(d, entries, sitesReady) : projectFlowHero(entry))" in home
    assert "entry.steps.map((s, i) =>" in home


def test_home_all_projects_renders_project_cards_with_progress():
    """M4：全部项目视图中央是项目列表，每张卡都显示自己的当前步骤。"""
    app = read("app.js")
    assert "function projectCardHtml(entry)" in app
    assert 'class="home-proj"' in app
    assert "data-open-project=" in app
    assert "第 ${index} 步 · ${next.name}" in app
    assert "entry.steps.map((step, i) =>" in app
    assert "function loadHomeProgress(d)" in app
    assert "ensureProjects(true)" in app


def test_home_project_progress_is_computed_from_project_data():
    """步骤状态必须来自该项目的图片集、运行、审核、裁判与优化记录。"""
    app = read("app.js")
    assert "function projectFlowSteps(d, project, runs, latest, review, job, optCount)" in app
    for guard in ("const reviewDone =", "const judgeDone =", "const judged = Math.max(0, eligible - pending);",
                  "projectRuns = runs.filter(r => (r.dataset_project || refProject(r.dataset)) === project.name)",
                  "const name = runProject.get(opt.source_run);",
                  "optCounts.get(project.name) || 0"):
        assert guard in app, guard
    # 配置模型 / 生成提示词是全站共用：保留步骤但必须显式标注
    assert 'shared: true' in app
    assert "全站共用" in app


def test_home_project_list_pages_ten_with_search():
    """全部项目每页 10 条 + 名称搜索：项目多了不能把首屏拉成无底长页。"""
    app = read("app.js")
    assert "const PROJECT_PAGE_SIZE = 10;" in app
    assert "Math.ceil(shown.length / PROJECT_PAGE_SIZE)" in app
    assert "shown.slice(start, start + PROJECT_PAGE_SIZE)" in app
    assert 'placeholder="搜索项目名称…"' in app
    assert "e => String(e.name).toLowerCase().includes(q)" in app
    assert 'id="home-pj-pager"' in app
    assert "data-pj-page" in app
    assert "state._pjPage = 1;" in app
    # 搜索只过滤名称，不匹配说明文字，避免搜「说明」里的词命中一堆无关项目
    assert 'el.hidden = !!q' not in app
    assert '$$("#home-projects .home-proj")' not in app


def test_home_project_card_switches_context_in_place():
    """方案 2A：点项目卡原地把工作台切到该项目；修饰键保留新标签打开。"""
    app = read("app.js")
    assert 'e.target.closest("[data-open-project]")' in app
    assert "setProject(open.dataset.openProject);" in app
    assert 'href="#/project/${encodeURIComponent(entry.name)}" data-open-project=' in app
    # 单项目视图可回到全部项目
    assert 'id="home-all-projects"' in app
    assert "setProject(PROJECT_ALL)" in app


def test_home_cache_is_versioned_and_carries_progress():
    """缓存升级到 v2：旧版只存 dashboard，新版必须同时存项目进度。"""
    app = read("app.js")
    assert "cached.v === 2 && cached.d" in app
    assert "JSON.stringify({ v: 2, d, pp })" in app
    assert 'get("/api/runs")' in app
    assert 'get("/api/judge-jobs")' in app
    assert 'get("/api/prompt-ai/optimizations")' in app
    assert "/reviews`" in app


def test_tables_are_wrapped_for_horizontal_scroll():
    app = read("app.js")
    assert '<div class="tbl-scroll"><table class="tbl">' in app
    assert app.count('<div class="tbl-scroll">') >= 10
    assert "</table></div>" in app


def test_skeleton_component_exists():
    app = read("app.js")
    css = read("style.css")
    assert "function skeleton(lines, kind)" in app
    assert 'role="status" aria-label="加载中"' in app
    assert ".skeleton {" in css
    assert "@keyframes sk-shimmer" in css

def test_large_grid_renders_in_chunks():
    app = read("app.js")
    assert "const CHUNK = 120;" in app
    assert "requestAnimationFrame(paint)" in app
    assert "insertAdjacentHTML" in app
    assert "bindWhenDone" in app


def test_guide_renders_immediately_and_reuses_root():
    app = read("app.js")
    css = read("style.css")
    assert "async function renderGuideStep" not in app
    assert "function ensureTourRoot()" in app
    assert "if (root) return root;" in app
    assert "function locateTourTarget(step, seq)" in app
    assert "function isTourVisible(el)" in app
    assert "function stepGuide(delta)" in app
    assert "spot.style.transform = " in app
    assert "will-change: transform" in css
    assert ".tour-spot.smooth" in css


def test_guide_nav_hops_guard_against_stale_hashchange():
    app = read("app.js")
    assert "hops: 0" in app
    assert "if (_tour.hops > 0) _tour.hops--;" in app
    assert "my.hops++;" in app


def test_guide_keeps_bubble_inside_viewport_for_tall_targets():
    app = read("app.js")
    # 目标比可视区高时不能居中滚动（页头会被顶出屏幕），要按锚点顶部对齐
    assert "function scrollTourTarget(el)" in app
    assert "function tourViewport()" in app
    assert "function scrollByInstant(delta)" in app
    start = app.index("function scrollTourTarget(el)")
    end = app.index("function scrollByInstant(delta)")
    body = app[start:end]
    assert "scrollIntoView" not in body
    assert "rect.height <= avail" in body

    # 高亮框必须严格等于「目标 ∩ 可视区」：曾经为了给气泡让位而收缩高亮，
    # 结果框跑到目标外面（第 3 步切掉标题、第 6 步框在按钮上方 60px 的空块）。
    pos = app[app.index("function positionTour(root, target, my)"):app.index("function locateTourTarget(")]
    assert "function placeBubble(" in app
    assert "const left = Math.max(r.left - pad, vp.left);" in pos
    assert "const right = Math.min(r.right + pad, vp.right);" in pos
    assert "const top = Math.max(r.top - pad, vp.top);" in pos
    assert "const bottom = Math.min(r.bottom + pad, vp.bottom);" in pos
    # 不允许再出现「按气泡位置收口 / 撑高高亮」的旧逻辑
    assert "by - gap" not in pos
    assert "MIN_SPOT" not in pos
    assert "limit" not in pos

    # 气泡择位顺序：下 → 右 → 左 → 上，放不下时限高滚动，绝不盖住目标
    bubble = app[app.index("function placeBubble("):app.index("function positionTour(")]
    assert 'const order = ["below", "right", "left", "above"];' in bubble
    assert "shrink: h" in bubble
    assert "bubble.style.maxHeight = pos.shrink" in pos


def test_guide_target_lookup_does_not_waste_budget():
    app = read("app.js")
    loc = app[app.index("function locateTourTarget("):app.index("function applyTourTarget(")]
    # 目标 DOM 实测 30-80ms 就绪：不能「先白等一段再回退到 entry」，
    # 旧实现的 entryProbe=400 让每一步都要 500ms 以上框才到位。
    assert "entryProbe" not in loc
    assert "entryAfter" not in loc
    assert "const totalBudget = step.entry ? 2500 : 900;" in loc
    assert "setTimeout(check, elapsed < 200 ? 24 : 50);" in loc


def test_guide_does_not_flash_through_center_between_steps():
    app = read("app.js")
    body = app[app.index("function renderGuideStep()"):app.index('// ---------------------------------------------------------------- 配置页')]
    assert "function pinTourBubble(bubble)" in app
    # 有目标的步骤不再先清空高亮再居中，避免「框晚到 + 气泡跳一下」
    assert "pinTourBubble(bubble);" in body
    assert 'bubble.classList.add("center");' not in body.split("pinTourBubble(bubble);")[1]
    # 目标缺失时不留上一帧的旧框
    apply_body = app[app.index("function applyTourTarget("):app.index("function renderGuideStep(")]
    assert "spot.hidden = true;" in apply_body


def test_guide_step2_highlights_site_card_not_whole_list():
    app = read("app.js")
    # 高亮整块 #c-sites 时，站点越多目标越高，气泡只能被挤到边缘
    assert 'hash: "#/config", selector: "#c-sites .site-card", entry: "#c-add-site"' in app


def test_guide_bubble_is_draggable():
    app = read("app.js")
    css = read("style.css")
    assert "function bindTourDrag(root)" in app
    assert "bindTourDrag(root);" in app
    assert "setPointerCapture" in app
    assert "releasePointerCapture" in app
    assert "dragPos" in app
    assert "cursor: grab" in css
    assert ".tour-bubble.dragging" in css


def test_guide_arrows_do_not_hijack_typing():
    app = read("app.js")
    assert "function isTourTyping(e)" in app
    assert "if (isTourTyping(e)) return;" in app
    assert "t.isContentEditable" in app


def test_zoom_uses_dom_not_inner_html():
    app = read("app.js")
    assert 'img.src = src;' in app
    assert 'm.setAttribute("aria-modal", "true")' in app
    assert 'm.innerHTML = `<img src="${src}">`' not in app

def test_help_body_renders_semantic_blocks():
    app = read("app.js")
    css = read("style.css")
    # \u672f\u8bed\u8868\u3001\u6b65\u9aa4\u3001\u5217\u8868\u3001\u4ee3\u7801\u5757\u3001\u95ee\u7b54\u90fd\u8981\u6709\u81ea\u5df1\u7684\u7ed3\u6784\uff0c\u4e0d\u80fd\u518d\u662f\u4e00\u4e2a pre \u5806\u5b57
    for fn in ("function parseHelpBody(lines, title)",
               "function helpCollectTerms(src, i)",
               "function helpBlocksHtml(blocks)",
               "function helpCodeHtml(text)"):
        assert fn in app, fn
    assert 'type: "glossary"' in app and 'type: "step"' in app and 'type: "qa"' in app
    assert 'class="help-table"' in app and 'class="help-steps"' in app and 'class="help-faq"' in app
    assert 'class="help-code"' in app
    # \u6bb5\u843d\u6c47\u603b\u4e0d\u80fd\u518d\u4f9d\u8d56\u9884\u683c\u5f0f\u7a7a\u767d
    assert "white-space: pre-wrap" not in css[css.index(".help-body {"):css.index(".help-tablewrap {")]
    # \u672f\u8bed\u5217\u8981\u7ed9\u8db3\u5bbd\u5ea6\uff0c\u5426\u5219 output_format_hash \u4f1a\u88ab\u786c\u6298\u6210\u4e24\u884c
    assert ".help-table .help-term {" in css
    term = css[css.index(".help-table .help-term {"):]
    assert "min-width: 150px;" in term[:300]
    # \u884c\u5185\u6807\u8bc6\u7b26\u4e0d\u80fd\u7528 code\uff08\u4e0d\u6362\u884c\uff09\uff0c\u7a84\u5c4f\u4f1a\u649e\u51fa\u6a2a\u5411\u6eda\u52a8\u6761
    assert '<span class="help-ic">' in app and '<code class="help-ic">' not in app
    assert "overflow-wrap: anywhere;" in css[css.index(".help-ic {"):][:400]
    # \u7a84\u5c4f\u672f\u8bed\u8868\u6539\u4e3a\u4e0a\u4e0b\u6392\uff0c\u4e0d\u518d\u4e24\u5217\u6324\u6210\u4e00\u4e2a\u5b57
    mq = css[css.index("@media (max-width: 900px) {"):]
    assert ".help-table thead { display: none; }" in mq[:2000]
    assert ".help-table tr { display: block;" in mq[:2000]


def test_design_tokens_are_resolved_not_self_referential():
    css = read("style.css")
    root = css[css.index(":root {"):css.index("/* \u6697\u8272")]
    # \u81ea\u5f15\u7528\u4f1a\u8ba9\u53d8\u91cf\u4e3a\u7a7a\uff1a\u6d45\u8272\u4e0b\u5361\u7247\u6ca1\u5e95\u8272\u3001\u672f\u8bed\u8868\u6ca1\u5206\u9694\u7ebf
    for name in ("--panel", "--surface-2", "--surface-3", "--surface-hover",
                 "--border-strong", "--text3", "--primary-soft", "--success-soft",
                 "--danger-soft", "--warning-soft", "--code-key", "--code-str",
                 "--code-num", "--code-bool", "--img-bg-soft", "--overlay"):
        assert f"{name}: var({name})" not in root, name
        assert f"{name}:" in root, name
    # \u6697\u8272\u4e24\u5957\u90fd\u8981\u8986\u76d6 --panel
    assert css.count("--panel: ") >= 3


# ------------------------------------------------------------------ UIUX 审计护栏（M0）
INLINE_STYLE_BASELINE = 11
AUDIT_DIR = ROOT / "tools" / "audit"
AUDIT_SNAPSHOT = ROOT / ".sdd" / "audit" / "yven.json"
AUDIT_STATE = ROOT / ".sdd" / "audit" / "state-yven.json"


def test_inline_style_count_does_not_grow():
    """页面级内联样式是"按钮比别人高""文字出框"的根因。

    M0 基线 335 处，M3 收口到 11 处（仅保留含动态值的）。数字只许降不许升：新增内联样式会让后续改版无法用
    CSS 令牌统一收敛，因此这里用硬门槛挡住增量，而不是等项目结束再清理。
    """
    app = read("app.js")
    n = app.count('style="')
    assert n <= INLINE_STYLE_BASELINE, (
        "内联样式从 %d 涨到 %d 处；新增样式请写进 style.css 的组件类，"
        "并复用已有设计令牌" % (INLINE_STYLE_BASELINE, n))


def test_bytecode_check_script_requires_python38():
    """对拍脚本必须存在，且明确拒绝非 3.8 解释器。

    _src/_pyc/*.pyc 是 3.8 字节码（magic 550d），3.11+ 的 marshal 读不了，
    换个版本跑会直接报 bad marshal data；脚本自己挡掉比依赖人的记忆可靠。
    """
    script = AUDIT_DIR / "check_bytecode.ps1"
    assert script.is_file(), "缺少 tools/audit/check_bytecode.ps1"
    raw = script.read_bytes()
    # PowerShell 5.1 会用 GBK 读无 BOM 的 .ps1，中文注释会打乱语法，必须带 BOM
    assert raw.startswith(b"\xef\xbb\xbf"), ".ps1 需要 UTF-8 BOM 才能被 5.1 正确解析"
    src = raw.decode("utf-8-sig")
    # 非 3.8 直接失败，不能"尽力而为"地继续比
    assert '-ne "3.8"' in src, "必须校验解释器版本为 3.8"
    assert "verify_bytecode.py" in src
    # 无后端改动时跳过，避免把无关提交也卡在 3.8 上
    assert "-- app _src" in src
    assert 'git checkout -- tools/recover/bytecode_match.json' in src


def test_audit_probes_are_committed_and_read_only():
    """审计探针必须随仓库走，否则"改前快照"无法复现，回滚就没有依据。"""
    for name in ("ui_probe.py", "ui_state_probe.py", "check_baseline.py"):
        assert (AUDIT_DIR / name).is_file(), name
    # 只读约束：探针只通过 HTTP 看界面，不 import 产品后端、不发写请求，
    # 因此不可能改到 workspace 数据；它唯一的写动作是保存自己的快照。
    for name in ("ui_probe.py", "ui_state_probe.py"):
        src = (AUDIT_DIR / name).read_text(encoding="utf-8")
        assert "from app" not in src and "import app" not in src, name
        # 探针只能对产品发 GET：不得出现产品 API 路径的写动词。
        for verb in ('method="POST"', "method='POST'", 'method="DELETE"',
                     "method='DELETE'", 'method="PATCH"', "method='PATCH'"):
            assert verb not in src, (name, verb)
        # 唯一的 PUT 是 Chrome DevTools 的 /json/new（新建标签页）：
        # 每个 PUT 都必须紧挨着 json/new，多一处就说明有产品写请求。
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if 'method="PUT"' in line:
                near = "\n".join(lines[max(0, i - 2):i + 2])
                assert "/json/new" in near, (name, "发现非 DevTools 的 PUT")
        # 探针不许经产品的 api()/post()/del() 封装发请求（那是前端业务通道）
        for helper in ("post(", "put(", "del(", "api("):
            assert helper not in src, (name, helper)
        assert "json.dump(" in src, name


def test_audit_baseline_snapshot_is_present():
    """M0 的交付物是"改动前的可复现快照"，缺失则后续无法证明改善。"""
    import json

    assert AUDIT_SNAPSHOT.is_file(), "缺少 .sdd/audit/yven.json"
    assert AUDIT_STATE.is_file(), "缺少 .sdd/audit/state-yven.json"
    snap = json.loads(AUDIT_SNAPSHOT.read_text(encoding="utf-8"))
    assert snap.get("label") == "yven"
    assert len(snap.get("routes") or {}) >= 12
    for route, widths in (snap.get("routes") or {}).items():
        assert set(w for w in widths) >= {"1366", "1024", "800", "390"}, route
    state = json.loads(AUDIT_STATE.read_text(encoding="utf-8"))
    for key in ("failure_states", "slow_nav", "mobile_nav", "keyboard_nav", "interactive"):
        assert key in state, key
    # 已知缺陷必须被快照如实记录，否则门禁是假的
    assert any((v.get("pageOverflow") or 0) > 0
               for v in (snap.get("breakpoints") or {}).get("800", {}).values())
    assert not state["mobile_nav"].get("menuOpened")
    assert not state["keyboard_nav"].get("reaches_submenu")


def test_audit_baseline_gate_reports_known_defects():
    """门禁脚本在 Yven 快照上必须复现已知缺陷，不能"全绿"。"""
    import subprocess
    import sys as _sys

    proc = subprocess.run(
        [_sys.executable, str(AUDIT_DIR / "check_baseline.py"),
         "--snapshot", str(AUDIT_SNAPSHOT), "--state", str(AUDIT_STATE)],
        capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    assert "must_fix 未通过 9 项" in proc.stdout, proc.stdout[-800:]
    # 两个 guard 在基线上本来就成立，不能是红的
    assert "guard 未通过 0 项" in proc.stdout, proc.stdout[-800:]

# ------------------------------------------------------------------ M3 视觉收口
def test_empty_states_always_offer_next_step():
    """空态只写「暂无 XX」，用户不知道下一步点哪。

    M3 统一走 emptyState()，并且它必须同时支持两种下一步：
    跨页跳转（href）和聚焦页内表单（data-focus + 事件委托）。
    """
    app = read("app.js")
    for bad in ('<div class="muted">暂无', '<div class="muted u-p-12">暂无',
                '<div class="card muted">暂无'):
        assert bad not in app, bad
    assert "function emptyState(text, action, hash, focus)" in app
    assert 'data-focus="' in app
    # CSP 禁止内联事件，聚焦动作必须走委托
    assert "closest(\"[data-focus]\")" in app


def test_utility_classes_beat_component_rules_without_important():
    """工具类要能覆盖组件规则，又不能靠 !important。

    .card h3（0,1,1）会压过 .u-m0（0,1,0），实测导致行高从 28px 变 35px；
    因此工具类统一写成 .u-x.u-x（0,2,0），并在注释里写明原因。
    """
    css = read("style.css")
    doubles = re.findall(r"^\.(u-[a-z0-9-]+)\.\1 \{", css, re.M)
    assert len(doubles) >= 60, len(doubles)
    block = css[css.index(".u-m0.u-m0"):]
    assert ".u-m0.u-m0 { margin: 0; }" in block
    # 简写必须排在长写之前，否则 margin 会盖掉 margin-top
    assert block.index(".u-m0.u-m0") < block.index(".u-mt-8.u-mt-8")

def test_dialog_width_is_content_sized_not_full_page():
    """确认框不能铺满 980px。

    原 `.dlg` 是 `width:100%; max-width:980px`，一句「确定删除？」也被撑成
    980px，正文挤在左边一小条、右侧大片空白。现在默认窄档 440px，
    只有左右对比/多字段表单显式声明 `{ wide: true }`。
    """
    css = read("style.css")
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(r"\.dlg \{([^}]*)\}", plain)
    assert m, "缺少 .dlg 规则"
    body = m.group(1)
    assert "width: min(440px, 100%);" in body, body
    assert "max-width: 980px" not in body
    # 宽档必须靠显式修饰类，不能回到全局 width:100%
    wide = re.search(r"\.dlg\.dlg-wide \{([^}]*)\}", plain)
    assert wide and "min(980px" in wide.group(1)
    app = read("app.js")
    assert 'const sizeClass = opts.wide ? " dlg-wide" : "";' in app
    # 只有两处真正的宽内容：优化建议详情（左右对比）、生成优化建议（多字段表单）
    assert app.count("{ wide: true }") == 2
    # 按钮靠右成组，不横跨整个弹窗
    actions = re.search(r"\.dlg \.dlg-actions \{([^}]*)\}", plain)
    assert actions and "justify-content: flex-end;" in actions.group(1)


def test_fixed_width_grids_collapse_on_narrow_screen():
    """双类名栅格在 390px 下必须折叠成单列。

    `.u-gtc-260.u-gtc-260`（0,2,0）权重高于窄屏里的 `.grid-2`（0,1,0），
    不单独覆盖就会保留 260px 左栏，把整页撑出 188px 横向滚动条
    （实测 docW=563 vs vw=375）。
    """
    css = read("style.css")
    mq = css[css.index("@media (max-width: 760px) {"):]
    assert ".grid.u-gtc-260.u-gtc-260" in mq[:4000]
    assert "grid-template-columns: minmax(0, 1fr);" in mq[:4000]

def test_default_model_select_rebuilds_when_models_edited():
    """配置页「默认站点 / 模型」必须跟随站点卡片的模型输入实时重建。

    回归背景：data-f 的 oninput 过去只把值写回内存数组，没有重建 #c-model，
    于是用户刚加进「可用模型」的第二行要刷新整页才会出现在默认下拉里，
    看起来像「上面配了两个、下面只有一个」。
    """
    app = read("app.js")
    assert 'if (inp.dataset.f === "models") inp.addEventListener("input", refreshDefaultSelect);' in app
    # 站点名是 optgroup 与选项值前缀，改动时也要刷新；放在 change 上避免输入抖动
    assert 'if (inp.dataset.f === "name") inp.addEventListener("change", refreshDefaultSelect);' in app


def test_default_model_select_falls_back_to_first_real_option():
    """当前默认模型已不在列表时，不能把 select 置成空值。

    过去固定回退到 smValue(cfg)；如果用户删掉了那个模型，值就不存在，
    原生 select 显示空白、自绘触发器停在旧文案，看起来像下拉坏了。
    """
    app = read("app.js")
    start = app.index("const refreshDefaultSelect = () => {")
    end = app.index("const saveCfg = async () => {")
    body = app[start:end]
    assert "if (all.includes(cur)) sel.value = cur;" in body
    assert "else if (all.includes(smValue(cfg))) sel.value = smValue(cfg);" in body
    assert 'else sel.value = all[0] || "";' in body


def test_site_card_textareas_share_one_grid_row():
    """站点卡片里「API Keys」与「可用模型」必须同排、同高。

    曾经用 .row（align-items:flex-end）：左栏下面多一行「已保存：sk-…」，
    右栏没有，于是右栏输入框被压得更低，视觉上一高一低。
    现在改成两列网格，标签/输入框/脚注各占一整行，高度由行决定。
    """
    app = read("app.js")
    assert '<div class="site-fields">' in app
    assert app.count('class="site-fields"') == 1
    # 两个 textarea 与两处脚注必须是同级节点，网格才能对齐
    start = app.index('<div class="site-fields">')
    end = app.index("</div>", app.index('class="site-saved"', start))
    block = app[start:end]
    assert block.count("<textarea") == 2
    assert 'class="site-saved"' in block
    assert "u-mt-2" not in block

    css = read("style.css")
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(r"\.site-card \.site-fields \{([^}]*)\}", plain)
    assert m, "缺少 .site-card .site-fields 规则"
    body = m.group(1)
    assert "display: grid;" in body
    assert "grid-template-columns: 1fr 1fr;" in body
    assert "align-items: stretch;" in body
    # 窄屏必须折叠成单列，否则右栏被压到不可读
    assert ".site-card .site-fields { grid-template-columns: minmax(0, 1fr); }" in plain


def test_prompt_ai_layout_no_overflow_and_even_controls():
    """提示词生成页的排版回归。

    1) 面板高度曾是 calc(100vh - 100px)，实际顶栏 52 + 上下文条 36 + 容器内边距
       24 + 页标题 ≈ 154px，底边压出视口，发送按钮要滚动才看见 → 改由 .pai-page
       撑满剩余高度。
    2) .pai-session-meta 曾写 flex:0，被压成 0 宽，模板标签折两行、模型下拉掉到
       第三行，头部撑到 135px → 改成 flex:0 0 auto + nowrap。
    3) 工具条里上传/选图是 28px、发送是 36px，一行两档高度 → 统一 36px。
    4) 输入框 resize:vertical 可拖拽，拖一下就把工具条挤出去 → 固定高度。
    """
    app = read("app.js")
    assert '<div class="pai-page">' in app
    # 工具条三个按钮不能再是 small 档
    start = app.index('<div class="pai-input-bar">')
    end = app.index('id="pai-dspick"', start)
    bar = app[start:end]
    assert 'class="btn small" id="pai-upload"' not in bar
    assert 'class="btn small" id="pai-fromds"' not in bar
    assert 'class="btn" id="pai-upload"' in bar
    assert 'class="btn" id="pai-fromds"' in bar

    css = read("style.css")
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    page = re.search(r"\.pai-page \{([^}]*)\}", plain)
    assert page, "缺少 .pai-page 规则"
    assert "display: flex;" in page.group(1)
    assert "calc(100vh - 154px)" in page.group(1)

    meta = re.search(r"\.pai-session-meta \{([^}]*)\}", plain)
    assert meta
    assert "flex: 0 0 auto;" in meta.group(1)
    assert "flex-wrap: nowrap;" in meta.group(1)

    ta = re.search(r"\.pai-input-bar textarea \{([^}]*)\}", plain)
    assert ta
    assert "resize: none;" in ta.group(1)

    bar_css = re.search(r"\.pai-input-bar > \.row \{([^}]*)\}", plain)
    assert bar_css
    assert "align-items: center;" in bar_css.group(1)
    # 窄屏下 .row > * 的 120px 最小宽度会把发送挤到第二行
    assert ".pai-input-bar > .row > * { min-width: 0; }" in plain


def test_viewer_uses_fixed_height_workspace():
    """结果查看器：整页不再滚动，左右两栏各自内部滚动。

    旧布局（1440×900 实测）文档高 1452px，要滚三次才看得到审核保存；
    左栏卡片被 grid 拉到 1118px 而列表只有 770px，底部空 283px；
    顶部 4 个开关 + 5 个按钮 + 元信息挤一行，折成两行，「返回列表」被顶到
    第二行单独一个。现在改为定高工作区 + 头部两行 + 面板按内容排。
    """
    app = read("app.js")
    assert '<div class="viewer-page">' in app
    assert 'class="card v-head"' in app
    assert 'class="v-head-meta"' in app
    assert 'class="v-head-actions"' in app
    # 原图的 .row 两栏结构应被替换，避免再次被 .row > * 的 min-width 影响
    start = app.index('route("viewer"')
    end = app.index("async function showImage", start)
    block = app[start:end]
    assert "checks u-f3 u-jc-fe" not in block
    assert 'class="v-togs"' in block
    # 列表项改为「名称 + 圆点」两段，长文件名用省略号而不是换行
    assert '<span class="img-name">' in block
    assert "img-meta" in block
    assert 'id="v-list-meta"' in block

    css = read("style.css")
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    page = re.search(r"\.viewer-page \{([^}]*)\}", plain)
    assert page, "缺少 .viewer-page 规则"
    assert "display: flex;" in page.group(1)
    assert "calc(100vh - 136px)" in page.group(1)

    col = re.search(r"\.u-viewer-col \{([^}]*)\}", plain)
    assert col
    assert "flex-direction: column;" in col.group(1)
    assert "overflow: hidden;" in col.group(1)

    # 面板不能等高：JSON 700px+ 会把「原图」拉成一样高，下面空半屏
    panels = re.search(r"\.panels \{([^}]*)\}", plain)
    assert panels
    assert "align-items: flex-start;" in panels.group(1)

    # 窄屏要折叠成上下堆叠，左栏限高，否则一张图都看不到
    assert ".viewer-page { height: auto; min-height: 0; }" in plain
    assert ".u-viewer-col { max-height: 260px; }" in plain


def test_result_panel_leads_with_conclusion_not_raw_json():
    """结果查看器的「模型输出」必须先给结论，而不是把诊断对象摊成树。

    原始对象是「模型输出 + 诊断元数据」的混合体：raw 是一整段带转义的原文，
    source_json 与顶层重复，_meta 是运行参数。直接铺树，用户要在十几行
    机器字段里找「到底判了什么」。这里锁住几个关键约束，防止回退。
    """
    app = read("app.js")
    start = app.index("function resultPanel(")
    end = app.index("function jsonPanel(", start)
    body = app[start:end]

    # 结论卡的三段结构：状态行 / 结论正文 / 技术细节折叠区
    assert 'class="rv-top"' in body
    assert 'class="rv-summary"' in body
    assert 'class="rv-detail u-hide"' in body
    # 原始数据必须默认折叠，默认只显示结论
    assert "jsonTreeHtml(data)" in body
    assert "rv-detail-tog" in body
    # 场景键做中文映射，避免「是否存在目标/事件」与 image_quality 混排
    assert "SCENE_KEY_CN" in app
    assert 'image_quality: "图像质量"' in app
    # 解析失败时 objects 必为空，但不能说成「未检出目标」
    assert "data.parse_ok === false" in body
    # 上游调用错误优先于「未能解析为 JSON」
    assert "upstreamErr" in body

    css = read("style.css")
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sel in [r"\.result-panel \{", r"\.rv-summary \{", r"\.rv-obj \{", r"\.rv-scene-item \{"]:
        assert re.search(sel, plain), "缺少 " + sel
    # 结论要足够醒目：给的是 base 字号与 1.75 行高
    summary = re.search(r"\.rv-summary \{([^}]*)\}", plain)
    assert "font-size: var(--fs-base);" in summary.group(1)
    assert "line-height: 1.75;" in summary.group(1)


def test_viewer_json_panel_uses_result_panel():
    """查看器与试跑结果都要走结论卡；JSON 工具仍保留原始树。"""
    app = read("app.js")
    start = app.index('route("viewer"')
    end = app.index("// ---------------------------------------------------------------- 帮助页", start)
    block = app[start:end]
    assert "resultPanel(data)" in block
    assert "resultPanel(x.data)" in block
    # 「JSON 结果」标题改为面向用户的「模型输出」
    assert "JSON 结果 " not in block
    assert "模型输出" in block
    # 试跑卡片同样换成结论卡
    assert "resultPanel(it.result)" in app
