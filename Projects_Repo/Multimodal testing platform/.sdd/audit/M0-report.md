# M0 · UIUX 审计护栏（Yven 基线）

> 生成时间：2026-11-06  
> 基线提交：`2f5efe0`（tag `Yven`）  
> 目的：在动 UI 之前先有一把**可重复、可对比、会失败**的尺子。  
> 本轮**不修改任何产品代码**，只新增只读探针、快照与门禁。

## 1. 交付物

| 文件 | 作用 | 是否进 exe |
|------|------|-----------|
| `tools/audit/ui_probe.py` | 12 条路由 × 4 个宽度：横向溢出、控件高度、字号、主按钮数、`alt`、键盘不可达、对比度 | 否（spec 只打包 `web/` `demo_pack/`） |
| `tools/audit/ui_state_probe.py` | 失败态、慢网切页、触屏下拉、键盘 Tab 序列、首页卡片可聚焦 | 否 |
| `tools/audit/check_baseline.py` | 把发现固化成 11 条断言（9 must_fix + 2 guard） | 否 |
| `.sdd/audit/yven.json` | 静态版式快照（40 KB） | 否 |
| `.sdd/audit/state-yven.json` | 交互/状态快照（2.7 KB） | 否 |
| `tests/test_frontend_p1.py` | +4 条门禁：内联样式不许增长、探针只读、快照存在、基线能复现缺陷 | 是（测试） |

## 2. 基线结论（Yven 实测）

**12 例横向溢出**，全部集中在 761–900px 空档（唯一主断点只有 760px）：

| 宽度 | 整页溢出 | 说明 |
|------|---------|------|
| 1366 / 1024 / 390 | 0 | 正常 |
| 900 | 0 | — |
| 860 | +32px | 开始溢出 |
| 800 | +92px | 顶栏右侧被切 |
| 780 | +112px | — |
| 761 | +131px | 最严重 |
| 760 | 0 | 汉堡菜单接管 |

**失败态：8/8 路由整页空白**（只剩顶栏）。拦截 `*/api/*` 后 `/prompts` 的 `#app.innerHTML` 为空字符串，`innerText` 仅 3 个字符（探针取标题时的空白），用户看到的就是一整块空区域。

**导航「工具」子菜单双重不可达**：
- 触屏：点击直接跳 `#/extract`，`menuDisplay=none`，4 个子项从未出现；
- 键盘：Tab 序列 `首页→…→工具▾→配置`，子菜单被整段跳过。

**首页**：2 个可见主按钮、11 张流程卡可点但**0 张可聚焦**。

**对比度**：暗色主按钮白字 **3.20:1**、浅色辅助文字 **4.38:1**，均低于 AA 4.5。

**控件高度**：`#/config`、`#/extract`、`#/truth` 同页并存 29/36/38px 三档。

## 3. 度量可信度验证

| 验证 | 结果 |
|------|------|
| 同一版本连跑两次，逐字段 diff | **0 处差异** |
| 注入"3 个主按钮 + 对比度 2.10" | 两项都被门禁抓到（`detected: True`） |
| 门禁在 Yven 上 | 9 must_fix 全红、2 guard 全绿（符合"如实复现"） |
| `pytest -q` | **163 passed**（原 159 + 4） |

> 关键点：门禁不是"跑完都绿"，而是**基线阶段必须红**。若某天它变绿了，说明问题真被修掉了，此时应更新基线快照而不是保留旧红灯。

## 4. 用法

```bash
# 1) 采集快照（需先启动服务：python run.py）
python tools/audit/ui_probe.py --label m1 --out .sdd/audit/m1.json
python tools/audit/ui_state_probe.py --out .sdd/audit/state-m1.json

# 2) 跑门禁（M0 基线阶段不加 --strict）
python tools/audit/check_baseline.py \
    --snapshot .sdd/audit/m1.json --state .sdd/audit/state-m1.json

# 3) 与基线做回归对比（改版阶段必须跑）
python tools/audit/ui_probe.py --label after --out .sdd/audit/after.json
python tools/audit/ui_probe.py --diff .sdd/audit/yven.json --out .sdd/audit/after.json \
    --fail-on-regression
```

