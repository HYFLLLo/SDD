"""裁判驱动的提示词迭代任务、错误池与回归图片集。"""
import json, os, shutil, threading, time, uuid
from collections import Counter
from typing import Dict, List
from . import datasets, judge, prompt_ai, prompts, reviews, runner, stats
from .config import safe_path, subdir
from .dircache import FingerprintCache, fingerprint
from .prompt_ai import OptimizationError
_lock = threading.RLock()
_active: Dict[(str, Dict)] = {}

def _clamp_int(value, default, minimum, maximum):
    try:
        return max(minimum, min(int(value), maximum))
    except Exception:
        return default


def _clamp_float(value, default, minimum, maximum):
    try:
        return max(minimum, min(float(value), maximum))
    except Exception:
        return default


def _normalize_job_state(state):
    """兼容旧版迭代任务文件，补齐后续版本新增的状态字段。"""
    if not isinstance(state, dict):
        return state
    state.setdefault("phase", "")
    state.setdefault("progress", "")
    state.setdefault("stop_reason", "")
    state.setdefault("error", "")
    state.setdefault("judge_model", "")
    state.setdefault("judge_site", "")
    state.setdefault("judge_profile", "")
    state.setdefault("optimizer_profile", "")
    state.setdefault("optimizer_model", "")
    state.setdefault("optimizer_site", "")
    state.setdefault("optimizer_sub_phase", "")
    state.setdefault("optimizer_started_at", "")
    state.setdefault("rounds", [])
    state.setdefault("best_run_id", state.get("current_run_id") or state.get("baseline_run_id") or "")
    state.setdefault("best_metrics", None)
    state.setdefault("baseline_metrics", None)
    state.setdefault("best_score", None)
    state.setdefault("no_improvement_rounds", 0)
    state.setdefault("source_version", state.get("current_version") or state.get("best_version") or 1)
    state.setdefault("current_version", state.get("source_version") or 1)
    state["max_rounds"] = _clamp_int(state.get("max_rounds"), 5, 1, 20)
    state["patience"] = _clamp_int(state.get("patience"), 2, 1, 10)
    state["min_improvement"] = _clamp_float(state.get("min_improvement"), 0.005, 0.0, 1.0)
    state["concurrency"] = _clamp_int(state.get("concurrency"), 2, 1, 20)
    state["analysis_concurrency"] = _clamp_int(state.get("analysis_concurrency"), state["concurrency"], 1, 20)
    state["judge_concurrency"] = _clamp_int(state.get("judge_concurrency"), state["concurrency"], 1, 20)
    state["judge_coverage_threshold"] = _clamp_float(state.get("judge_coverage_threshold"), 1.0, 0.0, 1.0)
    state["candidates_per_round"] = _clamp_int(state.get("candidates_per_round"), 1, 1, 3)
    state.setdefault("quick_test_size", 0)
    state.setdefault("candidate_execution_mode", "single_candidate")
    state.setdefault("candidate_execution_note", "当前实现每轮只执行 1 个候选；多候选配置已保留，尚未启用并行候选搜索。")
    thresholds = dict(state.get("thresholds") or {})
    thresholds["parse_rate"] = _clamp_float(thresholds.get("parse_rate"), 0.98, 0.0, 1.0)
    thresholds["protocol_valid_rate"] = _clamp_float(thresholds.get("protocol_valid_rate"), 0.95, 0.0, 1.0)
    thresholds["accuracy"] = _clamp_float(thresholds.get("accuracy"), 0.95, 0.0, 1.0)
    thresholds["judge_coverage"] = state["judge_coverage_threshold"]
    state["thresholds"] = thresholds
    return state


class JudgeIncompleteError(ValueError):
    """裁判没有达到迭代所需覆盖率，任务应等待补齐而非标记为程序失败。"""

    def __init__(self, status: str, coverage: float, threshold: float):
        self.judge_status = status or "unknown"
        self.coverage = float(coverage or 0.0)
        self.threshold = float(threshold or 0.0)
        super().__init__("裁判未完成或覆盖率不足：状态={}，覆盖率={:.0%}，要求={:.0%}".format(self.judge_status, self.coverage, self.threshold))


def error_pool(run_id):
    runner.get_run(run_id)
    review_map = {(item.get("image"), int(item.get("repeat", 1))): item for item in reviews.list_reviews(run_id)}
    judgment_map = {(item.get("image"), int(item.get("repeat", 1))): item for item in judge.list_judgments(run_id)}
    keys = sorted(set(review_map) | set(judgment_map))
    items = []
    verdict_counts = Counter()
    module_counts = Counter()
    severity_counts = Counter()
    for image, repeat in keys:
        review = review_map.get((image, repeat), {})
        judgment = judgment_map.get((image, repeat), {})
        verdict = judgment.get("verdict") or review.get("verdict") or "未判断"
        if verdict == "正确":
            pass
        else:
            verdict_counts[verdict] += 1
            if judgment.get("severity"):
                severity_counts[judgment["severity"]] += 1
            modules = []
            for fault in judgment.get("fault_location") or []:
                module = fault.get("module") or "unknown"
                modules.append(module)
                module_counts[module] += 1

            items.append({'image':image, 
             'repeat':repeat,  'verdict':verdict,  'severity':(judgment.get)("severity"), 
             'modules':sorted(set(modules)),  'reason':judgment.get("reason") or review.get("reason") or "", 
             'review':review, 
             'judgment':judgment})
    return {'run_id':run_id,
         'total':len(items),  'items':items,  'verdict_counts':dict(verdict_counts), 
         'module_counts':dict(module_counts),  'severity_counts':dict(severity_counts)}


