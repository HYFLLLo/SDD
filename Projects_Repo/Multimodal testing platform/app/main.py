"""FastAPI 主入口：REST API + 前端静态托管"""
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import datasets, prompts, runner, truth, evaluate, extractor, stats, trial, reviews, judge, prompt_ai, prompt_profiles, workflow, demo
from .config import BASE_DIR, load_config, save_config
from .maas import MaaSClient
from .schema import OUTPUT_REFERENCE, HEAD_KEYS, OBJECT_KEYS
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if getattr(__import__("sys"), "frozen", False):
    import sys
    WEB_DIR = os.path.join(sys._MEIPASS, "web")
app = FastAPI(title="多模态大模型能力测试平台")

def _err(e: Exception, code: int = 400):
    raise HTTPException(status_code=code, detail=(str(e)))


def _mask_key(key: str) -> str:
    """API Key 掩码：仅保留前后若干位，其余以省略号代替。"""
    key = str(key)
    if len(key) > 12:
        return key[:6] + "..." + key[-4:]
    return key


def _restore_masked_keys(payload: dict, current: dict):
    """把前端回传的脱敏占位符还原为已保存的真实 Key。

    配置页不再回显明文 Key：未修改时提交的是形如 ``sk-4fa...abcd`` 的占位符，
    这里按掩码匹配回真实值；用户新增或替换的（不含省略号的）行原样保留。
    """
    index = {}
    for s in (current.get("api") or {}).get("sites") or []:
        for k in s.get("api_keys") or []:
            index[_mask_key(k)] = k

    for s in (payload.get("api") or {}).get("sites") or []:
        keys = s.get("api_keys")
        if not isinstance(keys, list):
            continue
        restored = []
        for item in keys:
            text = str(item).strip()
            if not text:
                continue
            restored.append(index.get(text, text))
        s["api_keys"] = restored


@app.get("/api/config")
def get_config():
    cfg = load_config()
    out = dict(cfg)
    sites = []
    for s in cfg["api"].get("sites", []):
        safe = {k: v for k, v in s.items() if k != "api_keys"}
        safe["api_keys_masked"] = [_mask_key(k) for k in s.get("api_keys", [])]
        sites.append(safe)

    out["api"] = dict((cfg["api"]), sites=sites)
    return out


class ConfigIn(BaseModel):

    api: dict
    defaults: dict


@app.put("/api/config")
def put_config(cfg: ConfigIn):
    payload = cfg.dict()
    _restore_masked_keys(payload, load_config())
    save_config(payload)
    return {"ok": True}


@app.post("/api/config/test")
def api_test_config(site: Optional[str] = None):
    """测试站点连通性。优先拉取模型列表，404 时用对话接口探测。site 为空时测试全部站点。"""
    try:
        return MaaSClient(load_config()).test_connection(site=(site or None))
    except Exception as e:
        _err(e)


@app.get("/api/keys/stats")
def api_key_stats(site: Optional[str] = None):
    try:
        client = MaaSClient(load_config())
        return {'items':client.key_stats(site=(site or None)),  'recommended_concurrency':client.recommended_concurrency(site=(site or None))}
    except Exception as e:
        _err(e)


@app.get("/api/demo/status")
def api_demo_status():
    return demo.status()


@app.post("/api/demo/create")
def api_demo_create():
    try:
        return demo.create()
    except Exception as e:
        _err(e)


@app.get("/api/help")
def api_help():
    """应用内帮助：返回操作指南全文。

    exe 场景读打包进 _MEIPASS 的资源（build_exe.py 通过 --add-data 内置），
    开发场景读项目根目录的 操作指南.txt。
    """
    import sys
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(sys._MEIPASS, "操作指南.txt"))
    candidates.append(os.path.join(BASE_DIR, "操作指南.txt"))
    for p in candidates:
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return {"text": f.read().lstrip("\ufeff")}
    return {"text": "未找到操作指南文件（操作指南.txt）。"}


