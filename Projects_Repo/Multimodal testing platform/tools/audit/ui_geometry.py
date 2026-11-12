"""几何对拍：记录每个元素的位置/尺寸，用于证明样式重构"零位移"。

用法：
    python tools/audit/ui_geometry.py --out .sdd/audit/geom-before.json
    python tools/audit/ui_geometry.py --out .sdd/audit/geom-after.json
    python tools/audit/ui_geometry.py --diff .sdd/audit/geom-before.json --out .sdd/audit/geom-diff.json

只读：只向运行中的服务发 GET，不改产品数据。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_probe import (  # noqa: E402
    PROJECT, ROUTES, WIDTHS, chrome_path, free_port, subprocess_popen, wait_devtools,
)

# 深链一律用百分号编码，避免命令行/控制台编码差异把中文路由变成乱码
ROUTES_EXT = ROUTES + [
    "#/project/%E7%A4%BA%E4%BE%8B%E9%A1%B9%E7%9B%AE",
    "#/project/%E7%A4%BA%E4%BE%8B%E9%A1%B9%E7%9B%AE/%E9%98%B2%E6%BA%BA%E6%B0%B4-%E6%B0%B4%E8%BE%B9%E4%BA%BA%E5%91%98%E6%A3%80%E6%B5%8B",
]
PROPS = ["display", "position", "flex-grow", "flex-shrink", "flex-basis", "align-self",
         "align-items", "justify-content", "gap", "margin-top", "margin-right",
         "margin-bottom", "margin-left", "padding-top", "padding-right",
         "padding-bottom", "padding-left", "width", "height", "min-width",
         "min-height", "max-width", "max-height", "font-size", "font-weight",
         "color", "background-color", "border-left-color", "border-top-color",
         "border-top-width", "border-radius", "overflow", "overflow-x",
         "overflow-y", "text-overflow", "white-space", "text-align", "cursor",
         "grid-template-columns", "transform", "opacity", "visibility"]

GEOM = r"""
(() => {
  const out = [];
  const app = document.getElementById('app');
  if (!app) return JSON.stringify(out);
  const all = app.querySelectorAll('*');
  const counters = {};
  const pathOf = (el) => {
    const parts = [];
    let cur = el;
    while (cur && cur !== app) {
      const parent = cur.parentElement;
      // 只用 tag + 同名兄弟序号定位：加入工具类后 class 会变，key 必须保持稳定
      const siblings = parent ? Array.from(parent.children).filter(c => c.tagName === cur.tagName) : [];
      const idx = siblings.indexOf(cur);
      parts.push(cur.tagName.toLowerCase() + '#' + idx);
      cur = parent;
    }
    return parts.reverse().join('>');
  };
  all.forEach((el) => {
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) return;
    const key = pathOf(el);
    const seen = (counters[key] = (counters[key] || 0) + 1);
    const cs = getComputedStyle(el);
    const st = {};
    for (const p of __PROPS__) st[p] = cs.getPropertyValue(p);
    out.push({ k: key + '~' + seen, x: Math.round(r.x), y: Math.round(r.y),
               w: Math.round(r.width), h: Math.round(r.height),
               inline: el.hasAttribute('style'), st: st });
  });
  return JSON.stringify(out);
})()
"""



STABLE = """
(() => {
  const app = document.getElementById('app');
  if (!app) return 0;
  if (app.querySelector('.skeleton')) return 0;
  return app.querySelectorAll('*').length;
})()
"""


async def wait_stable(call, timeout=8.0, quiet_polls=3, interval=0.12):
    """等页面渲染稳定再采样：轮询元素数，连续 quiet_polls 次不变才算完成。

    固定 sleep 会在接口慢时截到半渲染页面，导致"元素凭空消失"的假差异。
    """
    import time as _time
    deadline = _time.time() + timeout
    last, stable = -1, 0
    while _time.time() < deadline:
        r = await call("Runtime.evaluate", {"expression": STABLE, "returnByValue": True})
        cur = r.get("result", {}).get("result", {}).get("value") or 0
        if cur == last and cur > 0:
            stable += 1
            if stable >= quiet_polls:
                return cur
        else:
            stable = 0
            last = cur
        await asyncio.sleep(interval)
    return last


async def run(base: str, chrome: str, out_path: str) -> dict:
    import websockets

    tmp = tempfile.mkdtemp(prefix="mmt-geom-")
    port = free_port()
    proc = subprocess_popen(chrome, tmp, port)
    result = {"routes": {}}
    try:
        wait_devtools(port)
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

            await call("Page.enable")

            for width in WIDTHS:
                await call("Emulation.setDeviceMetricsOverride",
                           {"width": width, "height": 900, "deviceScaleFactor": 1,
                            "mobile": width < 500})
                for route in ROUTES_EXT:
                    await call("Page.navigate", {"url": base + route})
                    await asyncio.sleep(0.35)
                    await wait_stable(call)
                    r = await call("Runtime.evaluate", {
                        "expression": GEOM.replace("__PROPS__", json.dumps(PROPS)),
                        "returnByValue": True})
                    val = r.get("result", {}).get("result", {}).get("value")
                    boxes = json.loads(val) if isinstance(val, str) else []
                    result["routes"].setdefault(route, {})[str(width)] = boxes
                    print("  %-14s %5d  %d elements" % (route, width, len(boxes)), flush=True)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return result


def diff(before: dict, after: dict) -> dict:
    report = {"missing": [], "appeared": [], "moved": [], "inlineDelta": 0,
              "styleChanged": []}
    for route, widths in before.get("routes", {}).items():
        for width, boxes in widths.items():
            bmap = {b["k"]: b for b in boxes}
            amap = {b["k"]: b for b in (after.get("routes", {}).get(route, {}).get(width) or [])}
            for k, b in bmap.items():
                a = amap.get(k)
                if a is None:
                    report["missing"].append("%s@%s %s" % (route, width, k))
                    continue
                if (b["x"], b["y"], b["w"], b["h"]) != (a["x"], a["y"], a["w"], a["h"]):
                    report["moved"].append({
                        "at": "%s@%s" % (route, width), "k": k,
                        "before": [b["x"], b["y"], b["w"], b["h"]],
                        "after": [a["x"], a["y"], a["w"], a["h"]],
                    })
                if b.get("inline") != a.get("inline"):
                    report["inlineDelta"] += 1
            for k in amap:
                if k not in bmap:
                    report["appeared"].append("%s@%s %s" % (route, width, k))
    return report


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8735/")
    ap.add_argument("--out", default=os.path.join(PROJECT, ".sdd", "audit", "geom.json"))
    ap.add_argument("--diff", default=None)
    ap.add_argument("--report", default=None,
                    help="diff 报告输出路径；默认 <out 同名>.diff.json，不覆盖快照")
    args = ap.parse_args()

    if args.diff:
        # 注意：--out 是"改造后快照"，报告必须另存，
        # 否则会把快照覆盖成报告，下一次 diff 就变成拿报告比报告。
        report_path = args.report or (os.path.splitext(args.out)[0] + ".diff.json")
        report = diff(load(args.diff), load(args.out))
        print("位移 %d / 样式变化 %d / 消失 %d / 新增 %d / inline 标记变化 %d" % (
            len(report["moved"]), len(report["styleChanged"]), len(report["missing"]),
            len(report["appeared"]), report["inlineDelta"]))
        for item in report["styleChanged"][:20]:
            print("  style %s %s %s: %r -> %r" % (item["at"], item["k"], item["prop"],
                                                  item["before"], item["after"]))
        for item in report["moved"][:20]:
            print("  moved %s %s  %s -> %s" % (item["at"], item["k"],
                                               item["before"], item["after"]))
        for item in report["missing"][:10]:
            print("  missing", item)
        with open(report_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
        print("报告：%s" % report_path)
        bad = report["moved"] or report["missing"] or report["styleChanged"]
        return 0 if not bad else 1

    asyncio.run(run(args.base, chrome_path(), args.out))
    print("几何快照：%s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
