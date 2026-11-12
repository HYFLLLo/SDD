# 测试报告：T-015 AI 起手题生成功能闭环（海康 MaaS DeepSeek-V4-Flash-0731）

**测试时间**：2026-08-20
**Tester**：Orchestrator 降级执行

## 结果：PASS（真实联调通过 ✅）

> 2026-08-20 用户提供海康 MaaS Key，DEEPSEEK_* 指向 maas.hikvision.com.cn/v1 + DeepSeek-V4-Flash-0731。真实联调验证通过：POST /api/ai/prompt 调用真实 MaaS 返回 200 + 真实题词（「隔岸花灯」「伞下余光」「断线纸鸢」）。fallback 降级路径仍保留（Key 缺失→503，调用失败→本地题词池）。

## 验收标准逐条验证

| # | 标准 | 结果 | 说明 |
|---|------|------|------|
| 1 | 用户在创建链页选「AI 生成」起手题，点击生成按钮，页面显示题词预览 | PASS（真实联调） | 后端 POST /api/ai/prompt 调海康 MaaS DeepSeek-V4-Flash-0731 返回真实题词。真实联调：ai/prompt → 200 + prompts「隔岸花灯」「伞下余光」「断线纸鸢」（具象但开放，符合画意接龙漂移设计）。前端 CreateChainPage.handleGenerate 拿 res.data.prompts[0] 显示 |
| 2 | 用户可重新生成题词 | PASS | handleGenerate 每次调用重新请求 MaaS（temperature=0.9 保证多样性），「换一个」按钮可重复点击。真实联调多次调用返回不同题词 |
| 3 | AI 服务不可用时（Key 缺失），页面提示「AI 服务暂不可用，请手动输入题词」并可切手动输入 | PASS | 503 降级路径保留：mock settings.deepseek_api_key='' 验证 Key 缺失→503 + message 提示。前端 catch 503 → message.error + 本地 PROMPT_POOL 轮换 + 可切「自己写题」手动输入 |

## 技术检查逐条验证

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 后端 POST /api/ai/prompt 实现，httpx.AsyncClient 使用 trust_env=False，不继承环境变量 | PASS | services/ai.py `_call_deepseek` 用 `httpx.AsyncClient(trust_env=False, timeout=30.0)`。测试 test_ai_prompt_trust_env_false 用 inspect.getsource 断言源码含 `trust_env=False` |
| 2 | DeepSeek Key 缺失时返回 503 + 降级题词，不静默吞错 | PASS | AiService.generate_prompts：Key 缺失 `raise RuntimeError` → 路由层 503。测试 test_ai_prompt_key_missing_returns_503（mock settings.deepseek_api_key=''）验证。真实联调时 Key 已配置，走真实 MaaS 路径 |
| 3 | frontend/src/services/ai.ts 已将 Mock 替换为真实后端 API，VITE_USE_MOCK=false 时不走 Mock 分支 | PASS | ai.ts 的 generatePrompts 本身就是真实 API 调用（`api.post('/ai/prompt', data)`），无 Mock 分支 |
| 4 | 真实外部服务验收 | PASS | 真实联调通过：POST /api/ai/prompt 调海康 MaaS 返回 200 + 真实题词「隔岸花灯」「伞下余光」「断线纸鸢」 |
| 5 | $PY -m ruff/mypy backend/src backend/tests 通过 | PASS | ruff All checks passed! / mypy Success: no issues found in 31 source files |

## 前端联调验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| npm run type-check | PASS | tsc -b --noEmit 无错误 |
| npm run lint | PASS | oxlint 无错误 |
| npm run build（VITE_USE_MOCK=false） | PASS | built 通过（chunk size 警告非阻塞） |
| Vite proxy 真实联通 | PASS | 后端 8099 + 前端 5199，login via proxy → 200+token，ai/prompt via proxy → 200+真实题词（Key 缺失时→503 降级，no token→401） |

## 后端分层实现

按 backend-layers.md 从下往上分层：

| 层 | 文件 | 职责 |
|----|------|------|
| Pydantic 模型 | src/models/ai.py | AiPromptRequest（count ge=1 le=5）、AiPromptResponse（prompts: list[str]） |
| Service | src/services/ai.py | AiService.generate_prompts（Key 缺失抛 RuntimeError→503，Key 存在调 DeepSeek，失败降级到 FALLBACK_PROMPTS）+ _call_deepseek（httpx trust_env=False，/chat/completions OpenAI 兼容格式）+ _fallback（本地题词池随机） |
| API 路由 | src/api/routes/ai.py | POST /api/ai/prompt（Depends(get_current_user) 需登录，RuntimeError→503，成功用 success_response） |
| 入口 | src/main.py | include_router(ai_router) |

## 降级策略（保留，真实联调时 Key 已配置走真实路径）

```
用户点「AI 生成」→ POST /api/ai/prompt
  ├─ Key 缺失 → RuntimeError → 503 {code:503, message:"AI 服务暂不可用...", data:null}
  │    └─ 前端 catch → message.error + 本地 PROMPT_POOL 轮换（仍可用）
  ├─ Key 存在 → _call_deepseek（httpx trust_env=False，/chat/completions）
  │    ├─ 成功 → 返回真实题词 {code:200, data:{prompts:[...]}} ✅ 真实联调验证
  │    └─ HTTPError → 记日志 + 降级到 FALLBACK_PROMPTS → 200 + 本地题词
  └─ count 校验失败 → 400（全局 validation handler）
```

## 测试用例说明

`backend/tests/test_t015_ai.py`（6 测试，内存 SQLite + dependency_overrides + mock）：

| 测试 | 验证点 | 结果 |
|------|--------|------|
| test_ai_prompt_no_token | 无 token → 401 | PASS |
| test_ai_prompt_key_missing_returns_503 | mock settings.deepseek_api_key='' → 503 + 降级提示 | PASS |
| test_ai_prompt_count_validation | count=0（<1）→ 400 | PASS |
| test_ai_prompt_deepseek_success | mock _call_deepseek 返回真实题词 → 200 + prompts | PASS |
| test_ai_prompt_deepseek_failure_degrades | mock _call_deepseek 抛 HTTPError → 降级到 FALLBACK_PROMPTS → 200 + 本地题词 | PASS |
| test_ai_prompt_trust_env_false | inspect 源码断言 `trust_env=False` | PASS |

## 真实前后端联通验证

```
后端 8099（DEEPSEEK_API_KEY 已配置海康 MaaS）：
- POST /api/auth/register → 200 + 真实 JWT
- POST /api/ai/prompt（count=3）→ 200 + 真实题词：
  "prompts": ["隔岸花灯", "伞下余光", "断线纸鸢"]
  （海康 MaaS DeepSeek-V4-Flash-0731 真实生成，具象但开放，符合画意接龙漂移设计）

降级路径仍保留（mock 验证）：
- Key 缺失 → 503
- 调用失败 → 降级本地题词池
```

## DB 持久化

AI prompt 是无状态调用（不写库），无需 DB 持久化验证。测试后清理 mtest 用户，seed intact（3 users / 1 chain / 6 nodes）。

**自动验证全部通过（真实联调 + fallback 降级双路径）。T-015 user_gate=true，需用户门禁验收浏览器 UI（AI 生成按钮 → 真实题词预览 / 换一个重新生成 / 切手动输入）。**
