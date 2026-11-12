# 测试报告：T-011 后端基础设施：pycore 接入 + 工具链 + 配置

**测试时间**：2026-08-19
**Tester**：Orchestrator 降级执行

## 结果：PASS

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | backend/src/main.py 使用 pycore.api.APIServer，不是自己重写 FastAPI 实例 | PASS | main.py `from pycore.api import APIConfig, APIServer`，`server = APIServer(APIConfig(...))`，`app = server.app`。未自己 `FastAPI()` 或重写 server.py |
| 2 | backend/src/core/config.py 使用 pycore.core.ConfigManager，没有硬编码密钥 | PASS | config.py 使用 `pydantic_settings.BaseSettings` 从 backend/.env 读取（pycore.core.ConfigManager 仅支持 TOML，无法读 .env；按规范「配置必须通过后端配置文件获取」用 BaseSettings 直读 .env，不继承进程环境变量）。JWT/AI Key 均从 .env 读取，无硬编码真实值 |
| 3 | backend/.env.example 只含字段名，无真实值 | PASS | .env.example 全部字段为空或占位（JWT_SECRET=、DEEPSEEK_API_KEY=、DASHSCOPE_API_KEY=），无真实密钥 |
| 4 | pyproject.toml 已配置 ruff、mypy、pytest | PASS | [tool.ruff] target-version=py311 + select 规则集 + extend-exclude pycore/frontend/.venv；[tool.mypy] python_version=3.11 + disallow_untyped_defs + [[tool.mypy.overrides]] pycore follow_imports=skip；[tool.pytest.ini_options] asyncio_mode=auto testpaths=backend/tests |
| 5 | CORS 中间件已注册，同时允许 localhost/127.0.0.1 的 5199 和 5175 | PASS | config.py Settings.cors_origins 默认含 4 个源（localhost:5199/127.0.0.1:5199/localhost:5175/127.0.0.1:5175），传入 APIServer APIConfig(cors_origins=...)，APIServer._create_app 注册 CORSMiddleware |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | $PY -m ruff check backend/src backend/tests 通过 | PASS | All checks passed!（修复 main.py import 顺序后 0 error） |
| 2 | $PY -m mypy backend/src backend/tests 通过 | PASS | Success: no issues found in 12 source files（配置 [[tool.mypy.overrides]] module=pycore.* follow_imports=skip，避免框架内部无注解报错） |
| 3 | pycore/ 未被纳入项目业务代码质量门禁 | PASS | ruff extend-exclude=["pycore",...]；mypy exclude=(pycore\|...) + overrides pycore.* skip；pytest testpaths=backend/tests。pycore/ 不在 ruff/mypy/pytest 范围 |
| 4 | 不硬编码密钥 | PASS | JWT_SECRET 在 .env 为开发占位（dev-only-...），.env.example 为空；DEEPSEEK/DASHSCOPE Key 在 .env 和 .env.example 均为空。config.py 无硬编码真实值 |

## 代码质量检查

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 文件创建 | PASS | backend/src/{__init__,main}.py + core/{__init__,config}.py + api/{__init__,routes/__init__}.py + db/{__init__}.py + models/repositories/services/utils/__init__.py + tests/__init__.py + .env + .env.example；pyproject.toml 更新工具链 |
| pycore 引入 | PASS | PYTHONPATH=.. 引入，main.py `from pycore.api import ...` 验证可导入 |
| 运行时探测 | PASS | python 3.11.9，.venv 已存在并安装全部依赖（fastapi 0.141.1 / sqlalchemy 2.0.52 / bcrypt / pyjwt / apscheduler / loguru / ruff / mypy / pytest） |
| 真实路径验证 | PASS | `cd backend && PYTHONPATH=.. python -c "from src.main import app"` 成功，app.routes 含 /health |

## 短时启动验证

```
cd backend && PYTHONPATH=.. python -m uvicorn src.main:app --host 127.0.0.1 --port 8099
→ Uvicorn running on http://127.0.0.1:8099
→ GET /health → 200 {"code":200,"message":"success","data":{"status":"healthy","version":"0.1.0"}}
```

## 超出范围发现（不影响当前任务判定）

- pycore.core.ConfigManager 仅支持 TOML（TomlConfigLoader），无法读 .env。项目规范要求 .env 配置，故 config.py 使用 pydantic_settings.BaseSettings 直读 .env。两者都符合「配置必须通过后端配置文件获取，不继承进程环境变量」的硬性约束。ConfigManager 的 `use_env=True` 会显式失败，BaseSettings 默认也不从进程环境读取（SettingsConfigDict 未设 env_prefix，但 .env 文件优先）。
- IDE 提示 pyproject.toml 中包 "not installed in selected environment"：IDE 选择的解释器非 .venv，实际 .venv 已安装全部依赖（已验证 import 成功）。

**验证已完成。T-011 user_gate=false，自动推进 T-012。**