@app.get("/api/dashboard")
def api_dashboard():
    """首页工作台聚合接口：一次返回流程各步骤状态与待办。

    只对最近 8 个运行计算审核/裁判进度，避免遍历全部历史数据拖慢加载。
    """
    cfg = load_config()
    sites = (cfg.get("api") or {}).get("sites") or []
    site_info = [{'name':s.get("name") or "",  'models':len(s.get("models") or []), 
     'has_keys':bool(s.get("api_keys"))} for s in sites]
    try:
        projects = datasets.list_projects()
    except Exception:
            projects = []
    try:
        prompt_items = prompts.list_prompts()
    except Exception:
            prompt_items = []
    try:
        runs = runner.list_runs()
    except Exception:
            runs = []
    try:
        judge_jobs = judge.list_jobs()
    except Exception:
            judge_jobs = []
    try:
        wf_jobs = workflow.list_jobs()
    except Exception:
            wf_jobs = []
    try:
        optimizations = prompt_ai.list_optimizations("")
    except Exception:
            optimizations = []
    try:
        truth_tasks = truth.list_tasks()
    except Exception:
            truth_tasks = []
    try:
        evals = evaluate.list_evals()
    except Exception:
            evals = []
    dataset_count = sum((p.get("dataset_count", 0) for p in projects))
    image_count = sum((p.get("image_count", 0) for p in projects))
    recent = []
    for r in runs[:8]:
        item = {k: r.get(k) for k in ('id', 'prompt_name', 'prompt_version',
                                      'dataset', 'dataset_name', 'dataset_project',
                                      'dataset_split', 'status', 'done',
                                      'failed', 'total', 'created', 'model',
                                      'error')}
        try:
            m = reviews.metrics(r["id"])
            item["review"] = {'reviewed':m["reviewed"],  'accuracy':m["accuracy"],  'counts':m["counts"]}
        except Exception:
                item["review"] = None
        try:
            item["judge"] = judge.coverage(r["id"])
        except Exception:
                item["judge"] = None
        job = next((j for j in judge_jobs if j.get("run_id") == r["id"]), None)
        item["judge_status"] = (job or {}).get("status")
        item["judge_active"] = bool((job or {}).get("is_active"))
        recent.append(item)
    return {'sites':site_info,  'default_model':(cfg.get("defaults") or {}).get("model") or "", 
     'project_count':len([p for p in projects if not p.get("legacy")]), 
     'dataset_count':dataset_count, 
     'image_count':image_count, 
     'prompt_count':len(prompt_items), 
     'prompts':[{'name':p["name"], 
      'latest':(p.get)("latest"),  'best_accuracy':(p.get)("best_accuracy")} for p in prompt_items[:20]], 
     'run_count':len(runs), 
     'running_count':len([r for r in runs if r.get("status") == "running"]), 
     'recent_runs':recent, 
     'active_judges':len([j for j in judge_jobs if j.get("is_active")]), 
     'active_workflows':len([w for w in wf_jobs if w.get("is_active")]), 
     'optimization_count':len(optimizations), 
     'truth_count':len(truth_tasks), 
     'truth_labeled':sum(((t.get("progress") or {}).get("labeled", 0) for t in truth_tasks)), 
     'truth_tasks':[{'id':(t.get)("id"), 
      'name':(t.get)("name"),  'dataset':(t.get)("dataset"), 
      'kind':(t.get)("kind"),  'auto_sync':bool(t.get("auto_sync")), 
      'labeled':((t.get("progress") or {}).get)("labeled", 0), 
      'total':((t.get("progress") or {}).get)("total", 0)} for t in truth_tasks[:10]], 
     'eval_count':len(evals), 
     'eval_tasks':sorted({e.get("truth_task") for e in evals if e.get("truth_task")})}


@app.get("/api/datasets")
def api_datasets():
    return {"items": (datasets.list_datasets())}


@app.get("/api/projects")
def api_projects():
    return {"items": (datasets.list_projects())}


class ProjectIn(BaseModel):

    name: str
    description = ""
    description: Optional[str]


@app.post("/api/projects")
def api_create_project(body: ProjectIn):
    try:
        return datasets.create_project(body.name, body.description or "")
    except Exception as e:
        _err(e)


@app.get("/api/projects/{name}")
def api_get_project(name: str):
    try:
        return datasets.get_project(name)
    except Exception as e:
        _err(e, 404)


@app.delete("/api/projects/{name}")
def api_delete_project(name: str):
    try:
        datasets.delete_project(name)
        return {"ok": True}
    except Exception as e:
        _err(e)


class DatasetIn(BaseModel):

    name: str
    project = ""
    project: Optional[str]


@app.post("/api/datasets")
def api_create_dataset(d: DatasetIn):
    try:
        ref = datasets.dataset_ref(d.project, d.name) if d.project else d.name
        if datasets.dataset_exists(ref):
            raise ValueError("同名图片集已存在")
        datasets.create_dataset(d.name, d.project or "")
        return {'ok':True,  'ref':ref}
    except Exception as e:
        _err(e)


class ImportIn(BaseModel):

    path: str


@app.post("/api/datasets/{name}/import")
def api_import(name: str, body: ImportIn):
    try:
        n = datasets.import_from_path(name, body.path)
        return {'ok':True,  'count':n}
    except Exception as e:
        _err(e)


@app.post("/api/datasets/{name}/upload")
async def api_upload(name: str, files: List[UploadFile] = File(...), sub: str = Form('')):
    try:
        n = 0
        for f in files:
            data = await f.read(datasets.MAX_UPLOAD_BYTES + 1)
            datasets.save_upload(name, (f.filename), data, sub=sub)
            n += 1

        return {'ok':True, 
         'count':n}
    except Exception as e:
        _err(e)


