# 多模态测试平台 — 接口契约（反向整理）

> 来源：由 `app/main.py`（FastAPI）的 OpenAPI 输出反向整理，**未经原厂确认**。
> 基址：`http://127.0.0.1:8735`（可用 `MMTEST_PORT` 覆盖）。所有接口仅监听本机。
> 整理日期：2026-11-05 ｜ 接口总数：111 个操作 / 89 条路径

## 通用约定

- 编码：JSON（`multipart/form-data` 仅上传类接口）。
- 错误：业务异常统一 `{"detail": "<面向用户的中文提示>"}`；参数校验失败为 FastAPI 标准 422。
- 文件下载：`/api/file/...` 与 `/api/runs/{id}/export.csv` 返回二进制/CSV。
- 安全：所有响应带 CSP / `X-Content-Type-Options` / `Referrer-Policy`；Host 不在白名单直接 400。
- 分页：列表接口现状为**全量返回** `{"items": [...]}`，不支持分页参数（见 `docs/Plan.md` 待办）。
- 鉴权：无。

## 按领域分组的接口

### 配置与运行环境

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/config` | - | 读取配置，API Key 已掩码 |
| PUT | `/api/config` | `ConfigIn` | 保存配置；掩码值会被还原为原 Key |
| POST | `/api/config/test` | - | 测试连通性 |
| GET | `/api/keys/stats` | - | 各 Key 使用/冷却状态 |
| GET | `/api/help` | - | 内置帮助文本 |
| GET | `/api/version` | - | 版本、构建时间、提交号、Python 与运行形态（源码/打包） |

### 首页与示例

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/dashboard` | - | 首页聚合数据 |
| GET | `/api/demo/status` | - | 示例项目是否已创建 |
| POST | `/api/demo/create` | `{"n": int}` | 创建示例项目（图 + 提示词 + 真值） |

### 项目与图片集

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET/POST | `/api/projects` | `ProjectIn` | 列出 / 新建项目 |
| GET/DELETE | `/api/projects/{name}` | - | 项目详情 / 删除 |
| GET/POST | `/api/datasets` | `DatasetIn` | 列出 / 新建图片集 |
| DELETE | `/api/datasets/{name}` | - | 删除图片集 |
| POST | `/api/datasets/{name}/import` | `ImportIn` | 从本地目录导入 |
| POST | `/api/datasets/{name}/upload` | multipart `files[]` | 上传图片 |
| GET | `/api/datasets/{name}/images` | - | 图片列表（含 split） |
| GET | `/api/datasets/{name}/meta` | - | 图片集元信息 |
| DELETE | `/api/datasets/{name}/image?rel=` | - | 删除单图 |
| PUT | `/api/datasets/{name}/split` | `SplitIn` | 设置单图分组 |

### 提示词与版本

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET/POST | `/api/prompts` | `PromptIn` | 列出 / 新建提示词 |
| DELETE | `/api/prompts/{name}` | - | 删除提示词全部版本 |
| GET | `/api/prompts/template` | - | 五段式骨架与最小协议模板 |
| GET/PUT | `/api/prompts/{name}/settings` | `SettingsIn` | 输出模式、字段映射、状态标签 |
| PUT | `/api/prompts/{name}/meta` | `PromptMetaIn` | 分组等元信息 |
| POST | `/api/prompts/{name}/versions` | `VersionIn` | 新增版本 |
| GET/PUT/DELETE | `/api/prompts/{name}/versions/{version}` | `NoteIn` | 版本详情 / 备注与状态 / 删除 |
| GET | `/api/prompts/{name}/diff?v1=&v2=` | - | 版本差异 |
| POST | `/api/prompts/{name}/rollback` | `RollbackIn` | 回滚到指定版本 |
| POST | `/api/prompts/{name}/merge` | `MergeIn` | 按模块合并版本 |
| GET | `/api/prompts/{name}/best` | - | 最优版本（按评估指标） |
| POST | `/api/prompts/{name}/rename` | `PromptRenameIn` | 重命名 |
| POST | `/api/prompts/{name}/duplicate` | `PromptRenameIn` | 复制 |

