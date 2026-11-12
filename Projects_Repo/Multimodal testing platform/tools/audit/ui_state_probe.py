"""交互与状态探针：失败态、慢网、触屏下拉、键盘可达性。

与 ui_probe.py 互补：那个量"静态版式"，这个量"能不能用"。

用法：
    python tools/audit/ui_state_probe.py --out .sdd/audit/state-yven.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
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

# 需要"接口全挂时也要给出可理解反馈"的路由
FAIL_ROUTES = ["#/home", "#/datasets", "#/prompts", "#/runs",
               "#/judge-iter", "#/evals", "#/truth", "#/prompt-ai"]


def chrome_path() -> str:
    for p in CHROME_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    raise SystemExit("找不到 Chrome")


def wait_service(base: str, timeout: float = 20.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(base + "api/version", timeout=1)
            return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("服务未就绪：" + base)


async def probe(base: str, chrome: str) -> dict:
    import websockets

    out = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "base": base,
           "failure_states": {}, "slow_nav": {}, "mobile_nav": {},
           "keyboard_nav": {}, "interactive": {}}
    tmp = tempfile.mkdtemp(prefix="mmt-state-")
    port = 9701
    proc = __import__("subprocess").Popen(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--user-data-dir=" + tmp, "--remote-debugging-port=" + str(port),
         "--no-first-run", "--window-size=1366,900", "about:blank"],
        stdout=__import__("subprocess").DEVNULL,
        stderr=__import__("subprocess").DEVNULL)
    try:
        end = time.time() + 20
        while time.time() < end:
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        url = "http://127.0.0.1:%d/json/new?%s" % (port, urllib.parse.quote(base, safe=":/"))
        target = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, method="PUT"), timeout=10).read())
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=1 << 26) as ws:
            state = {"mid": 0}

            async def call(method, params=None):
                state["mid"] += 1
                mid = state["mid"]
                await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("id") == mid:
                        return msg

            async def ev(expr):
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
            await call("Emulation.setDeviceMetricsOverride",
                       {"width": 1366, "height": 900, "deviceScaleFactor": 1, "mobile": False})

            # 1) 失败态：所有 /api/* 断掉
            await call("Network.setBlockedURLs", {"urls": ["*/api/*"]})
            for route in FAIL_ROUTES:
                await call("Page.navigate", {"url": base + route})
                await asyncio.sleep(1.6)
                res = await ev(r"""
                (() => {
                  const app = document.getElementById('app');
                  const text = (app.innerText || '').trim();
                  const hasRetry = /重试|再试一次|刷新/.test(text);
                  const hasErr = !!document.querySelector('#app .msg.err, #app .error, #app [role=alert]');
                  return JSON.stringify({
                    textLen: text.length,
                    head: text.slice(0, 60),
                    blank: text.length === 0,
                    hasRetry, hasErr,
                    activeNav: (document.querySelector('#nav a.active') || {}).textContent || null
                  });
                })()
                """)
                out["failure_states"][route] = res or {}
                flag = "BLANK" if (res or {}).get("blank") else (
                    "NO-RETRY" if not (res or {}).get("hasRetry") else "ok")
                print("  失败态 %-14s %s" % (route, flag), flush=True)

            await call("Network.setBlockedURLs", {"urls": []})

            # 2) 慢网：切页后是否残留上一页内容
            await call("Network.emulateNetworkConditions",
                       {"offline": False, "latency": 900,
                        "downloadThroughput": 200000, "uploadThroughput": 200000})
            await call("Page.navigate", {"url": base + "#/home"})
            await asyncio.sleep(3.0)
            await call("Runtime.evaluate", {"expression": "location.hash='#/runs'"})
            await asyncio.sleep(0.7)
            slow = await ev(r"""
            (() => {
              const t = document.querySelector('.page-title');
              return JSON.stringify({
                title: t ? t.innerText.trim().split('\n')[0] : null,
                hasSkeleton: !!document.querySelector('#app .skeleton'),
                activeNav: (document.querySelector('#nav a.active') || {}).textContent || null
              });
            })()
            """)
            out["slow_nav"] = slow or {}
            await call("Network.emulateNetworkConditions",
                       {"offline": False, "latency": 0,
                        "downloadThroughput": -1, "uploadThroughput": -1})

            # 3) 触屏：「工具」下拉能否点开
            await call("Emulation.setDeviceMetricsOverride",
                       {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
            await call("Emulation.setTouchEmulationEnabled",
                       {"enabled": True, "maxTouchPoints": 5})
            await call("Page.navigate", {"url": base + "#/home"})
            await asyncio.sleep(2.0)
            await call("Runtime.evaluate", {"expression":
                       "document.getElementById('nav-toggle').click();1"})
            await asyncio.sleep(0.5)
            box = await ev("JSON.stringify((()=>{const r=document.querySelector('.nav-dropbtn')"
                           ".getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())")
            if box:
                await call("Input.dispatchTouchEvent",
                           {"type": "touchStart",
                            "touchPoints": [{"x": box["x"], "y": box["y"]}]})
                await call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                await asyncio.sleep(0.7)
            mobile = await ev(r"""
            (() => {
              const menu = document.querySelector('.nav-dropdown-menu');
              const cs = menu ? getComputedStyle(menu) : null;
              const links = menu ? menu.querySelectorAll('a').length : 0;
              return JSON.stringify({
                menuDisplay: cs ? cs.display : null,
                menuOpened: !!cs && cs.display !== 'none',
                submenuLinks: links,
                landedHash: location.hash
              });
            })()
            """)
            out["mobile_nav"] = mobile or {}
            print("  触屏「工具」: %s" % (out["mobile_nav"] or {}), flush=True)
            await call("Emulation.setTouchEmulationEnabled", {"enabled": False})

            # 4) 键盘：Tab 能否进入「工具」子菜单
            await call("Emulation.setDeviceMetricsOverride",
                       {"width": 1366, "height": 900, "deviceScaleFactor": 1, "mobile": False})
            await call("Page.navigate", {"url": base + "#/home"})
            await asyncio.sleep(2.0)
            await call("Runtime.evaluate", {"expression":
                       "document.querySelector('.skip-link').focus();1"})
            seq = []
            for _ in range(12):
                await call("Input.dispatchKeyEvent",
                           {"type": "keyDown", "key": "Tab", "code": "Tab",
                            "windowsVirtualKeyCode": 9, "nativeVirtualKeyCode": 9})
                await call("Input.dispatchKeyEvent",
                           {"type": "keyUp", "key": "Tab", "code": "Tab",
                            "windowsVirtualKeyCode": 9, "nativeVirtualKeyCode": 9})
                await asyncio.sleep(0.1)
                cur = await ev("JSON.stringify({t:(document.activeElement.textContent||'')"
                               ".trim().slice(0,10),href:document.activeElement.getAttribute"
                               "?document.activeElement.getAttribute('href'):null})")
                if cur:
                    seq.append(cur)
            out["keyboard_nav"] = {
                "sequence": seq,
                "reaches_submenu": any((s.get("href") or "").startswith("#/extract")
                                       and "工具" not in (s.get("t") or "") for s in seq),
            }
            print("  键盘可达子菜单: %s" % out["keyboard_nav"]["reaches_submenu"], flush=True)

            # 5) 交互：首页可点卡片是否可聚焦
            inter = await ev(r"""
            (() => {
              // 全部项目视图是 .home-proj，单项目视图是 .home-step；两者都算首页可操作卡
              const cards = [...document.querySelectorAll('#app .home-step, #app .home-proj')];
              // 原生可交互元素（button/a/input…）本身就在 Tab 序列里，
              // 只看 tabindex/role 会把 <button> 误判成不可聚焦。
              const NATIVE = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA', 'SUMMARY'];
              const focusable = cards.filter(el => {
                if (NATIVE.includes(el.tagName)) return el.tabIndex >= 0;
                const ti = el.getAttribute('tabindex');
                return el.hasAttribute('role') || (ti !== null && Number(ti) >= 0);
              }).length;
              return JSON.stringify({homeStepCount: cards.length, focusable});
            })()
            """)
            out["interactive"] = inter or {}
            print("  首页流程卡可聚焦: %s" % (out["interactive"] or {}), flush=True)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="交互与状态探针（只读）")
    ap.add_argument("--base", default="http://127.0.0.1:8735/")
    ap.add_argument("--chrome", default="")
    ap.add_argument("--out", default=os.path.join(PROJECT, ".sdd", "audit", "state.json"))
    args = ap.parse_args()
    base = args.base if args.base.endswith("/") else args.base + "/"
    wait_service(base)
    print("交互与状态审计 %s" % base)
    data = asyncio.run(probe(base, args.chrome or chrome_path()))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
    blanks = sum(1 for v in data["failure_states"].values() if v.get("blank"))
    norety = sum(1 for v in data["failure_states"].values()
                 if not v.get("blank") and not v.get("hasRetry"))
    print("\n失败态：空白 %d / 无重试 %d / 触屏下拉可开 %s / 键盘可达 %s" % (
        blanks, norety, data["mobile_nav"].get("menuOpened"),
        data["keyboard_nav"].get("reaches_submenu")))
    print("快照：" + args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