@app.delete("/api/datasets/{name}")
def api_del_dataset(name: str):
    try:
        datasets.delete_dataset(name)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/datasets/{name}/images")
def api_dataset_images(name: str):
    return {"items": (datasets.scan_images(name))}


@app.get("/api/datasets/{name}/meta")
def api_dataset_meta(name: str):
    try:
        return datasets.get_dataset(name)
    except Exception as e:
        _err(e, 404)


@app.delete("/api/datasets/{name}/image")
def api_del_dataset_image(name: str, rel: str):
    try:
        datasets.delete_image(name, rel)
        return {"ok": True}
    except Exception as e:
        _err(e, 404)


class SplitIn(BaseModel):

    rel: str
    split: str


@app.put("/api/datasets/{name}/split")
def api_set_dataset_split(name: str, body: SplitIn):
    try:
        return datasets.set_image_split(name, body.rel, body.split)
    except Exception as e:
        _err(e)


@app.get("/api/prompts")
def api_prompts():
    return {"items": (prompts.list_prompts())}


@app.get("/api/prompts/template")
def api_prompt_template():
    return {'reference':OUTPUT_REFERENCE, 
     'head_keys':HEAD_KEYS, 
     'object_keys':OBJECT_KEYS}


class PromptIn(BaseModel):

    name: str
    content = ""
    content: Optional[str]
    note = ""
    note: Optional[str]
    group = ""
    group: Optional[str]
    use_template = False
    use_template: Optional[bool]


@app.post("/api/prompts")
def api_create_prompt(p: PromptIn):
    try:
        return prompts.create_prompt(p.name, p.content or "", p.note or "", p.group or "", bool(p.use_template))
    except Exception as e:
        _err(e)


class PromptMetaIn(BaseModel):

    group = None
    group: Optional[str]


@app.put("/api/prompts/{name}/meta")
def api_prompt_meta(name: str, body: PromptMetaIn):
    try:
        return prompts.update_meta(name, group=(body.group))
    except Exception as e:
        _err(e)


class VersionIn(BaseModel):

    content = ""
    content: str
    sections = None
    sections: Optional[dict]
    note = ""
    note: Optional[str]
    parent = None
    parent: Optional[int]
    branch = "main"
    branch: Optional[str]
    status = "draft"
    status: Optional[str]
    change_summary = ""
    change_summary: Optional[str]
    expected_effect = ""
    expected_effect: Optional[str]
    changed_modules = Field(default_factory=list)
    changed_modules: List[str]
    source_run = None
    source_run: Optional[str]
    judge_refs = Field(default_factory=list)
    judge_refs: List[str]


@app.post("/api/prompts/{name}/versions")
def api_add_version(name: str, v: VersionIn):
    try:
        return prompts.add_version(name, v.content, v.note or "", v.parent, v.dict())
    except Exception as e:
        _err(e)


@app.get("/api/prompts/{name}/versions/{version}")
def api_get_version(name: str, version: int):
    try:
        return prompts.get_version(name, version)
    except Exception as e:
        _err(e, 404)


class NoteIn(BaseModel):

    note = ""
    note: str
    status = None
    status: Optional[str]


@app.put("/api/prompts/{name}/versions/{version}")
def api_update_version(name: str, version: int, body: NoteIn):
    try:
        prompts.update_version(name, version, note=(body.note), status=(body.status))
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.delete("/api/prompts/{name}/versions/{version}")
def api_del_version(name: str, version: int):
    try:
        prompts.delete_version(name, version)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/prompts/{name}/diff")
def api_diff(name: str, v1: int, v2: int):
    try:
        return {'rows':(prompts.diff_versions)(name, v1, v2), 
         'summary':(prompts.summary_diff)(name, v1, v2), 
         'sections':(prompts.diff_sections)(name, v1, v2)}
    except Exception as e:
        _err(e)


class RollbackIn(BaseModel):

    target: int
    note = ""
    note: Optional[str]


@app.post("/api/prompts/{name}/rollback")
def api_prompt_rollback(name: str, body: RollbackIn):
    try:
        return prompts.rollback(name, body.target, body.note or "")
    except Exception as e:
        _err(e)


class MergeIn(BaseModel):

    sources = Field(default_factory=dict)
    sources: dict
    note = ""
    note: Optional[str]
    branch = "main"
    branch: Optional[str]


@app.post("/api/prompts/{name}/merge")
def api_prompt_merge(name: str, body: MergeIn):
    try:
        return prompts.merge_versions(name, body.sources, body.note or "", body.branch or "main")
    except Exception as e:
        _err(e)


@app.get("/api/prompts/{name}/best")
def api_prompt_best(name: str, metric: str = 'accuracy'):
    try:
        return prompts.best_version(name, metric)
    except Exception as e:
        _err(e)