def create_regression_dataset(run_id, project, name, verdicts=None):
    run = runner.get_run(run_id)
    pool = error_pool(run_id)
    allowed = set(verdicts or ["误报", "漏报", "部分正确"])
    selected = [item for item in pool["items"] if item["verdict"] in allowed]
    if not selected:
        raise ValueError("没有符合条件的错误样本")
    try:
        datasets.get_project(project)
    except ValueError:
        datasets.create_project(project, "由错误池生成的回归图片集")
    ref = datasets.dataset_ref(project, name)
    try:
        existing = datasets.get_dataset(ref)
        if existing.get("count"):
            raise ValueError("目标图片集已存在且不为空，请换一个名称")
    except ValueError as exc:
        if "不存在" not in str(exc):
            raise
    datasets.create_dataset(name, project)
    copied = []
    seen = set()
    for item in selected:
        rel = item["image"]
        if rel in seen:
            continue
        seen.add(rel)
        source = runner.image_file(run_id, rel)
        if not os.path.isfile(source):
            continue
        target = datasets.image_path(ref, rel)
        os.makedirs((os.path.dirname(target)), exist_ok=True)
        shutil.copy2(source, target)
        datasets.set_image_split(ref, rel, "回归集")
        copied.append({'image':rel,  'verdict':item["verdict"],  'severity':(item.get)("severity"), 
         'modules':item.get("modules") or [],  'reason':item.get("reason") or "", 
         'source_run':run_id,  'source_dataset':run["dataset"]})
    datasets.update_dataset_meta(ref, {'description':"从错误池生成的回归图片集", 
     'provenance':{'source_run':run_id, 
      'source_dataset':run["dataset"],  'created':(time.strftime)("%Y-%m-%d %H:%M:%S"), 
      'items':copied}})
    return {'ref':ref, 
     'project':project,  'name':name,  'count':len(copied)}

def _path(job_id):
    return safe_path(subdir("workflows"), f"{job_id}.json")


