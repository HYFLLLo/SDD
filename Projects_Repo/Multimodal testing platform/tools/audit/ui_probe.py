"""UI/UX 审计探针：在真实浏览器里测量，不靠观感。

用法：
    python tools/audit/ui_probe.py --out .sdd/audit/before.json
    python tools/audit/ui_probe.py --label after --out .sdd/audit/after.json
    python tools/audit/ui_probe.py --diff .sdd/audit/before.json --out .sdd/audit/diff.json

只读：不改产品代码、不改 workspace 数据，只向运行中的服务发 GET/静态请求。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import sys
import tempfile
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

# 覆盖全部 18 条路由；深链用现有示例数据填充
ROUTES = [
    "#/home", "#/datasets", "#/prompts", "#/prompt-ai", "#/runs",
    "#/judge-iter", "#/config", "#/extract", "#/truth", "#/evals",
    "#/jsontool", "#/help",
]
WIDTHS = [1366, 1024, 800, 390]

# 断点空档检测：761..900 是当前唯一主断点 760 之上的可疑区间
BREAKPOINT_PROBES = [1366, 1200, 1024, 900, 860, 800, 780, 761, 760, 390]


def chrome_path() -> str:
    for p in CHROME_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    raise SystemExit("找不到 Chrome，可用 --chrome 指定")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_service(base: str, timeout: float = 20.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(base + "api/version", timeout=1)
            return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("服务未就绪：%s（请先 python run.py 或指定 --base" % base)


def contrast(fg: str, bg: str) -> float:
    def lum(hexcolor: str) -> float:
        h = hexcolor.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- 页内探针
PROBE_LAYOUT = r"""
(() => {
  const doc = document.documentElement;
  const hOver = doc.scrollWidth - doc.clientWidth;
  const offenders = [];
  document.querySelectorAll('#app *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > window.innerWidth + 1) {
      const over = Math.round(r.right - window.innerWidth);
      offenders.push({
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || '').slice(0, 48),
        over: over
      });
    }
  });
  offenders.sort((a, b) => b.over - a.over);

  // 所有容器的横向溢出（识别"被 overflow 兜住"的情况）
  const clipped = [];
  document.querySelectorAll('#app *').forEach(el => {
    if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0) {
      const cs = getComputedStyle(el);
      if (cs.overflowX !== 'visible') {
        clipped.push({
          cls: String(el.className || el.tagName).slice(0, 40),
          overflow: el.scrollWidth - el.clientWidth
        });
      }
    }
  });
  clipped.sort((a, b) => b.overflow - a.overflow);

  const title = document.querySelector('.page-title');
  return JSON.stringify({
    title: title ? title.innerText.trim().split('\n')[0] : null,
    scrollW: doc.scrollWidth,
    clientW: doc.clientWidth,
    pageOverflow: hOver,
    offenders: offenders.slice(0, 6),
    clippedContainers: clipped.slice(0, 4),
    textLen: (document.getElementById('app') || {}).innerText ?
             document.getElementById('app').innerText.trim().length : 0,
    // 只数"用户当前看得见"的主按钮：隐藏 tab 里的不算，
    // 否则一个页面放 5 个 tab、每 tab 一个主按钮会被误判成主行动不唯一。
    primaryBtns: [...document.querySelectorAll('#app .btn.primary')]
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0).length
  });
})()
"""

PROBE_CONTROLS = r"""
(() => {
  const heights = new Set(), fonts = new Set(), radii = new Set();
  const sel = '#app button, #app .btn, #app input, #app select, #app textarea';
  document.querySelectorAll(sel).forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.height > 0) heights.add(Math.round(r.height));
    const cs = getComputedStyle(el);
    fonts.add(cs.fontSize);
    radii.add(cs.borderRadius.split(' ')[0]);
  });
  const navH = new Set();
  document.querySelectorAll('#nav a').forEach(a => {
    const r = a.getBoundingClientRect();
    if (r.height > 0) navH.add(Math.round(r.height));
  });
  // 表单可用性
  const inputs = document.querySelectorAll('#app input:not([type=checkbox]):not([type=radio]), #app select, #app textarea');
  const withRequired = document.querySelectorAll('#app [required]').length;
  const withInvalid = document.querySelectorAll('#app [aria-invalid]').length;
  return JSON.stringify({
    heights: [...heights].sort((a, b) => a - b),
    fontSizes: [...fonts].sort(),
    radii: [...radii].sort(),
    navHeights: [...navH].sort((a, b) => a - b),
    fieldCount: inputs.length,
    requiredCount: withRequired,
    invalidCount: withInvalid
  });
})()
"""

PROBE_A11Y = r"""
(() => {
  const imgs = [...document.querySelectorAll('#app img')];
  const noAlt = imgs.filter(i => !i.hasAttribute('alt')).length;
  const clickableDiv = [...document.querySelectorAll(
    '#app div[onclick], #app .home-step, #app .home-proj, #app .dataset-row, #app .sess-item, #app .thumb')]
    .filter(el => !['A', 'BUTTON'].includes(el.tagName));
  const keyboardDead = clickableDiv.filter(el => {
    const ti = el.getAttribute('tabindex');
    return !el.hasAttribute('role') && (ti === null || Number(ti) < 0) && el.tagName === 'DIV';
  }).length;
  const dropdown = document.querySelector('.nav-dropdown');
  const menu = document.querySelector('.nav-dropdown-menu');
  const css = menu ? getComputedStyle(menu) : null;
  return JSON.stringify({
    imgTotal: imgs.length,
    imgNoAlt: noAlt,
    clickableDivTotal: clickableDiv.length,
    clickableDivKeyboardDead: keyboardDead,
    dropdownDisplay: css ? css.display : null,
    dropdownDisplayRule: css ? (css.display === 'none' ? 'hidden-by-default' : css.display) : null,
    focusVisibleRules: [...document.styleSheets].reduce((n, s) => {
      try { return n + [...s.cssRules].filter(r => (r.selectorText || '').includes(':focus-visible')).length; }
      catch (e) { return n; }
    }, 0)
  });
})()
"""


async def run_probe(base: str, chrome: str, out_path: str, label: str) -> dict:
    import websockets

    tmp = tempfile.mkdtemp(prefix="mmt-audit-")
    port = free_port()
    proc = subprocess_popen(chrome, tmp, port)
    result = {"label": label, "base": base, "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
              "routes": {}, "breakpoints": {}, "contrast": {}, "console": {}}
    try:
        wait_devtools(port)
        url = "http://127.0.0.1:%d/json/new?%s" % (port, urllib.parse.quote(base, safe=":/"))
        target = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, method="PUT"), timeout=10).read())

        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=1 << 26) as ws:
            state = {"mid": 0, "errors": []}

            async def call(method, params=None):
                state["mid"] += 1
                mid = state["mid"]
                await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("method") == "Runtime.exceptionThrown":
                        state["errors"].append(
                            str(msg["params"]["exceptionDetails"].get("text"))[:160])
                    if msg.get("id") == mid:
                        return msg

            async def evaluate(expr):
                r = await call("Runtime.evaluate",
                               {"expression": expr, "returnByValue": True, "awaitPromise": True})
                val = r.get("result", {}).get("result", {}).get("value")
                try:
                    return json.loads(val) if isinstance(val, str) else val
                except Exception:
                    return val

            await call("Runtime.enable")
            await call("Page.enable")
            await call("Network.enable")

            for width in WIDTHS:
                await call("Emulation.setDeviceMetricsOverride",
                           {"width": width, "height": 768, "deviceScaleFactor": 1,
                            "mobile": width < 500})
                for route in ROUTES:
                    await call("Page.navigate", {"url": base + route})
                    await asyncio.sleep(1.15)
                    layout = await evaluate(PROBE_LAYOUT) or {}
                    controls = await evaluate(PROBE_CONTROLS) or {}
                    a11y = await evaluate(PROBE_A11Y) or {}
                    entry = {
                        "title": layout.get("title"),
                        "pageOverflow": layout.get("pageOverflow"),
                        "offenders": layout.get("offenders", []),
                        "clippedContainers": layout.get("clippedContainers", []),
                        "textLen": layout.get("textLen"),
                        "primaryBtns": layout.get("primaryBtns"),
                        "heights": controls.get("heights", []),
                        "fontSizes": controls.get("fontSizes", []),
                        "radii": controls.get("radii", []),
                        "navHeights": controls.get("navHeights", []),
                        "fieldCount": controls.get("fieldCount"),
                        "requiredCount": controls.get("requiredCount"),
                        "invalidCount": controls.get("invalidCount"),
                        "imgNoAlt": a11y.get("imgNoAlt"),
                        "imgTotal": a11y.get("imgTotal"),
                        "clickableDivKeyboardDead": a11y.get("clickableDivKeyboardDead"),
                        "clickableDivTotal": a11y.get("clickableDivTotal"),
                        "dropdownDisplay": a11y.get("dropdownDisplay"),
                        "focusVisibleRules": a11y.get("focusVisibleRules"),
                    }
                    result["routes"].setdefault(route, {})[str(width)] = entry
                    bad = " OVERFLOW" if (entry["pageOverflow"] or 0) > 0 else ""
                    if entry["textLen"] == 0:
                        bad += " BLANK"
                    print("  %-14s %5d  over=%s%s" % (
                        route, width, entry["pageOverflow"], bad), flush=True)

            # 断点空档：只测 overflow，不测全量
            for width in BREAKPOINT_PROBES:
                await call("Emulation.setDeviceMetricsOverride",
                           {"width": width, "height": 768, "deviceScaleFactor": 1,
                            "mobile": width < 500})
                rec = {}
                for route in ("#/home", "#/runs", "#/help"):
                    await call("Page.navigate", {"url": base + route})
                    await asyncio.sleep(0.9)
                    layout = await evaluate(PROBE_LAYOUT) or {}
                    rec[route] = {"pageOverflow": layout.get("pageOverflow"),
                                  "offenders": layout.get("offenders", [])[:2]}
                result["breakpoints"][str(width)] = rec

            # 对比度：读取实际计算色值
            await call("Emulation.setDeviceMetricsOverride",
                       {"width": 1366, "height": 900, "deviceScaleFactor": 1, "mobile": False})
            for theme in ("light", "dark"):
                await call("Page.navigate", {"url": base + "#/runs"})
                await asyncio.sleep(0.8)
                await call("Runtime.evaluate", {"expression":
                           "document.documentElement.setAttribute('data-theme','%s')" % theme})
                await asyncio.sleep(0.35)
                pairs = await evaluate(r"""
                (() => {
                  const pick = (sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return null;
                    let bgEl = el, bg = 'rgba(0, 0, 0, 0)';
                    while (bgEl && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
                      bg = getComputedStyle(bgEl).backgroundColor;
                      bgEl = bgEl.parentElement;
                    }
                    return { fg: getComputedStyle(el).color, bg: bg };
                  };
                  return JSON.stringify({
                    muted: pick('#app .muted'),
                    primaryBtn: pick('#app .btn.primary'),
                    tag: pick('#app .tag'),
                    body: pick('#app .page-title')
                  });
                })()
                """)
                result["contrast"][theme] = pairs

            await call("Runtime.evaluate", {"expression": "1"})
            result["console"]["exceptions"] = state["errors"][:10]
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)

    # 对比度换算成比值
    for theme, pairs in list(result["contrast"].items()):
        converted = {}
        for key, val in (pairs or {}).items():
            if not val:
                continue
            try:
                fg = rgb_to_hex(val["fg"])
                bg = rgb_to_hex(val["bg"])
                converted[key] = {"fg": fg, "bg": bg, "ratio": round(contrast(fg, bg), 2)}
            except Exception:
                converted[key] = val
        result["contrast"][theme] = converted

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return result


def subprocess_popen(chrome: str, tmp: str, port: int):
    import subprocess
    return subprocess.Popen(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--user-data-dir=" + tmp, "--remote-debugging-port=" + str(port),
         "--no-first-run", "--window-size=1366,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def rgb_to_hex(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("#"):
        return value
    if value.startswith("rgb"):
        nums = [float(x) for x in value[value.index("(") + 1:value.index(")")].split(",")[:3]]
        return "#%02x%02x%02x" % tuple(int(round(n)) for n in nums)
    raise ValueError("unsupported color: %r" % value)


def wait_devtools(port: int, timeout: float = 20.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1)
            return
        except Exception:
            time.sleep(0.25)
    raise SystemExit("Chrome DevTools 未就绪")


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def diff(before: dict, after: dict) -> dict:
    """逐项对比，只报告"变差"与"变好"，不静默放过任何回归。"""
    issues = []
    fixed = []

    def cmp(name, b, a, lower_is_better=True, tol=0):
        if b is None or a is None:
            return
        if a == b:
            return
        better = (a < b) if lower_is_better else (a > b)
        if abs(a - b) <= tol:
            return
        (fixed if better else issues).append({"metric": name, "before": b, "after": a})

    for route, widths in before.get("routes", {}).items():
        for width, b in widths.items():
            a = after.get("routes", {}).get(route, {}).get(width)
            if not a:
                continue
            tag = "%s@%s" % (route, width)
            cmp(tag + " overflow", b.get("pageOverflow"), a.get("pageOverflow"))
            cmp(tag + " blank", 1 if b.get("textLen") == 0 else 0,
                1 if a.get("textLen") == 0 else 0)
            cmp(tag + " primaryBtns", b.get("primaryBtns"), a.get("primaryBtns"))
            cmp(tag + " imgNoAlt", b.get("imgNoAlt"), a.get("imgNoAlt"))
            cmp(tag + " keyboardDead", b.get("clickableDivKeyboardDead"),
                a.get("clickableDivKeyboardDead"))
            cmp(tag + " heightsVariants", len(b.get("heights") or []),
                len(a.get("heights") or []))
            cmp(tag + " fontVariants", len(b.get("fontSizes") or []),
                len(a.get("fontSizes") or []))
    for theme, pairs in before.get("contrast", {}).items():
        for key, b in (pairs or {}).items():
            a = after.get("contrast", {}).get(theme, {}).get(key)
            if not isinstance(b, dict) or not isinstance(a, dict):
                continue
            if "ratio" in b and "ratio" in a:
                cmp("%s contrast %s" % (theme, key), b["ratio"], a["ratio"],
                    lower_is_better=False, tol=0.05)
    return {"regressions": issues, "improvements": fixed,
            "before_label": before.get("label"), "after_label": after.get("label")}


def main() -> int:
    ap = argparse.ArgumentParser(description="UI/UX 审计探针（只读）")
    ap.add_argument("--base", default="http://127.0.0.1:8735/")
    ap.add_argument("--chrome", default="")
    ap.add_argument("--label", default="snapshot")
    ap.add_argument("--out", default=os.path.join(PROJECT, ".sdd", "audit", "snapshot.json"))
    ap.add_argument("--diff", default="", help="与已有快照对比，输出回归/改善")
    ap.add_argument("--fail-on-regression", action="store_true")
    args = ap.parse_args()

    if args.diff:
        before = load(args.diff)
        after = load(args.out) if os.path.isfile(args.out) else None
        if after is None:
            raise SystemExit("--diff 需要先有 --out 产物：%s" % args.out)
        report = diff(before, after)
        with open(args.out.replace(".json", "-diff.json"), "w",
                  encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print("\n回归 %d 项 / 改善 %d 项" % (
            len(report["regressions"]), len(report["improvements"])))
        for item in report["regressions"]:
            print("  REGRESS %-46s %s -> %s" % (
                item["metric"], item["before"], item["after"]))
        if args.fail_on_regression and report["regressions"]:
            return 1
        return 0

    base = args.base if args.base.endswith("/") else args.base + "/"
    wait_service(base)
    chrome = args.chrome or chrome_path()
    print("审计 %s（%s）" % (base, os.path.basename(chrome)))
    data = asyncio.run(run_probe(base, chrome, args.out, args.label))
    print("\n快照：%s" % args.out)

    overflows = sum(1 for r in data["routes"].values() for w in r.values()
                    if (w.get("pageOverflow") or 0) > 0)
    blanks = sum(1 for r in data["routes"].values() for w in r.values()
                 if w.get("textLen") == 0)
    dead = sum(1 for r in data["routes"].values() for w in r.values()
               if (w.get("clickableDivKeyboardDead") or 0) > 0)
    print("横向溢出 %d 例 / 空白页 %d 例 / 键盘不可达 %d 例" % (overflows, blanks, dead))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