@app.delete("/api/prompts/{name}")
def api_del_prompt(name: str):
    try:
        prompts.delete_prompt(name)
        return {"ok": True}
    except Exception as e:
        _err(e)


class PromptRenameIn(BaseModel):

    new_name: str


@app.post("/api/prompts/{name}/rename")
def api_rename_prompt(name: str, body: PromptRenameIn):
    try:
        return prompts.rename_prompt(name, body.new_name)
    except Exception as e:
        _err(e)


@app.post("/api/prompts/{name}/duplicate")
def api_duplicate_prompt(name: str, body: PromptRenameIn):
    try:
        return prompts.duplicate_prompt(name, body.new_name)
    except Exception as e:
        _err(e)


@app.get("/api/prompts/{name}/settings")
def api_get_prompt_settings(name: str):
    try:
        return prompts.get_settings(name)
    except Exception as e:
        _err(e, 404)


class SettingsIn(BaseModel):

    output_mode = "fixed"
    output_mode: str
    map = Field(default_factory=dict)
    map: Optional[dict]
    status_labels = None
    status_labels: Optional[List[str]]


@app.put("/api/prompts/{name}/settings")
def api_put_prompt_settings(name: str, s: SettingsIn):
    try:
        return prompts.update_settings(name, s.dict())
    except Exception as e:
        _err(e)


@app.get("/api/runs")
def api_runs():
    return {"items": (runner.list_runs())}


class RunIn(BaseModel):

    dataset: str
    prompt_name: str
    prompt_version: int
    model = None
    model: Optional[str]
    site = None
    site: Optional[str]
    repeat = 1
    repeat: int
    temperature = None
    temperature: Optional[float]
    seed = None
    seed: Optional[int]
    max_tokens = None
    max_tokens: Optional[int]
    concurrency = None
    concurrency: Optional[int]
    split = None
    split: Optional[str]
    show_fields = Field(default_factory=list)
    show_fields: Optional[List[str]]
    auto_start = True
    auto_start: bool


@app.post("/api/runs")
def api_create_run(r: RunIn):
    try:
        run = runner.create_run(r.dict())
        if r.auto_start:
            runner.start_run(run["id"])
            run["status"] = "running"
        return run
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str):
    try:
        return runner.get_run(run_id)
    except Exception as e:
        _err(e, 404)


@app.post("/api/runs/{run_id}/start")
def api_start_run(run_id: str):
    try:
        return runner.start_run(run_id)
    except Exception as e:
        _err(e)


@app.post("/api/runs/{run_id}/stop")
def api_stop_run(run_id: str):
    runner.stop_run(run_id)
    return {"ok": True}


@app.delete("/api/runs/{run_id}")
def api_del_run(run_id: str):
    try:
        runner.delete_run(run_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}/images")
def api_run_images(run_id: str):
    try:
        return {"items": (runner.list_run_images(run_id))}
    except Exception as e:
        _err(e, 404)


@app.post("/api/runs/{run_id}/reparse")
def api_reparse_run(run_id: str):
    try:
        return runner.reparse_results(run_id)
    except Exception as e:
        _err(e, 404)


@app.get("/api/runs/{run_id}/result")
def api_run_result(run_id: str, rel: str, repeat: int = 1):
    try:
        return runner.get_result(run_id, rel, repeat)
    except Exception as e:
        _err(e, 404)


@app.get("/api/runs/{run_id}/stability")
def api_run_stability(run_id: str):
    try:
        return stats.run_stability(run_id)
    except Exception as e:
        _err(e, 404)


@app.get("/api/runs/{run_id}/export.csv")
def api_run_export(run_id: str):
    try:
        p = runner.export_csv(run_id)
        return FileResponse(p, media_type="text/csv", filename=f"{run_id}.csv")
    except Exception as e:
        _err(e, 404)


@app.get("/api/runs/{run1_id}/diff/{run2_id}")
def api_diff_runs(run1_id: str, run2_id: str):
    try:
        return runner.diff_runs(run1_id, run2_id)
    except Exception as e:
        _err(e, 404)


class TrialIn(BaseModel):

    dataset: str
    prompt_content: str
    images = None
    images: Optional[List[str]]
    sample = 0
    sample: Optional[int]
    model = None
    model: Optional[str]
    site = None
    site: Optional[str]
    temperature = None
    temperature: Optional[float]
    seed = None
    seed: Optional[int]
    max_tokens = None
    max_tokens: Optional[int]
    output_mode = "fixed"
    output_mode: Optional[str]
    map = None
    map: Optional[dict]
    status_labels = None
    status_labels: Optional[List[str]]
    show_fields = Field(default_factory=list)
    show_fields: Optional[List[str]]