## 5. 11 条断言

| # | 维度 | 级别 | 断言 | Yven 状态 |
|---|------|------|------|----------|
| 1 | 响应式 | guard | 1366/1024/390 无整页溢出 | PASS |
| 2 | 响应式 | must_fix | 761–900 无整页溢出 | FAIL |
| 3 | 状态完整性 | must_fix | 接口失败不空白 | FAIL |
| 4 | 状态完整性 | must_fix | 失败态提供重试 | FAIL |
| 5 | 可访问性 | must_fix | 触屏可展开工具子菜单 | FAIL |
| 6 | 可访问性 | must_fix | 键盘可进入工具子菜单 | FAIL |
| 7 | 视觉层级 | must_fix | 每页唯一主行动 | FAIL（home/judge-iter/truth 各 2） |
| 8 | 可访问性 | must_fix | 首页流程卡可键盘操作 | FAIL（0/11） |
| 9 | 可访问性 | must_fix | 对比度 ≥4.5:1 | FAIL（3.20 / 4.38） |
| 10 | 一致性 | must_fix | 同页控件高度 ≤2 档 | FAIL（3 页 3 档） |
| 11 | 状态完整性 | guard | 任何路由不出现空白页 | PASS |

## 6. 已知局限（不许当成"已验证"）

- 探针只覆盖 12 条主路由；`project` / `datasetDetail` / `viewer` / `truthEdit` / `workflow` / `profiles` 是深链，需要真实数据 id，M1 再补。
- 对比度取的是"元素自身色 vs 最近不透明祖先背景"，渐变与半透明叠层可能低估，需人工复核。
- 触屏手势用 CDP `dispatchTouchEvent` 模拟，不能替代真机；M3 验收要以真机点一遍为准。
- 未纳入：动效性能、滚动流畅度、读屏器实际播报顺序。

## 7. 字节码对拍环境（Python 3.8）

`_src/_pyc/*.pyc` 是 Python 3.8 字节码（magic `550d`），而 3.11 起 pyc 头从 16 字节
改为 12 字节、指令集也变了。所以 **3.12 读这些文件会直接报 `bad marshal data`**，
换成 3.12 跑只会得到一堆假差异。

本机安装位置（与 3.11/3.12 同构，用户级，无需管理员）：

```
C:\Users\huyufeng7\AppData\Local\Programs\Python\Python38\python.exe
```

安装时使用的参数：`InstallAllUsers=0`、`Include_launcher=0`、`PrependPath=0`。
因此 `python` 仍是 3.12，PATH 未被改动，`py -3.8` 可单独调用。

日常检查用脚本，不必手敲长路径：

```powershell
# app/ 无改动时自动跳过；有改动才用 3.8 跑，并比对是否退化
powershell -ExecutionPolicy Bypass -File tools\audit\check_bytecode.ps1

# 强制跑一次
powershell -ExecutionPolicy Bypass -File tools\audit\check_bytecode.ps1 -Force
```

脚本的判定：`missing != 0`、`diff` 变大、`exact` 变小，任一命中即失败；
跑完会把被脚本重写的 `bytecode_match.json` 还原，避免无意义 diff。

验收记录（2026-11-06）：`TOTAL 623 functions | exact 592 | near 10 | diff 21 | missing 0`，
与基线完全一致。

> 注意：`.ps1` 必须保存为 **UTF-8 with BOM**。PowerShell 5.1 会用 GBK 解析无 BOM 的
> 脚本，中文会被打乱并报语法错误（`<` 运算符、`Array index expression` 等假错误）。
> 这条与 `web/` 的 no-BOM 规范不冲突：那是给浏览器读的，`.ps1` 是给 5.1 读的。

## 7. 下一步

M1（项目上下文，纯前端）开工前先跑一次本报告第 4 节第 1 步，确认基线仍与 `yven.json` 一致；不一致先查环境，不要带着脏基线开工。