### 运行

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET/POST | `/api/runs` | `RunIn` | 列出 / 创建运行（`auto_start` 默认 true） |
| GET/DELETE | `/api/runs/{run_id}` | - | 运行详情 / 删除 |
| POST | `/api/runs/{run_id}/start` | - | 启动 |
| POST | `/api/runs/{run_id}/stop` | - | 停止 |
| GET | `/api/runs/{run_id}/images` | - | 结果图片清单 |
| GET | `/api/runs/{run_id}/result?rel=` | - | 单图结果（原图/推理图/解析/原始响应/提示词快照） |
| GET | `/api/runs/{run_id}/stability` | - | 稳定性统计 |
| GET | `/api/runs/{run_id}/errors` | - | 错误池 |
| GET | `/api/runs/{run_id}/export.csv` | - | 导出 CSV |
| GET | `/api/runs/{run1_id}/diff/{run2_id}` | - | 两次运行对比 |
| POST | `/api/runs/{run_id}/regression-dataset` | `RegressionIn` | 从失败样本建回归集 |
| POST | `/api/trial` | `TrialIn` | 免建运行的快速试跑 |

### 人工审核

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | `/api/reviews` | `ReviewIn` | 保存单图审核 |
| GET | `/api/runs/{run_id}/reviews` | - | 审核列表与汇总 |
| GET | `/api/runs/{run_id}/review?rel=&repeat=` | - | 单图审核详情 |
| POST | `/api/runs/{run_id}/reviews/batch` | `ReviewBatchIn` | 批量审核（按 scope） |
| POST | `/api/runs/{run_id}/reviews/reuse` | `ReviewReuseIn` | 从其他运行复用人工基线 |

### 裁判与优化

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | `/api/runs/{run_id}/judge` | `JudgeIn` | 启动裁判任务 |
| POST | `/api/runs/{run_id}/judge/stop` | - | 停止裁判 |
| GET | `/api/runs/{run_id}/judge-job` | - | 该运行当前裁判任务状态 |
| GET | `/api/judge-jobs` | - | 全部裁判任务 |
| GET/DELETE | `/api/runs/{run_id}/judgments` | - | 裁判结论列表 / 清空 |
| GET | `/api/runs/{run_id}/judgment?rel=` | - | 单图裁判结论 |
| POST | `/api/prompt-ai/optimize` | `OptimizeIn` | 生成优化建议（不改 output_format） |
| GET | `/api/prompt-ai/optimizations` | - | 优化记录列表 |
| GET/DELETE | `/api/prompt-ai/optimizations/{record_id}` | - | 记录详情 / 删除 |
| POST | `/api/prompt-ai/optimizations/{record_id}/save` | `CandidateSaveIn` | 保存为提示词新版本 |

### 提示词生成（对话）

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | `/api/prompt-ai/parse-sections` | `PromptParseIn` | 拆解五段式 |
| GET/POST | `/api/prompt-ai/sessions` | `PromptSessionIn` | 会话列表 / 新建 |
| GET/PUT/DELETE | `/api/prompt-ai/sessions/{session_id}` | `PromptSessionUpdateIn` | 详情 / 改名分组 / 删除 |
| POST | `/api/prompt-ai/sessions/{session_id}/attachments` | multipart `files[]` | 上传附件 |
| POST | `/api/prompt-ai/sessions/{session_id}/attachments/from-dataset` | `SessionDatasetAttachmentIn` | 引用数据集图片 |
| POST | `/api/prompt-ai/sessions/{session_id}/messages` | `PromptChatIn` | 发送消息（后台生成） |
| GET | `/api/prompt-ai/sessions/{session_id}/chat-status` | - | 轮询生成状态 |
| POST | `/api/prompt-ai/sessions/{session_id}/save` | `PromptSessionSaveIn` | 保存为提示词版本 |
| GET/PUT/DELETE | `/api/prompt-profiles{,/{name}}` | `PromptProfileIn` | 生成/裁判/优化模板 |

### 真值与评估

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET/POST | `/api/truth` | `TruthIn` | 真值任务列表 / 新建 |
| GET/DELETE | `/api/truth/{task}` | - | 任务详情 / 删除 |
| GET | `/api/truth/{task}/images` | - | 待标注图片 |
| POST | `/api/truth/{task}/label` | `LabelIn` | 保存单图标签 |
| GET | `/api/truth/for-image?dataset=&rel=` | - | 查某图已有真值 |
| POST | `/api/truth/sync-run/{run_id}` | - | 从运行同步真值 |
| GET/POST | `/api/evals` | `EvalIn` | 评估列表 / 新建评估 |
| GET/DELETE | `/api/evals/{eval_id}` | - | 评估详情 / 删除 |
| GET | `/api/evals/compare?ids=` | - | 多次评估对比 |