@app.post("/api/trial")
def api_trial(t: TrialIn):
    try:
        return trial.run_trial(t.dict())
    except Exception as e:
        _err(e)


class PromptSessionIn(BaseModel):

    system_prompt = ""
    system_prompt: Optional[str]
    model = ""
    model: Optional[str]
    title = "提示词生成"
    title: Optional[str]
    profile_name = ""
    profile_name: Optional[str]
    site = ""
    site: Optional[str]
    group = ""
    group: Optional[str]


class PromptParseIn(BaseModel):

    content: str


@app.post("/api/prompt-ai/parse-sections")
def api_parse_prompt_sections(body: PromptParseIn):
    sections = prompts.extract_sections(body.content)
    return {'sections':sections, 
     'recognized':[key for key, value in sections.items() if value]}


@app.post("/api/prompt-ai/sessions")
def api_prompt_session(s: PromptSessionIn):
    try:
        return prompt_ai.create_session(s.system_prompt or "", s.model or "", s.title or "提示词生成", s.profile_name or "", s.site or "", s.group or "")
    except Exception as e:
        _err(e)


@app.get("/api/prompt-ai/sessions")
def api_prompt_sessions():
    return {"items": (prompt_ai.list_sessions())}


@app.get("/api/prompt-ai/sessions/{session_id}")
def api_get_prompt_session(session_id: str):
    try:
        return prompt_ai.get_session(session_id)
    except Exception as e:
        _err(e, 404)


class PromptSessionUpdateIn(BaseModel):

    title = None
    title: Optional[str]
    group = None
    group: Optional[str]


@app.put("/api/prompt-ai/sessions/{session_id}")
def api_update_prompt_session(session_id: str, body: PromptSessionUpdateIn):
    try:
        return prompt_ai.update_session(session_id, body.title, body.group)
    except Exception as e:
        _err(e)


@app.delete("/api/prompt-ai/sessions/{session_id}")
def api_delete_prompt_session(session_id: str):
    try:
        prompt_ai.delete_session(session_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.post("/api/prompt-ai/sessions/{session_id}/attachments")
async def api_session_upload_attachments(session_id: str, files: List[UploadFile] = File(...)):
    """上传图片附件到提示词生成会话"""
    try:
        payload = []
        for f in files:
            payload.append((f.filename or "image.jpg", await f.read()))

        return {"items": (prompt_ai.save_upload_attachments(session_id, payload))}
    except Exception as e:
        _err(e)


class SessionDatasetAttachmentIn(BaseModel):

    dataset: str
    rel: str


@app.post("/api/prompt-ai/sessions/{session_id}/attachments/from-dataset")
def api_session_dataset_attachment(session_id: str, body: SessionDatasetAttachmentIn):
    """从图片集中挑选图片作为会话附件"""
    try:
        return prompt_ai.add_dataset_attachment(session_id, body.dataset, body.rel)
    except Exception as e:
        _err(e)


class PromptChatIn(BaseModel):

    message: str
    model = None
    model: Optional[str]
    site = None
    site: Optional[str]
    attachment_ids = Field(default_factory=list)
    attachment_ids: Optional[List[str]]


@app.post("/api/prompt-ai/sessions/{session_id}/messages")
def api_prompt_chat(session_id: str, body: PromptChatIn):
    try:
        return prompt_ai.chat(session_id, body.message, body.model, body.site, body.attachment_ids or [])
    except Exception as e:
        _err(e)


@app.get("/api/prompt-ai/sessions/{session_id}/chat-status")
def api_prompt_chat_status(session_id: str):
    try:
        status = prompt_ai.chat_status(session_id)
        return {"status": (status or "idle")}
    except Exception as e:
        _err(e)


class PromptSessionSaveIn(BaseModel):

    name: str
    content: str
    note = "由提示词生成对话保存"
    note: Optional[str]
    parent = None
    parent: Optional[int]


@app.post("/api/prompt-ai/sessions/{session_id}/save")
def api_prompt_session_save(session_id: str, body: PromptSessionSaveIn):
    try:
        prompt_ai.get_session(session_id)
        if not body.content.strip():
            raise ValueError("提示词内容为空")
        if body.parent is None:
            return prompts.create_prompt(body.name, body.content, body.note or "")
        return prompts.add_version(body.name, body.content, body.note or "", body.parent)
    except Exception as e:
        _err(e)


class ReviewIn(BaseModel):

    run_id: str
    rel: str
    repeat = 1
    repeat: int
    verdict: str
    expected_status = None
    expected_status: Optional[str]
    expected_objects = Field(default_factory=list)
    expected_objects: Optional[List[dict]]
    reason = ""
    reason: Optional[str]
    reviewer = ""
    reviewer: Optional[str]


@app.post("/api/reviews")
def api_save_review(body: ReviewIn):
    try:
        saved = reviews.save_review(body.run_id, body.rel, body.repeat, body.dict())
        run = runner.get_run(body.run_id)
        prompts.attach_metrics(run["prompt_name"], run["prompt_version"], body.run_id, reviews.metrics(body.run_id))
        try:
            sync = truth.sync_from_review(run["dataset"], body.rel, body.expected_status, body.expected_objects)
            if sync:
                saved["truth_sync"] = sync
        except Exception:
            pass
        return saved
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}/reviews")
def api_list_reviews(run_id: str):
    return reviews.summary(run_id)


