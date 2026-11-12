# 多模态测试平台 — 源码 / 开发规范 / UI 审查报告

- 审查日期：2026-11-05
- 被审对象：`多模态测试平台-使用版/多模态测试平台.exe`（24.5 MB）
- 审查方式：PyInstaller 归档解包 + 前端源码直读 + 后端字节码核验 + 本地运行时接口实测
- 结论口径：只报不改，本报告未修改被审二进制或任何业务文件

## 一、技术栈与工程形态

| 层 | 实际实现 |
|----|----------|
| 打包 | PyInstaller 单文件 exe，Python 3.8，`MEI` cookie 尾部 |
| 后端 | FastAPI + pydantic，uvicorn 绑定 `127.0.0.1`，默认端口 8735，可顺延 |
| 前端 | 原生 JS 单页应用（无框架、无构建链），`web/index.html` + `app.js`(3,930 行) + `style.css`(606 行) |
| 存储 | 纯文件系统 `workspace/`，无数据库；`config.json` + JSON/TXT/JPG |
| 模型调用 | OpenAI 兼容协议，多站点 + 多 Key 轮询，限流/超时重试 |
| 数据规模 | 后端业务模块 22 个、约 16 万字节码；REST 路由 72 组；前端 18 个页面路由 |

## 二、架构与数据流

`配置(站点/Key/默认参数) → 图片集(项目::图片集) → 提示词生成/提示词版本(V1..Vn, 五段式) → 运行(图片×版本×复现次数) → 人工审核(verdict + expected_objects) → 裁判(fault_location 八模块) → 优化建议(仅 role/task/definition/workflow) → 新版本 → 评估(accuracy/P-R-F1/混淆矩阵) → 回归集`

值得肯定的设计（已逐条用字节码或运行时验证）：

- 提示词五段式拆分，`output_format` 在自动优化链路中被哈希锁定，优化器越权会被拒绝。
- 审核沉淀真值采取"手动优先 + 自动补齐"，重复运行可用 SHA-256 复用人工基线。
- 运行/裁判/优化均为后台任务，重启后能对账为 `interrupted`/`已暂停`，支持断点续跑。
- 列表接口用目录指纹缓存，并刻意避免读接口写盘，避免轮询阻塞。
- 裁判提示词把业务 JSON 与图片内容显式标注为"待评估数据、非指令"，有防注入意识。
- `safe_path()` 用 `realpath` + 前缀校验阻止目录穿越；`_mask_key()` 保证配置接口不回显明文 Key。

## 三、开发规范评估

### 做得好的地方

- 模块职责清晰：`config / datasets / prompts / runner / reviews / judge / workflow / evaluate` 边界明确。
- 错误文案面向使用者，含"未配置 API Key，请先到配置页填写"这类可操作提示。
- 有范围校验：并发 1–20、单 Key 并发 1–8、超时 5–600、max_tokens 128–131072 等。
- 兼容历史数据：旧单站点配置自动迁移、旧结果命名回退读取、旧数据集归入"未归档项目"。

### 主要问题

| 级别 | 问题 | 证据 |
|------|------|------|
| 高 | 仓库内没有任何源码、依赖清单、构建脚本与测试 | 交付物只有 exe + workspace + 两份文档；无法复现构建，`python run.py` 开发模式实际不可用 |
| 高 | 无自动化测试 | 归档内无 test 目录/用例；评估、IoU 匹配、协议解析等核心算法无回归保护 |
| 高 | 版本与变更不可追溯 | 无 CHANGELOG、无构建版本号、无 git 历史；出问题无法二分定位 |
| 中 | 前端无构建与模块化 | 单文件 3,930 行、107 处 `innerHTML`、19 处 `confirm()`、5 处 `prompt()` |
| 中 | 无鉴权 + 无安全响应头 | 72 组路由全部匿名可调；响应头无 CSP/X-Content-Type-Options/Referrer-Policy；Host 未校验 |
| 中 | 未处理单实例锁 | 依靠"端口被占则探测是否本应用"来识别重复启动，属启发式而非互斥锁 |
| 低 | 文案与实现存在轻微漂移 | 操作指南称"首次运行自动生成 workspace"，实际 `MMTEST_WORKSPACE` 可覆盖；指南第 5 条编号重复 |
| 低 | 缺中文路径/空格路径的显式处理 | exe 与 `workspace/` 放在含中文和空格的目录（本机实测路径即如此）时能正常启动，但代码中未见针对该场景的测试用例，属未受保护路径 |

## 四、UI / 交互评估

### 优点