### 字段提取与自动迭代

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/extract/fields?run_id=` | - | 可选字段路径 |
| POST | `/api/extract` | `ExtractIn` | 按条件筛样本并导出 |
| GET/POST | `/api/workflows` | `WorkflowIn` | 自动迭代任务列表 / 新建 |
| GET/DELETE | `/api/workflows/{job_id}` | - | 详情 / 删除 |
| POST | `/api/workflows/{job_id}/pause` | - | 暂停 |
| POST | `/api/workflows/{job_id}/resume` | - | 续跑 |

### 静态与文件

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 单页应用入口 |
| GET | `/static/{path}` | 前端资源（`app.js`、`style.css`） |
| GET | `/api/file/dataset/{dataset}/{rel}` | 数据集原图 |
| GET | `/api/file/run/{run_id}/image/{rel}` | 运行原图快照 |
| GET | `/api/file/run/{run_id}/annotated/{rel}` | 推理标注图 |
| GET | `/api/file/review/{run_id}/annotated/{rel}` | 审核用标注图 |
| GET | `/api/file/truth/{task}/{rel}` | 真值图片 |
| GET | `/api/file/prompt-session/{session_id}/{name}` | 会话附件 |
| GET | `/docs`、`/redoc`、`/openapi.json` | 自动文档（放宽 CSP 以加载 CDN） |

## 请求模型（Pydantic）

只列必填与关键可选字段；完整定义以 `GET /openapi.json` 为准。

| 模型 | 必填 | 关键可选 |
|------|------|----------|
| `ProjectIn` | `name` | `description` |
| `DatasetIn` | `name` | `project` |
| `ImportIn` | `path` | - |
| `SplitIn` | `rel`、`split` | - |
| `PromptIn` | `name` | `content`、`note`、`group`、`use_template=false` |
| `VersionIn` | - | `content`、`sections`、`note`、`parent`、`branch`、`status`、`change_summary`、`expected_effect`、`changed_modules`、`source_run`、`judge_refs` |
| `SettingsIn` | - | `output_mode=fixed`、`map`、`status_labels` |
| `RunIn` | `dataset`、`prompt_name`、`prompt_version` | `model`、`site`、`repeat=1`、`temperature`、`seed`、`max_tokens`、`concurrency`、`split`、`show_fields`、`auto_start=true` |
| `ReviewIn` | `run_id`、`rel`、`verdict` | `repeat=1`、`expected_status`、`expected_objects`、`reason`、`reviewer` |
| `ReviewBatchIn` | `verdict` | `scope=unreviewed` |
| `ReviewReuseIn` | `source_run_id` | `overwrite=false` |
| `JudgeIn` | - | `model`、`site`、`concurrency=2`、`coverage_threshold=1.0`、`force=false`、`profile_name` |
| `OptimizeIn` | `prompt_name`、`version`、`run_id` | `model`、`site`、`max_items=50`、`profile_name` |
| `TrialIn` | `dataset`、`prompt_content` | `images`、`sample=0`、`model`、`site`、`temperature`、`seed`、`max_tokens`、`output_mode`、`map`、`status_labels`、`show_fields` |
| `TruthIn` | `name`、`kind`、`labels`、`dataset` | - |
| `LabelIn` | `rel`、`labels` | - |
| `EvalIn` | `run_id`、`truth_task` | `field`、`set_field`、`name` |
| `ExtractIn` | `run_id`、`output_name` | `mode=filter`、`logic=and`、`conditions`、`group_field`、`sources` |
| `WorkflowIn` | `baseline_run_id` | `prompt_name`、`source_version`、`split`、模型/站点、`max_rounds=5`、`patience=2`、`min_improvement=0.005`、`min_parse_rate=0.98`、`min_protocol_rate=0.95`、`min_accuracy=0.95`、`concurrency=2`、`candidates_per_round=1`、`quick_test_size=0` 等 |

## 关键响应形状

- `GET /api/config`：`{"api": {"sites": [...]}, "defaults": {...}}`，`api_keys` 为掩码串。
- `GET /api/runs/{id}`：运行元数据 + `total/done/failed/status` + `images_snapshot` + 提示词快照。
- `GET /api/runs/{id}/result`：`{"parsed": {...}, "raw": "...", "image": url, "annotated": url, "prompt": {...}}`。
- 列表接口：`{"items": [...]}`。
- 写接口：多数返回保存后的对象；`{"ok": true}` 形式用于删除/批量操作。

## 契约差异与待办

1. 列表接口无分页，大数据集下响应体可能很大（前端已用缓存与增量渲染缓解）。
2. 错误体只有 `detail` 字符串，无机器可读错误码。
3. 无鉴权与 CSRF 防护，依赖本机绑定 + Host 白名单。
4. `/api/extract` 的 `sources` 无默认值，调用方必须显式传入。