class ReviewBatchIn(BaseModel):

    verdict: str
    scope = "unreviewed"
    scope: str


@app.post("/api/runs/{run_id}/reviews/batch")
def api_batch_reviews(run_id: str, body: ReviewBatchIn):
    try:
        result = reviews.batch_save(run_id, body.verdict, body.scope)
        run = runner.get_run(run_id)
        prompts.attach_metrics(run["prompt_name"], run["prompt_version"], run_id, reviews.metrics(run_id))
        return result
    except Exception as e:
        _err(e)


class ReviewReuseIn(BaseModel):

    source_run_id: str
    overwrite = False
    overwrite: bool


@app.post("/api/runs/{run_id}/reviews/reuse")
def api_reuse_reviews(run_id: str, body: ReviewReuseIn):
    try:
        return reviews.reuse_baseline(body.source_run_id, run_id, body.overwrite)
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}/review")
def api_get_review(run_id: str, rel: str, repeat: int = 1):
    return reviews.get_review(run_id, rel, repeat)


class JudgeIn(BaseModel):

    model = None
    model: Optional[str]
    site = None
    site: Optional[str]
    concurrency = 2
    concurrency: int
    coverage_threshold = 1.0
    coverage_threshold: float
    force = False
    force: bool
    profile_name = ""
    profile_name: Optional[str]


@app.post("/api/runs/{run_id}/judge")
def api_judge_run(run_id: str, body: JudgeIn):
    try:
        return judge.start_judge(run_id, body.model, body.concurrency, body.force, body.profile_name or "", body.site, body.coverage_threshold)
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}/judge-job")
def api_judge_job(run_id: str):
    try:
        return judge.get_job(run_id)
    except Exception as e:
        _err(e, 404)


@app.get("/api/judge-jobs")
def api_judge_jobs():
    return {"items": (judge.list_jobs())}


@app.post("/api/runs/{run_id}/judge/stop")
def api_stop_judge(run_id: str):
    judge.stop_judge(run_id)
    return {"ok": True}


@app.delete("/api/runs/{run_id}/judge")
def api_delete_judge(run_id: str):
    try:
        judge.delete_judge(run_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}/judgments")
def api_list_judgments(run_id: str):
    return {"items": (judge.list_judgments(run_id))}


@app.get("/api/runs/{run_id}/judgment")
def api_get_judgment(run_id: str, rel: str, repeat: int = 1):
    return judge.get_judgment(run_id, rel, repeat)


class OptimizeIn(BaseModel):

    prompt_name: str
    version: int
    run_id: str
    model = None
    model: Optional[str]
    site = None
    site: Optional[str]
    max_items = 50
    max_items: int
    profile_name = ""
    profile_name: Optional[str]


@app.post("/api/prompt-ai/optimize")
def api_prompt_optimize(body: OptimizeIn):
    try:
        return prompt_ai.start_optimize(body.prompt_name, body.version, body.run_id, body.model, body.max_items, body.profile_name or "", body.site)
    except Exception as e:
        _err(e)


@app.get("/api/prompt-ai/optimizations/{record_id}")
def api_get_optimization(record_id: str):
    try:
        return prompt_ai.get_optimization_view(record_id)
    except Exception as e:
        _err(e, 404)