- 视觉基线统一：`--primary #2e6de6`、8pt 间距、10px 圆角、卡片化布局，深色顶栏有层次。
- 认知负担控制得不错：新手引导、快速上手示例、首页待办、帮助页内置全文指南。
- 结果查看器信息密度合理：原图 / 推理图 / 解析 JSON / 原始响应 / 提示词快照五视图。
- JSON 树形/原文双模式、IoU 框编辑、快捷键 1–5 审核，都是针对真实工作流的效率设计。

### 主要问题

| 级别 | 问题 | 证据 |
|------|------|------|
| 高 | 可访问性基本缺失 | 124 个 `<label>` 仅 2 个 `for=`；94 个 `<input>` 仅 1 个 `aria-label`；`role=` 0 处；无 `:focus-visible` |
| 高 | 模态框键盘不可用 | `openDlg()` 无焦点陷阱、无 `aria-modal`、无关闭后焦点归还 |
| 中 | 破坏性操作依赖浏览器原生弹窗 | 19 处 `confirm()`、5 处 `prompt()`，样式与主界面割裂，且无法批量确认 |
| 中 | 移动端只有基础适配 | 仅 3 个 `@media (max-width:760px)`；顶栏 8 个导航项在窄屏会挤压；无折叠菜单 |
| 中 | 加载态只有文字 | **无骨架屏/进度条组件**；长任务仅"加载中…"，大数据集下体感卡顿 |
| 低 | 无暗色模式、无主题变量分层 | 仅 `:root` 一套亮色变量；`prefers-color-scheme` 0 处 |
| 低 | CSS 层级靠覆盖生效 | `.btn`、`.dlg`、`.row`、`.tag.blue` 各定义两次；`style.css` 中 `!important` 5 处 |

## 五、优先修复建议

### P0（影响可维护性与安全底线）

1. **把源码纳入版本管理**：找回 `app/`、`web/`、`run.py`、`requirements.txt`/`pyproject.toml`、`*.spec`，建立可复现构建。当前 exe 是唯一事实来源，任何改动都不可审计。
2. **补最小测试集**：`schema.parse_result` 协议容错、`comparison.compare` IoU 匹配、`evaluate._metrics_*` 指标计算、`config.normalize_config` 校验，四处各 10–20 条用例即可覆盖主要回归面。
3. **加安全响应头**：`Content-Security-Policy`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`，并对 `Host` 做 `127.0.0.1/localhost` 白名单校验，防止 DNS rebinding。

### P1（影响可用性）

4. **修可访问性**：给输入控件补 `for/id` 或 `aria-label`；模态框加 `role="dialog" aria-modal="true"` + 焦点陷阱 + Esc 关闭后焦点归还；补 `:focus-visible` 样式。
5. **替换原生弹窗**：把 19 处 `confirm()` 统一为站内确认对话框，危险操作保留二次输入确认。
6. **补加载骨架与长任务进度**：运行/裁判/优化已在后端有进度，前端应展示百分比与剩余估算，而非仅"加载中"。

### P2（体验提升）

7. **CSS 去重**：合并重复规则，按 `tokens / layout / components / pages` 分层，消除 `!important`。
8. **移动端导航**：≤760px 改为折叠菜单，表格提供横向滚动容器。
9. **暗色模式**：把颜色全部抽到语义变量（`--surface / --surface-2 / --text-muted`），加 `prefers-color-scheme` 与手动切换。

## 六、可直接复用的分析资产

| 路径 | 说明 |
|------|------|
| `_artifacts/app.js` | 完整前端源码（3,930 行，UTF-8 无损） |
| `_artifacts/style.css` | 完整样式（606 行） |
| `_artifacts/index.html` | 页面骨架与导航结构 |
| `_artifacts/demo_pack/` | 内置示例素材（20 张图 + 提示词 + 真值） |
| `_src/app.*.py` | 6 个成功反编译的后端模块（config/demo/evaluate/extractor/stats 等） |
| `_analysis/backend_inventory.json` | 22 个模块的函数/全局符号清单 |
| `_analysis/disasm_*.txt` | 关键函数的 Python 3.8 字节码反汇编 |

> 注意：`_src/` 中部分模块反编译不完整（decompyle3 对 3.8 的个别控制流会输出 `while True: pass` 之类伪影），凡涉及控制流结论均已回查字节码，勿直接以反编译文本为准。

## 七、复现命令

```powershell
# 只读启动（不改动原 workspace）
$env:MMTEST_WORKSPACE='<临时目录>'; $env:MMTEST_NO_BROWSER='1'; $env:MMTEST_PORT='8799'
Start-Process '.\多模态测试平台.exe' -WindowStyle Hidden

# 接口契约
Invoke-RestMethod 'http://127.0.0.1:8799/openapi.json'
```