def _save(state):
    state["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["heartbeat"] = time.time()
    path = _path(state["id"])
    payload = dict(state)
    payload.pop("is_active", None)
    tmp = "{}.tmp.{}".format(path, threading.get_ident())
    try:
        with _lock:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            for attempt in range(5):
                try:
                    os.replace(tmp, path)
                    break
                except PermissionError:
                    if attempt < 4:
                        time.sleep(0.02 * (attempt + 1))
                    else:
                        raise

    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        else:
            raise


def get_job(job_id):
    with _lock:
        path = _path(job_id)
        if not os.path.isfile(path):
            raise ValueError("迭代任务不存在")
        with open(path, "r", encoding="utf-8") as handle:
            state = json.load(handle)
        normalized = _normalize_job_state(dict(state))
        if normalized != state:
            state = normalized
            try:
                _save(state)
            except Exception:
                pass

        entry = _active.get(job_id)
        state["is_active"] = bool(entry) and not entry["stop"].is_set()
    if state.get("status") == "running" and not state["is_active"]:
        state["status"] = "paused"
        state.setdefault("stop_reason", "服务重启后任务已暂停，可继续执行")
        try:
            _save(state)
        except Exception:
            pass
    return state


def delete_job(job_id):
    with _lock:
        entry = _active.get(job_id)
        if entry:
            if not entry["stop"].is_set():
                raise ValueError("任务正在运行，请先暂停再删除")
    path = _path(job_id)
    if not os.path.isfile(path):
        raise ValueError("迭代任务不存在")
    os.remove(path)


_jobs_cache = FingerprintCache()

def list_jobs():
    root = subdir("workflows")
    fp = fingerprint(root)

    def compute():
        items = []
        for filename in sorted((os.listdir(root)), reverse=True):
            if not filename.endswith(".json"):
                pass
            else:
                try:
                    items.append(get_job(filename[:-5]))
                except Exception:
                    continue

        return items

    return _jobs_cache.get("all", fp, compute)


def start_job(params):
    baseline_run = runner.get_run(params["baseline_run_id"])
    prompt_name = params.get("prompt_name") or baseline_run["prompt_name"]
    source_version = int(params.get("source_version") or baseline_run["prompt_version"])
    prompts.get_version(prompt_name, source_version)
    if baseline_run["prompt_name"] != prompt_name:
        raise ValueError("基线运行与提示词名称不一致")
    job_id = time.strftime("%Y%m%d-%H%M%S") + "_" + uuid.uuid4().hex[:8]
    state = {'id':job_id, 
     'status':"running",  'phase':"准备",  'prompt_name':prompt_name, 
     'source_version':source_version,  'current_version':source_version, 
     'baseline_run_id':baseline_run["id"],  'current_run_id':baseline_run["id"], 
     'dataset':baseline_run["dataset"],  'split':params.get("split") if (params.get("split") is not None) else (baseline_run.get("dataset_split")), 
     'model':params.get("model") or baseline_run["model"], 
     'site':params.get("site") or baseline_run.get("site") or "", 
     'judge_model':params.get("judge_model") or "", 
     'judge_site':params.get("judge_site") or "", 
     'optimizer_model':params.get("optimizer_model") or "", 
     'optimizer_site':params.get("optimizer_site") or "", 
     'judge_profile':params.get("judge_profile") or "", 
     'optimizer_profile':params.get("optimizer_profile") or "", 
     'max_rounds':max(1, min(int(params.get("max_rounds") or 5), 20)), 
     'patience':max(1, min(int(params.get("patience") or 2), 10)), 
     'min_improvement':max(0.0, float(params.get("min_improvement") or 0.005)), 
     'thresholds':{'parse_rate':float(params.get("min_parse_rate") or 0.98), 
      'protocol_valid_rate':float(params.get("min_protocol_rate") or 0.95), 
      'accuracy':float(params.get("min_accuracy") or 0.95)}, 
     'concurrency':max(1, min(int(params.get("concurrency") or baseline_run.get("concurrency") or 2), 20)), 
     'analysis_concurrency':max(1, min(int(params.get("analysis_concurrency") or params.get("concurrency") or baseline_run.get("concurrency") or 2), 20)), 
     'judge_concurrency':max(1, min(int(params.get("judge_concurrency") or params.get("concurrency") or 2), 20)), 
     'judge_coverage_threshold':max(0.0, min(float(params.get("judge_coverage_threshold") if params.get("judge_coverage_threshold") is not None else 1.0), 1.0)), 
     'candidates_per_round':max(1, min(int(params.get("candidates_per_round") or 1), 3)), 
     'quick_test_size':max(0, min(int(params.get("quick_test_size") or 0), 50)), 
     'candidate_execution_mode':"single_candidate", 
     'candidate_execution_note':"当前实现每轮只执行 1 个候选；如配置大于 1，将在任务状态中保留请求值但不伪造多候选结果。", 
     'rounds':[],  'best_version':source_version, 
     'best_run_id':baseline_run["id"],  'best_score':None,  'best_metrics':None, 
     'baseline_metrics':None,  'no_improvement_rounds':0, 
     'created':(time.strftime)("%Y-%m-%d %H:%M:%S")}
    _save(state)
    _launch(state)
    return get_job(job_id)


def pause_job(job_id):
    with _lock:
        active = _active.get(job_id)
        if active:
            active["stop"].set()
    state = get_job(job_id)
    state["status"] = "paused"
    state["stop_reason"] = "用户暂停"
    try:
        _save(state)
    except Exception:
        pass
    else:
        current_run = state.get("current_run_id")
        if current_run:
            runner.stop_run(current_run)
            judge.stop_judge(current_run)


def resume_job(job_id):
    state = get_job(job_id)
    with _lock:
        active = _active.get(job_id)
        if active:
            if not active["stop"].is_set():
                raise ValueError("迭代任务正在执行")
        old_thread = active.get("thread") if active else None
    if old_thread is not None and old_thread.is_alive():
        old_thread.join(timeout=15.0)
        if old_thread.is_alive():
            raise ValueError("上一次迭代任务仍在收尾，请稍后再试")
    if state.get("status") in {'stable', 'done'}:
        raise ValueError("迭代任务已经结束")
    state["status"] = "running"
    state["stop_reason"] = ""
    state["error"] = ""
    _save(state)
    _launch(state)
    return get_job(job_id)

def _launch(state):
    stop = threading.Event()
    thread = threading.Thread(target=_execute, args=(state["id"], stop), daemon=True)
    with _lock:
        _active[state["id"]] = {'stop':stop, 
         'thread':thread}
    thread.start()


def _wait_run(run_id, stop, state=None):
    run = runner.get_run(run_id)
    if run.get("status") != "done" or run.get("done", 0) + run.get("failed", 0) < run.get("total", 0):
        if not run.get("is_active"):
            runner.start_run(run_id)
    while True:
        run = runner.get_run(run_id)
        if stop.is_set():
            runner.stop_run(run_id)
        if state is not None:
            total = run.get("total", 0)
            done = run.get("done", 0) + run.get("failed", 0)
            state["progress"] = f"运行进度 {done}/{total}" if total else "运行准备中"
            try:
                _save(state)
            except Exception:
                pass
        if not run.get("is_active") and run.get("status") != "running":
            if state is not None:
                state["progress"] = ""
                try:
                    _save(state)
                except Exception:
                    pass
            return run
        time.sleep(0.5)


def _wait_judge(run_id, model, concurrency, stop, profile_name='', site='', state=None, coverage_threshold=1.0):
    job = judge.get_job(run_id)
    if not job.get("is_active"):
        if job.get("status") not in {'done'}:
            judge.start_judge(run_id, (model or None), concurrency, force=False, profile_name=profile_name,
              site=(site or None),
              coverage_threshold=coverage_threshold)
    while True:
        job = judge.get_job(run_id)
        if stop.is_set():
            judge.stop_judge(run_id)
        if state is not None:
            total = job.get("total", 0)
            completed = job.get("done", 0) + job.get("failed", 0)
            coverage = float(job.get("coverage") or 0.0)
            state["judge_job"] = {'run_id':run_id, 
             'status':(job.get)("status"),  'coverage':coverage, 
             'total':total,  'done':(job.get)("done", 0),  'failed':(job.get)("failed", 0), 
             'active_workers':(job.get)("active_workers", 0),  'heartbeat':(job.get)("heartbeat")}
            state["progress"] = f"裁判进度 {completed}/{total} · 覆盖率 {coverage:.0%}" if total else "裁判准备中"
            try:
                _save(state)
            except Exception:
                pass
        if not job.get("is_active"):
            if job.get("status") not in {'running'}:
                coverage = float(job.get("coverage") or 0.0)
                if job.get("status") == "done" and coverage >= coverage_threshold:
                    if state is not None:
                        state["progress"] = ""
                        try:
                            _save(state)
                        except Exception:
                            pass
                    return job
                if stop.is_set() or job.get("status") == "paused":
                    if state is not None:
                        state["status"] = "paused"
                        state["stop_reason"] = "裁判任务已暂停，可继续执行"
                        try:
                            _save(state)
                        except Exception:
                            pass
                    return job
                raise JudgeIncompleteError(job.get("status"), coverage, coverage_threshold)
        time.sleep(0.5)


def _quality(run_id):
    stability = stats.run_stability(run_id)
    review_metrics = reviews.metrics(run_id)
    judgments = judge.list_judgments(run_id)
    job = judge.get_job(run_id)
    high_errors = sum((1 for item in judgments if item.get("severity") == "高" and item.get("verdict") != "正确"))
    verdict_counts = Counter((item.get("verdict") for item in judgments if item.get("verdict")))
    deterministic_counts = Counter((item.get("deterministic_verdict") for item in judgments if item.get("deterministic_verdict")))
    disagreement = sum((1 for item in judgments if item.get("llm_verdict") and item.get("deterministic_verdict") and item.get("llm_verdict") != item.get("deterministic_verdict")))
    accuracy = review_metrics.get("accuracy")
    protocol_rate = stability.get("protocol_valid_rate")
    parse_rate = stability.get("parse_rate")
    uncertain_count = review_metrics.get("uncertain", 0)
    reviewed_total = review_metrics.get("reviewed", 0) or 1
    uncertain_ratio = round(uncertain_count / reviewed_total, 4)
    score = accuracy if accuracy is not None else protocol_rate if protocol_rate is not None else parse_rate
    eligible = int(job.get("eligible") or 0)
    coverage = float(job.get("coverage") if job.get("coverage") is not None else len(judgments) / eligible if eligible else 0.0)
    box_tp = 0
    box_fp = 0
    box_fn = 0
    for item in judgments:
        dc = item.get("deterministic_comparison") or {}
        matches = dc.get("matches") or []
        box_tp += len(matches)
        box_fp += int(dc.get("unmatched_predicted") or 0)
        box_fn += int(dc.get("unmatched_expected") or 0)

    box_precision = round(box_tp / (box_tp + box_fp), 4) if box_tp + box_fp > 0 else None
    box_recall = round(box_tp / (box_tp + box_fn), 4) if box_tp + box_fn > 0 else None
    box_f1 = round(2 * box_precision * box_recall / (box_precision + box_recall), 4) if box_precision is not None and box_recall is not None and box_precision + box_recall > 0 else None
    root_cause_counts = {}
    for item in judgments:
        rc = item.get("root_cause") or "无法确定"
        root_cause_counts[rc] = root_cause_counts.get(rc, 0) + 1
    return {'accuracy':accuracy, 
     'reviewed':(review_metrics.get)("reviewed", 0),  'error_rate':(review_metrics.get)("error_rate"), 
     'uncertain_count':uncertain_count, 
     'uncertain_ratio':uncertain_ratio,  'parse_rate':parse_rate, 
     'protocol_valid_rate':protocol_rate,  'status_agree_avg':(stability.get)("status_agree_avg"), 
     'high_severity_errors':high_errors, 
     'quality_score':score,  'judge_coverage':round(coverage, 4), 
     'judge_eligible':eligible,  'judge_count':len(judgments), 
     'verdict_counts':dict(verdict_counts),  'deterministic_verdict_counts':dict(deterministic_counts), 
     'judge_llm_disagreement':disagreement, 
     'box_tp':box_tp, 
     'box_fp':box_fp,  'box_fn':box_fn,  'box_precision':box_precision, 
     'box_recall':box_recall,  'box_f1':box_f1,  'root_cause_counts':dict(root_cause_counts)}

def _judge_module_stats(run_id):
    """统计裁判报告中各 fault_location 模块出现次数。"""
    counts = {}
    for item in judge.list_judgments(run_id):
        for fault in item.get("fault_location") or []:
            module = fault.get("module") or "unknown"
            counts[module] = counts.get(module, 0) + 1

    return counts


def _is_model_dominant(run_id):
    """判断裁判是否主要指向 model 模块。返回 (is_dominant, detail_str)。"""
    counts = _judge_module_stats(run_id)
    if not counts:
        return (False, '')
    total = sum(counts.values())
    model_count = counts.get("model", 0)
    if total >= 5 and model_count / total >= 0.7:
        parts = ["{}({})".format(m, c) for m, c in sorted((counts.items()), key=(lambda x: -x[1]))]
        return (
         True, "、".join(parts))
    return (False, '')


def _check_root_cause_ceiling(rounds):
    """Check if recent rounds consistently point to model capability ceiling.
    Returns (is_ceiling, reason_str).
    Signal: last 2 rounds both have root_cause majority = model capability.
    """
    if len(rounds) < 2:
        return (False, '')
    recent = rounds[-2:]
    model_dominant_count = 0
    for r in recent:
        metrics = r.get("metrics") or {}
        rc_counts = metrics.get("root_cause_counts") or {}
        total = sum(rc_counts.values())
        if total == 0:
            pass
        else:
            model_count = rc_counts.get("模型能力不足", 0)
            if model_count / total >= 0.5:
                model_dominant_count += 1

    if model_dominant_count >= 2:
        return (True, '近 2 轮根因分析均指向模型能力不足，提示词已达天花板，建议换模型或微调')
    return (False, '')


def _meets_thresholds(metrics, thresholds):
    return metrics.get("accuracy") is not None and metrics["accuracy"] >= thresholds["accuracy"] and (metrics.get("parse_rate") or 0) >= thresholds["parse_rate"] and (metrics.get("protocol_valid_rate") or 0) >= thresholds["protocol_valid_rate"] and metrics.get("judge_coverage", 0) >= thresholds.get("judge_coverage", 1.0) and metrics.get("high_severity_errors", 0) == 0 and metrics.get("uncertain_ratio", 0) <= 0.3


def _compare_quality(previous, candidate, state):
    """候选门禁：高严重度不回归，准确率优先，协议/解析/覆盖率不得下降。"""
    delta = {}
    for key in ('accuracy', 'parse_rate', 'protocol_valid_rate', 'judge_coverage',
                'high_severity_errors'):
        old, new = previous.get(key), candidate.get(key)
        delta[key] = None if (old is None) or (new is None) else (round(new - old, 4))

    reasons = []
    if candidate.get("judge_coverage", 0) < state["thresholds"].get("judge_coverage", 1.0):
        reasons.append("裁判覆盖率不足")
    if candidate.get("high_severity_errors", 0) > previous.get("high_severity_errors", 0):
        reasons.append("高严重度错误增加")
    if candidate.get("uncertain_ratio", 0) > 0.3:
        reasons.append("无法判断占比过高（{:.0%}），accuracy 可能虚高".format(candidate["uncertain_ratio"]))
    for key, label in (('parse_rate', '解析率'), ('protocol_valid_rate', '协议合规率')):
        old, new = previous.get(key), candidate.get(key)
        if old is not None and new is not None and new + 0.01 < old:
            reasons.append(label + "明显下降")
    old_acc, new_acc = previous.get("accuracy"), candidate.get("accuracy")
    improved = (new_acc is not None) and ((old_acc is None) or (new_acc >= old_acc + state["min_improvement"]))
    high_sev_improved = candidate.get("high_severity_errors", 0) < previous.get("high_severity_errors", 0)
    if not improved and not high_sev_improved:
        reasons.append("准确率没有达到最小提升幅度且高严重度错误未减少")
    return (not reasons, delta, "；".join(reasons) if reasons else "准确率提升且通过回归门禁")

def _finish_pending_round(state, metrics):
    pending = state.get("pending_round")
    if not pending or pending.get("run_id") != state.get("current_run_id"):
        return False
    previous = state.get("best_metrics") or state.get("baseline_metrics") or metrics
    (accepted, delta, reason) = _compare_quality(previous, metrics, state)
    if accepted:
        state["best_score"] = metrics.get("quality_score")
        state["best_version"] = pending["version"]
        state["best_run_id"] = pending["run_id"]
        state["best_metrics"] = metrics
        state["no_improvement_rounds"] = 0
        prompts.mark_version_status(state["prompt_name"], pending["version"], "accepted")
    else:
        state["no_improvement_rounds"] += 1
        state["current_version"] = state.get("best_version", state["source_version"])
        state["current_run_id"] = state.get("best_run_id", state["baseline_run_id"])
        prompts.mark_version_status(state["prompt_name"], pending["version"], "rejected")
    state["rounds"].append({'round':(len(state["rounds"])) + 1, 
     'version':pending["version"],  'run_id':pending["run_id"], 
     'optimization_id':pending["optimization_id"],  'source_version':(pending.get)("source_version", state.get("best_version")), 
     'source_run_id':(pending.get)("source_run_id", state.get("best_run_id")), 
     'metrics':metrics, 
     'delta':delta,  'accepted':accepted,  'rejected':not accepted, 
     'reason':reason})
    state.pop("pending_round", None)
    if _meets_thresholds(metrics, state["thresholds"]):
        if accepted:
            state["status"] = "stable"
            state["stop_reason"] = "达到稳定阈值且无高严重度回归"
            return True
    (is_ceiling, ceiling_reason) = _check_root_cause_ceiling(state.get("rounds", []))
    if is_ceiling:
        state["status"] = "stable"
        state["stop_reason"] = ceiling_reason
        return True
    if state["no_improvement_rounds"] >= state["patience"]:
        state["status"] = "stable"
        state["stop_reason"] = f'连续 {state["patience"]} 轮未通过质量门禁'
        return True
    return False
    return False


def _execute(job_id, stop):
    try:
        try:
            state = get_job(job_id)
            while len(state["rounds"]) < state["max_rounds"]:
                if stop.is_set():
                    state["status"] = "paused"
                    state["stop_reason"] = "用户暂停"
                    _save(state)
                    return
                current_run = state["current_run_id"]
                pending = state.get("pending_round")
                if pending and pending.get("run_id") == current_run:
                    current_run_state = runner.get_run(current_run)
                    processed = current_run_state.get("done", 0) + current_run_state.get("failed", 0)
                    if current_run_state.get("status") != "done" or processed < current_run_state.get("total", 0):
                        state["phase"] = "继续候选版本运行"
                        _save(state)
                        completed_run = _wait_run(current_run, stop, state=state)
                        if stop.is_set():
                            continue
                        if completed_run.get("done", 0) == 0:
                            raise ValueError("候选版本没有产生有效结果")
                    if not reviews.list_reviews(current_run):
                        state["phase"] = "复用人工基线"
                        _save(state)
                        reuse = reviews.reuse_baseline(state["baseline_run_id"], current_run, overwrite=False)
                        if reuse["copied"] == 0 and not reviews.list_reviews(current_run):
                            state["status"] = "waiting_for_review"
                            state["stop_reason"] = "候选运行与基线没有重合样本，请人工审核候选运行后继续"
                            _save(state)
                            return
                state["phase"] = "补齐当前版本裁判"
                _save(state)
                if not reviews.list_reviews(current_run):
                    state["status"] = "waiting_for_review"
                    state["stop_reason"] = "当前运行没有人工审核；请先审核，或从已有基线复用审核"
                    _save(state)
                    return
                _wait_judge(
                    current_run,
                    state["judge_model"],
                    state["judge_concurrency"],
                    stop,
                    state.get("judge_profile") or "",
                    state.get("judge_site") or "",
                    state=state,
                    coverage_threshold=state["judge_coverage_threshold"],
                )
                if stop.is_set():
                    continue
                current_job = judge.get_job(current_run)
                current_coverage = float(current_job.get("coverage") or 0.0)
                if current_job.get("status") == "paused":
                    state["status"] = "paused"
                    state["stop_reason"] = "裁判任务已暂停，可继续执行"
                    _save(state)
                    return
                if current_job.get("status") != "done" or current_coverage < state["judge_coverage_threshold"]:
                    state["status"] = "waiting_for_judge"
                    state["stop_reason"] = "裁判未完成或覆盖率不足，未进入优化"
                    _save(state)
                    return
                if not state.get("rounds"):
                    (is_model_dom, model_detail) = _is_model_dominant(current_run)
                    if is_model_dom:
                        state["status"] = "stable"
                        state["stop_reason"] = "裁判报告主要指向模型能力不足（{}）。提示词可优化空间有限，建议更换更强的分析模型后重试。".format(model_detail)
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                current_metrics = _quality(current_run)
                state["thresholds"]["judge_coverage"] = state["judge_coverage_threshold"]
                prompts.attach_metrics(state["prompt_name"], state["current_version"], current_run, current_metrics)
                if state.get("pending_round"):
                    if _finish_pending_round(state, current_metrics):
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                    _save(state)
                    if len(state["rounds"]) >= state["max_rounds"]:
                        state["status"] = "done"
                        state["stop_reason"] = "达到最大迭代轮数"
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                else:
                    if state["best_score"] is None and current_metrics.get("quality_score") is not None:
                        state["best_score"] = current_metrics["quality_score"]
                        state["best_version"] = state["current_version"]
                        state["best_run_id"] = current_run
                        state["best_metrics"] = current_metrics
                        state["baseline_metrics"] = current_metrics
                        _save(state)
                state["thresholds"]["judge_coverage"] = state["judge_coverage_threshold"]
                if not state.get("rounds") and _meets_thresholds(current_metrics, state["thresholds"]):
                    state["status"] = "stable"
                    state["stop_reason"] = "当前版本已达到稳定阈值且无高严重度回归"
                    state["phase"] = "完成"
                    state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    _save(state)
                    return
                state["phase"] = "生成并保存候选版本"
                _save(state)
                if stop.is_set():
                    continue
                state["optimizer_started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                state["optimizer_sub_phase"] = "正在调用优化器模型 {}…".format(
                    state.get("optimizer_model") or state["model"]
                )
                _save(state)
                candidate = prompt_ai.optimize(
                    state["prompt_name"],
                    state["current_version"],
                    current_run,
                    state.get("optimizer_model") or state["model"],
                    50,
                    state.get("optimizer_profile") or "",
                    site=state.get("optimizer_site") or state.get("site") or None,
                    trajectory=state.get("rounds", []),
                )
                state["optimizer_sub_phase"] = ""
                state["optimizer_started_at"] = ""
                _save(state)
                version = prompt_ai.save_candidate(candidate["id"], branch=f"auto/{job_id}")
                state["phase"] = "运行候选版本"
                state["candidate_record_id"] = candidate["id"]
                source_version = state["current_version"]
                source_run_id = state["current_run_id"]
                _save(state)
                run = runner.create_run({
                    "dataset": state["dataset"],
                    "split": state.get("split"),
                    "prompt_name": state["prompt_name"],
                    "prompt_version": version["version"],
                    "model": state["model"],
                    "repeat": 1,
                    "concurrency": state["analysis_concurrency"],
                    "site": state.get("site") or "",
                })
                state["current_run_id"] = run["id"]
                state["current_version"] = version["version"]
                state["pending_round"] = {
                    "version": version["version"],
                    "run_id": run["id"],
                    "optimization_id": candidate["id"],
                    "source_version": source_version,
                    "source_run_id": source_run_id,
                    "candidate_index": 1,
                    "candidate_count_requested": state.get("candidates_per_round", 1),
                    "candidate_count_executed": 1,
                    "candidate_execution_note": "当前版本每轮实际执行 1 个候选；多候选配置已保留，尚未启用并行候选搜索",
                }
                _save(state)
                quick_test_size = state.get("quick_test_size") or 0
                if quick_test_size > 0:
                    qt_run = runner.get_run(run["id"])
                    if not qt_run.get("is_active") and qt_run.get("status") != "running":
                        runner.start_run(run["id"])
                    qt_ready = False
                    while not stop.is_set():
                        qt_run = runner.get_run(run["id"])
                        qt_done = qt_run.get("done", 0) + qt_run.get("failed", 0)
                        qt_total = qt_run.get("total", 0)
                        state["progress"] = "快测进度 {}/{}".format(qt_done, qt_total)
                        try:
                            _save(state)
                        except Exception:
                            pass
                        if qt_done >= quick_test_size:
                            qt_ready = True
                            break
                        if not qt_run.get("is_active") and qt_run.get("status") != "running":
                            qt_ready = True
                            break
                        time.sleep(0.5)
                    if qt_ready and not stop.is_set():
                        qt_stability = stats.run_stability(run["id"])
                        qt_parse_rate = qt_stability.get("parse_rate")
                        if qt_parse_rate is not None and qt_parse_rate < 0.3:
                            runner.stop_run(run["id"])
                            state["phase"] = "快测拒绝：解析率 {:.0%}，跳过全量运行".format(qt_parse_rate)
                            _save(state)
                            reject_metrics = _quality(run["id"])
                            prompts.attach_metrics(state["prompt_name"], version["version"], run["id"], reject_metrics)
                            state["pending_round"] = {
                                "version": version["version"],
                                "run_id": run["id"],
                                "optimization_id": candidate["id"],
                                "source_version": source_version,
                                "source_run_id": source_run_id,
                                "candidate_index": 1,
                                "candidate_count_requested": state.get("candidates_per_round", 1),
                                "candidate_count_executed": 1,
                                "candidate_execution_note": "quick test rejected",
                            }
                            _finish_pending_round(state, reject_metrics)
                            _save(state)
                            if state.get("status") in ("stable", "done"):
                                state["phase"] = "完成"
                                state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                                _save(state)
                                return
                            continue
                completed_run = _wait_run(run["id"], stop, state=state)
                if stop.is_set():
                    continue
                if completed_run.get("done", 0) == 0:
                    raise ValueError("候选版本没有产生有效结果")
                state["phase"] = "复用人工基线"
                _save(state)
                reuse = reviews.reuse_baseline(state["baseline_run_id"], run["id"], overwrite=False)
                if reuse["copied"] == 0 and not reviews.list_reviews(run["id"]):
                    state["status"] = "waiting_for_review"
                    state["stop_reason"] = "候选运行与基线没有重合样本，请人工审核候选运行后继续"
                    _save(state)
                    return
                candidate_stability = stats.run_stability(run["id"])
                candidate_parse_rate = candidate_stability.get("parse_rate")
                baseline_metrics = state.get("baseline_metrics") or {}
                baseline_parse_rate = baseline_metrics.get("parse_rate")
                quick_reject = False
                if candidate_parse_rate is not None and candidate_parse_rate < 0.3:
                    quick_reject = True
                    quick_reason = "候选版本解析率仅为 {:.0%}，跳过裁判直接拒绝".format(candidate_parse_rate)
                elif candidate_parse_rate is not None and baseline_parse_rate is not None and candidate_parse_rate < baseline_parse_rate * 0.5:
                    quick_reject = True
                    quick_reason = "候选版本解析率仅为基线的 {:.0%}，跳过裁判直接拒绝".format(
                        candidate_parse_rate / baseline_parse_rate
                    )
                if quick_reject:
                    state["phase"] = quick_reason
                    _save(state)
                    reject_metrics = _quality(run["id"])
                    prompts.attach_metrics(state["prompt_name"], version["version"], run["id"], reject_metrics)
                    state["pending_round"] = {
                        "version": version["version"],
                        "run_id": run["id"],
                        "optimization_id": candidate["id"],
                        "source_version": source_version,
                        "source_run_id": source_run_id,
                        "candidate_index": 1,
                        "candidate_count_requested": state.get("candidates_per_round", 1),
                        "candidate_count_executed": 1,
                        "candidate_execution_note": "quick rejected",
                    }
                    _finish_pending_round(state, reject_metrics)
                    _save(state)
                    if state.get("status") in ("stable", "done"):
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                    continue
                state["phase"] = "裁判候选版本"
                _save(state)
                _wait_judge(
                    run["id"],
                    state["judge_model"],
                    state["judge_concurrency"],
                    stop,
                    state.get("judge_profile") or "",
                    state.get("judge_site") or "",
                    state=state,
                    coverage_threshold=state["judge_coverage_threshold"],
                )
                if stop.is_set():
                    continue
                metrics = _quality(run["id"])
                prompts.attach_metrics(state["prompt_name"], version["version"], run["id"], metrics)
                score = metrics.get("quality_score")
                if score is not None and score == 0.0 and len(state.get("rounds", [])) >= 1:
                    state["status"] = "stable"
                    state["stop_reason"] = "候选版本质量评分为 0，优化方向可能有问题。建议：1) 检查裁判归因是否准确；2) 手动优化提示词后重试；3) 更换分析模型或裁判模型。"
                    state["phase"] = "完成"
                    state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    _save(state)
                    return
                finished = _finish_pending_round(state, metrics)
                _save(state)
                if finished:
                    break
            else:
                state["status"] = "done"
                state["stop_reason"] = "达到最大迭代轮数"
            state["phase"] = "完成"
            state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save(state)
        except JudgeIncompleteError as exc:
            try:
                state = get_job(job_id)
                state["status"] = "waiting_for_judge"
                state["stop_reason"] = str(exc)
                state["phase"] = "等待裁判补齐"
                state["error"] = ""
                _save(state)
            except Exception:
                pass
        except OptimizationError as exc:
            try:
                state = get_job(job_id)
                state["status"] = "stable"
                state["stop_reason"] = str(exc)
                state["phase"] = "完成"
                state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                state["optimizer_sub_phase"] = ""
                state["optimizer_started_at"] = ""
                _save(state)
            except Exception:
                pass
        except Exception as exc:
            try:
                state = get_job(job_id)
                state["status"] = "failed"
                err_msg = str(exc)
                if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
                    err_msg = "优化器模型调用超时。建议：1) 在配置页增大 optimizer_timeout（当前 {} 秒）；2) 更换更快的优化器模型；3) 减少 optimizer_max_tokens。".format(
                        state.get("optimizer_timeout", 600)
                    )
                state["error"] = err_msg
                state["phase"] = "失败"
                state["optimizer_sub_phase"] = ""
                state["optimizer_started_at"] = ""
                _save(state)
            except Exception:
                pass
    finally:
        with _lock:
            current = _active.get(job_id)
            if current is not None and current.get("stop") is stop:
                _active.pop(job_id, None)
