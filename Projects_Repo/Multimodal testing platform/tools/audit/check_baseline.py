"""把审计发现固化成"已知问题基线"，防止改版时悄悄变差。

设计原则：
- 快照（.sdd/audit/*.json）只是数据；这里定义"哪些数字必须改善、哪些数字不许变差"。
- 门禁分两级：`must_fix`（本轮承诺修掉的）与 `guard`（不许回归的）。
- 任何一项 must_fix 通过，脚本会把该条目记为 resolved，但不会自动删除断言——
  只有显式更新 EXPECTATIONS 才允许放宽，避免"改断言"当修复。

用法：
    python tools/audit/check_baseline.py --snapshot .sdd/audit/yven.json \
        --state .sdd/audit/state-yven.json
    python tools/audit/check_baseline.py --snapshot new.json --state new-state.json --strict
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------- 期望值
# 每一项：id / 维度 / 描述 / 判定函数 / 级别
# 级别 must_fix = 本轮要修；guard = 只是不许变差
# 判定函数返回 (ok: bool, detail: str)

def _routes(snapshot):
    return snapshot.get("routes", {})


def _at(snapshot, route, width):
    return _routes(snapshot).get(route, {}).get(str(width), {})


def _all(snapshot):
    for route, widths in _routes(snapshot).items():
        for width, entry in widths.items():
            yield route, int(width), entry


def expect_no_page_overflow(snapshot, state):
    """任何路由在 1366/1024/390 都不许整页横向溢出。800 档单列（见 breakpoint_gap）。"""
    bad = []
    for route, width, entry in _all(snapshot):
        if width in (1366, 1024, 390) and (entry.get("pageOverflow") or 0) > 0:
            bad.append("%s@%d(+%dpx)" % (route, width, entry["pageOverflow"]))
    return (not bad), ("溢出：" + ", ".join(bad)) if bad else "1366/1024/390 全部无整页横向溢出"


def expect_breakpoint_gap(snapshot, state):
    """761–900 区间当前存在断点空档；修好后此条转为 resolved。"""
    bp = snapshot.get("breakpoints", {})
    bad = [w for w in ("900", "860", "800", "780", "761")
           if any((v.get("pageOverflow") or 0) > 0 for v in bp.get(w, {}).values())]
    if bad:
        return False, "断点空档仍在：%s 有整页横向溢出" % ",".join(bad)
    return True, "761–900 区间无整页横向溢出"


def expect_failure_state_not_blank(snapshot, state):
    """接口全挂时，页面必须给出可理解反馈（不能只剩标题）。"""
    fs = (state or {}).get("failure_states", {})
    if not fs:
        return False, "缺少失败态快照"
    blank = [r for r, v in fs.items() if (v.get("textLen") or 0) < 20]
    return (not blank), ("空白页：" + ",".join(blank)) if blank else "所有路由都有可见反馈"


def expect_failure_state_has_retry(snapshot, state):
    fs = (state or {}).get("failure_states", {})
    if not fs:
        return False, "缺少失败态快照"
    norety = [r for r, v in fs.items() if not v.get("hasRetry")]
    return (not norety), ("无重试：" + ",".join(norety)) if norety else "所有失败态都提供重试"


def expect_submenu_mobile(snapshot, state):
    """触屏点「工具」必须展开子菜单，而不是直接跳走。"""
    m = (state or {}).get("mobile_nav", {})
    return bool(m.get("menuOpened")), (
        "菜单 display=%s，跳转到 %s" % (m.get("menuDisplay"), m.get("landedHash"))
        if not m.get("menuOpened") else "触屏可展开 4 个子项")


def expect_submenu_keyboard(snapshot, state):
    k = (state or {}).get("keyboard_nav", {})
    return bool(k.get("reaches_submenu")), (
        "Tab 序列未进入子菜单：%s" % [s.get("t") for s in k.get("sequence", [])][:10]
        if not k.get("reaches_submenu") else "键盘可进入子菜单")


def expect_single_primary(snapshot, state):
    """每个页面都只该有一个主行动；多主按钮等于没有主按钮。

    这里只数"当前可见"的 primary 按钮（探针已排除隐藏 tab），
    1366 下逐页检查，避免只盯首页而放过内页。
    """
    e = _at(snapshot, "#/home", 1366)
    if e.get("primaryBtns") is None:
        return False, "首页缺少指标"
    bad = []
    for route, width, entry in _all(snapshot):
        if width != 1366:
            continue
        n = entry.get("primaryBtns")
        if n is None:
            continue
        if n > 1:
            bad.append("%s:%s" % (route, n))
    if bad:
        return False, "多主按钮：" + ", ".join(bad)
    return True, "各页可见主按钮均 ≤1"


def expect_home_cards_focusable(snapshot, state):
    i = (state or {}).get("interactive", {})
    total, ok = i.get("homeStepCount"), i.get("focusable")
    if total is None:
        return False, "缺少首页卡片快照"
    return (ok or 0) >= (total or 0), "可聚焦 %s/%s 张流程卡" % (ok, total)


def expect_contrast(snapshot, state):
    """辅助文字与主按钮都要到达 AA（4.5:1）。"""
    bad = []
    for theme, pairs in (snapshot.get("contrast") or {}).items():
        for key, val in (pairs or {}).items():
            if not isinstance(val, dict) or "ratio" not in val:
                continue
            need = 4.5
            if val["ratio"] < need:
                bad.append("%s/%s=%.2f" % (theme, key, val["ratio"]))
    return (not bad), ("低于 4.5:1：" + ", ".join(sorted(bad))) if bad else "明暗两套均 ≥4.5:1"


def expect_control_heights(snapshot, state):
    """同一页控件高度档位不超过 2 档（36/38 这类并存要收敛）。"""
    bad = []
    for route, width, entry in _all(snapshot):
        if width != 1366:
            continue
        hs = [h for h in (entry.get("heights") or []) if 28 <= h <= 60]
        if len(set(hs)) > 2:
            bad.append("%s:%s" % (route, hs))
    return (not bad), ("高度档位过多：" + "; ".join(bad)) if bad else "各页控件高度 ≤2 档"


def expect_no_blank_routes(snapshot, state):
    blank = []
    for route, width, entry in _all(snapshot):
        if (entry.get("textLen") or 0) == 0:
            blank.append("%s@%d" % (route, width))
    return (not blank), ("空白：" + ",".join(blank[:8])) if blank else "无空白页"


EXPECTATIONS = [
    # id, 维度, 级别, 说明, 判定
    ("overflow_primary", "响应式", "guard", "1366/1024/390 无整页横向溢出", expect_no_page_overflow),
    ("breakpoint_gap", "响应式", "must_fix", "761–900 断点空档", expect_breakpoint_gap),
    ("failure_visible", "状态完整性", "must_fix", "接口失败不空白", expect_failure_state_not_blank),
    ("failure_retry", "状态完整性", "must_fix", "失败态提供重试", expect_failure_state_has_retry),
    ("submenu_mobile", "可访问性", "must_fix", "触屏可展开工具子菜单", expect_submenu_mobile),
    ("submenu_keyboard", "可访问性", "must_fix", "键盘可进入工具子菜单", expect_submenu_keyboard),
    ("single_primary", "视觉层级", "must_fix", "每页唯一主行动", expect_single_primary),
    ("home_focusable", "可访问性", "must_fix", "首页流程卡可键盘操作", expect_home_cards_focusable),
    ("contrast", "可访问性", "must_fix", "辅助文字/主按钮对比度 ≥4.5:1", expect_contrast),
    ("control_heights", "一致性", "must_fix", "同页控件高度 ≤2 档", expect_control_heights),
    ("no_blank", "状态完整性", "guard", "任何路由不出现空白页", expect_no_blank_routes),
]


def load(path):
    if not path or not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser(description="审计基线门禁")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--state", default="")
    ap.add_argument("--strict", action="store_true",
                    help="must_fix 未通过则返回非 0（M0 基线阶段不要开）")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    snap = load(args.snapshot)
    state = load(args.state) if args.state else {}
    if not snap:
        raise SystemExit("快照不存在或无内容：%s" % args.snapshot)

    rows, failed_must, failed_guard = [], 0, 0
    for eid, dim, level, desc, fn in EXPECTATIONS:
        try:
            ok, detail = fn(snap, state)
        except Exception as exc:  # 探针缺字段也要显式失败，不能静默通过
            ok, detail = False, "判定异常：%r" % (exc,)
        if not ok:
            if level == "must_fix":
                failed_must += 1
            else:
                failed_guard += 1
        rows.append({"id": eid, "dimension": dim, "level": level,
                     "desc": desc, "ok": ok, "detail": detail})

    print("维度        级别      状态  说明")
    print("-" * 92)
    for r in rows:
        mark = "PASS" if r["ok"] else ("FAIL" if r["level"] == "must_fix" else "WARN")
        print("%-10s  %-7s  %-4s  %s" % (r["dimension"], r["level"], mark, r["desc"]))
        if not r["ok"]:
            print("            └─ %s" % r["detail"])

    print("\nmust_fix 未通过 %d 项 / guard 未通过 %d 项" % (failed_must, failed_guard))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"snapshot": args.snapshot, "state": args.state,
                       "rows": rows, "must_fix_failed": failed_must,
                       "guard_failed": failed_guard}, fh, ensure_ascii=False, indent=2)
    if args.strict:
        return 1 if (failed_must or failed_guard) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
