# 多模态大模型能力测试平台

本地单机 Web 应用：管理图片集与提示词版本，批量调用 OpenAI 兼容的多模态模型，
做人工审核、裁判归因、提示词优化与准确率 / P-R-F1 评估。

源码由发行版 `多模态测试平台.exe`（PyInstaller + Python 3.8）逆向恢复而来，
恢复过程与对拍证据见 `tools/recover/` 与 `_src/`。

## 目录结构

```text
app/                 FastAPI 后端（22 个模块，REST 路由 + 业务逻辑）
web/                 原生 JS 单页前端（index.html / app.js / style.css）
run.py               启动入口：选端口、起 uvicorn、开浏览器
demo_pack/           内置示例素材（20 张图 + 提示词 + 真值）
tests/               pytest 回归用例
tools/recover/       字节码恢复与逐函数对拍工具、手写修复片段
_src/_pyc/           原始 3.8 字节码（恢复证据，勿删）
workspace/           运行时数据（不入库，含 API Key）
```

## 环境

- Python 3.10+（开发与测试在 3.12 验证）
- 依赖：`pip install -r requirements-dev.txt`

## 开发运行

```powershell
python run.py
```

默认 `http://127.0.0.1:8735`；端口被占用时自动顺延。若已有本平台实例在运行，
启动器会直接打印复用地址并退出（单实例锁，见 `app/instance_lock.py`），不会起第二个服务。

运行期信息：

- 版本：`GET /api/version`（帮助页也会显示版本、构建时间与提交号）
- 日志：`workspace/logs/app.log`，JSON Lines，2MB × 3 轮转；API Key 与异常信息统一脱敏

环境变量：

| 变量 | 作用 |
|------|------|
| `MMTEST_WORKSPACE` | 数据目录，默认 `./workspace` |
| `MMTEST_PORT` | 起始端口，默认 `8735` |
| `MMTEST_NO_BROWSER` | `1` 时不自动开浏览器 |
| `MMTEST_ALLOWED_HOSTS` | 额外允许的 Host（逗号分隔） |

## 测试

```powershell
python -m pytest -q
```

覆盖协议解析（`schema.parse_result`）、IoU 匹配与判定（`comparison.compare`）、
指标计算（`evaluate._metrics_*`）、配置校验（`config.normalize_config`）、
路径穿越防护（`config.safe_path`）以及安全中间件 / Host 白名单。

## 打包

```powershell
pyinstaller --noconfirm --clean multimodaltest.spec
```

产物 `dist/多模态测试平台.exe`，单文件、内置 `web/`、`demo_pack/`、`操作指南.txt`
与 `build_info.json`（构建时间与提交号）。

## 安全基线

`app/security.py` 在 `run.py` 启动时注册：

- Host 白名单（默认 `127.0.0.1` / `localhost` / `::1`），拒绝 DNS rebinding
- `Content-Security-Policy`（`script-src 'self'`，`/docs`、`/redoc` 单独放宽）
- `X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`

## 恢复说明与已知限制

| 类别 | 说明 |
|------|------|
| 逐字节一致 | 核心算法与校验函数（parse_result、comparison、evaluate、config 等）经 3.8 字节码逐条对拍 |
| 手写重建 | `app/main.py` 等装配产物由 `tools/recover/assemble.py` 生成；手写片段在 `tools/recover/manual/`，优先级最高 |
| 尚未验证 | `workflow._execute` 等长流程业务为手写重建（near 级），需原厂或业务方确认 |
| 已知技术债 | 前端单文件 3,900 行、107 处 `innerHTML`、19 处 `confirm()`；无障碍与移动端适配待 P1 处理 |

> 不要手工修改 `app/*.py`：重新运行 `python tools/recover/assemble.py` 会覆盖。
> 需要改被恢复的函数，请改 `tools/recover/manual/<module>.<func>.py` 后重新装配。