@app.delete("/api/prompt-ai/optimizations/{record_id}")
def api_delete_optimization(record_id: str):
    try:
        prompt_ai.delete_optimization(record_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


class CandidateSaveIn(BaseModel):

    note = ""
    note: Optional[str]
    branch = "main"
    branch: Optional[str]


@app.post("/api/prompt-ai/optimizations/{record_id}/save")
def api_save_candidate(record_id: str, body: CandidateSaveIn):
    try:
        return prompt_ai.save_candidate(record_id, body.note or "", body.branch or "main")
    except Exception as e:
        _err(e)


@app.get("/api/prompt-ai/optimizations")
def api_optimizations(prompt_name: str = ''):
    return {"items": (prompt_ai.list_optimizations(prompt_name))}


@app.get("/api/prompt-profiles")
def api_prompt_profiles(profile_type: str = ''):
    return {"items": (prompt_profiles.list_profiles(profile_type))}


class PromptProfileIn(BaseModel):

    name: str
    type: str
    content: str
    description = ""
    description: Optional[str]


@app.put("/api/prompt-profiles/{name}")
def api_save_prompt_profile(name: str, body: PromptProfileIn):
    try:
        if name != body.name:
            raise ValueError("路径名称与模板名称不一致")
        return prompt_profiles.save_profile(body.name, body.type, body.content, body.description or "")
    except Exception as e:
        _err(e)


@app.delete("/api/prompt-profiles/{name}")
def api_delete_prompt_profile(name: str):
    try:
        prompt_profiles.delete_profile(name)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/runs/{run_id}/errors")
def api_error_pool(run_id: str):
    try:
        return workflow.error_pool(run_id)
    except Exception as e:
        _err(e, 404)


class RegressionIn(BaseModel):

    project: str
    name: str
    verdicts = Field(default_factory=(lambda: ["误报", "漏报", "部分正确"]))
    verdicts: List[str]


@app.post("/api/runs/{run_id}/regression-dataset")
def api_regression_dataset(run_id: str, body: RegressionIn):
    try:
        return workflow.create_regression_dataset(run_id, body.project, body.name, body.verdicts)
    except Exception as e:
        _err(e)


class WorkflowIn(BaseModel):

    baseline_run_id: str
    prompt_name = None
    prompt_name: Optional[str]
    source_version = None
    source_version: Optional[int]
    split = None
    split: Optional[str]
    model = None
    model: Optional[str]
    site = None
    site: Optional[str]
    judge_model = None
    judge_model: Optional[str]
    judge_site = None
    judge_site: Optional[str]
    optimizer_model = None
    optimizer_model: Optional[str]
    optimizer_site = None
    optimizer_site: Optional[str]
    judge_profile = ""
    judge_profile: Optional[str]
    optimizer_profile = ""
    optimizer_profile: Optional[str]
    max_rounds = 5
    max_rounds: int
    patience = 2
    patience: int
    min_improvement = 0.005
    min_improvement: float
    min_parse_rate = 0.98
    min_parse_rate: float
    min_protocol_rate = 0.95
    min_protocol_rate: float
    min_accuracy = 0.95
    min_accuracy: float
    concurrency = 2
    concurrency: int
    analysis_concurrency = None
    analysis_concurrency: Optional[int]
    judge_concurrency = None
    judge_concurrency: Optional[int]
    judge_coverage_threshold = 1.0
    judge_coverage_threshold: float
    candidates_per_round = 1
    candidates_per_round: int
    quick_test_size = 0
    quick_test_size: int


@app.get("/api/workflows")
def api_workflows():
    return {"items": (workflow.list_jobs())}


@app.post("/api/workflows")
def api_create_workflow(body: WorkflowIn):
    try:
        return workflow.start_job(body.dict())
    except Exception as e:
        _err(e)


@app.get("/api/workflows/{job_id}")
def api_get_workflow(job_id: str):
    try:
        return workflow.get_job(job_id)
    except Exception as e:
        _err(e, 404)


@app.post("/api/workflows/{job_id}/pause")
def api_pause_workflow(job_id: str):
    try:
        workflow.pause_job(job_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.post("/api/workflows/{job_id}/resume")
def api_resume_workflow(job_id: str):
    try:
        return workflow.resume_job(job_id)
    except Exception as e:
        _err(e)


@app.delete("/api/workflows/{job_id}")
def api_delete_workflow(job_id: str):
    try:
        workflow.delete_job(job_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/extract/fields")
def api_extract_fields(run_id: str):
    """扫描部分结果，把 JSON 扁平化为可用字段路径建议（含 custom 原始结构）"""
    import json as _json
    from .schema import flatten_paths
    fields = set()
    base = os.path.join(runner._run_dir(run_id), "results")
    count = 0
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".json"):
                pass
            else:
                try:
                    with open((os.path.join(dirpath, fn)), "r", encoding="utf-8") as f:
                        d = _json.load(f)
                except Exception:
                        continue

                else:
                    fields.update(flatten_paths(d))
                    count += 1
                    if count >= 20:
                        break

        if count >= 20:
            break
    return {"fields": (sorted(fields))}


class ExtractIn(BaseModel):

    run_id: str
    output_name: str
    mode = "filter"
    mode: str
    logic = "and"
    logic: str
    conditions = Field(default_factory=list)
    conditions: Optional[List[dict]]
    group_field = None
    group_field: Optional[str]
    sources = Field(default_factory=(lambda: ["json"]))
    sources: List[str]


@app.post("/api/extract")
def api_extract(e: ExtractIn):
    try:
        return extractor.extract(e.dict())
    except Exception as ex:
        _err(ex)


@app.get("/api/truth")
def api_truth():
    return {"items": (truth.list_tasks())}


class TruthIn(BaseModel):

    name: str
    kind: str
    labels: List[str]
    dataset: str


@app.post("/api/truth")
def api_create_truth(t: TruthIn):
    try:
        return truth.create_task(t.name, t.kind, t.labels, t.dataset)
    except Exception as e:
        _err(e)


@app.get("/api/truth/for-image")
def api_truth_for_image(dataset: str, rel: str):
    """审核页预填：查某张图在该图片集关联真值任务中的标签。
    注意必须注册在 /api/truth/{task} 之前，否则 for-image 会被当成任务名。"""
    try:
        return truth.labels_for_image(dataset, rel)
    except Exception as e:
        _err(e)


@app.get("/api/truth/{task}")
def api_get_truth(task: str):
    try:
        return truth.get_task(task)
    except Exception as e:
        _err(e, 404)


@app.delete("/api/truth/{task}")
def api_del_truth(task: str):
    try:
        truth.delete_task(task)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/truth/{task}/images")
def api_truth_images(task: str, filter: str = 'all', offset: int = 0, limit: int = 50):
    try:
        return truth.list_images(task, filter, offset, limit)
    except Exception as e:
        _err(e, 404)


class LabelIn(BaseModel):

    rel: str
    labels: List[str]


@app.post("/api/truth/{task}/label")
def api_set_label(task: str, body: LabelIn):
    try:
        return truth.set_labels(task, body.rel, body.labels)
    except Exception as e:
        _err(e)


@app.post("/api/truth/sync-run/{run_id}")
def api_truth_sync_run(run_id: str):
    """把某次运行的全部人工审核批量沉淀为真值（历史数据迁移）。"""
    try:
        return truth.sync_run(run_id)
    except Exception as e:
        _err(e)


@app.get("/api/evals")
def api_evals():
    return {"items": (evaluate.list_evals())}


class EvalIn(BaseModel):

    run_id: str
    truth_task: str
    field = None
    field: Optional[str]
    set_field = None
    set_field: Optional[str]
    name = None
    name: Optional[str]


@app.post("/api/evals")
def api_create_eval(e: EvalIn):
    try:
        return evaluate.run_eval(e.dict())
    except Exception as ex:
        _err(ex)


@app.get("/api/evals/compare")
def api_eval_compare(ids: str):
    return evaluate.compare([i for i in ids.split(",") if i])


@app.get("/api/evals/{eval_id}")
def api_get_eval(eval_id: str):
    try:
        return evaluate.get_eval(eval_id)
    except Exception as e:
        _err(e, 404)


@app.delete("/api/evals/{eval_id}")
def api_del_eval(eval_id: str):
    try:
        evaluate.delete_eval(eval_id)
        return {"ok": True}
    except Exception as e:
        _err(e)


@app.get("/api/file/dataset/{dataset}/{rel:path}")
def api_file_dataset(dataset: str, rel: str):
    try:
        p = datasets.image_path(dataset, rel)
        if not os.path.exists(p):
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
            raise
    except Exception as e:
            _err(e, 404)


@app.get("/api/file/prompt-session/{session_id}/{name}")
def api_file_prompt_session(session_id: str, name: str):
    """提示词生成会话的附件图片"""
    try:
        p = prompt_ai.attachment_file(session_id, name)
        if not os.path.isfile(p):
            _err(FileNotFoundError(name), 404)
        return FileResponse(p)
    except HTTPException:
            raise
    except Exception as e:
            _err(e, 404)


@app.get("/api/file/run/{run_id}/annotated/{rel:path}")
def api_file_annotated(run_id: str, rel: str, repeat: int = 1):
    try:
        p = runner.result_file(run_id, rel, repeat, "annotated")
        if not p:
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
            raise
    except Exception as e:
            _err(e, 404)


@app.get("/api/file/run/{run_id}/image/{rel:path}")
def api_file_run_image(run_id: str, rel: str):
    try:
        p = runner.image_file(run_id, rel)
        if not os.path.isfile(p):
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
            raise
    except Exception as e:
            _err(e, 404)


@app.get("/api/file/truth/{task}/{rel:path}")
def api_file_truth(task: str, rel: str):
    """标注页面显示用：直接返回数据集中的原图"""
    try:
        p = truth.image_path(task, rel)
        if not os.path.exists(p):
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
            raise
    except Exception as e:
            _err(e, 404)


@app.get("/api/file/review/{run_id}/annotated/{rel:path}")
def api_file_review_annotated(run_id: str, rel: str, repeat: int = 1):
    try:
        p = reviews.review_file(run_id, rel, repeat, "annotated")
        if not p:
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
            raise
    except Exception as e:
            _err(e, 404)


@app.exception_handler(Exception)
async def global_exc(request, exc):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=(exc.status_code), content={"detail": (exc.detail)})
    return JSONResponse(status_code=500, content={"detail": (str(exc))})


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
