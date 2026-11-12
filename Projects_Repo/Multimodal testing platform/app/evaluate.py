"""评估模块：运行结果 × 真值任务 → 评估记录

- single（整图分类）：预测取结果某字段（默认 overall_status），
  多次复现按多数投票；输出 准确率/各类别 P-R-F1/混淆矩阵。
- multi（目标集合）：预测取 objects[].name 集合（跨复现按过半出现），
  真值为标签集合；输出 各标签 P-R-F1/微平均/完全匹配率。
每条评估记录保存在 evals/{eval_id}/eval.json，可与提示词版本关联横评。
"""
import json, os, time
from collections import Counter
from typing import Dict, List, Optional
from . import truth, prompts
from .config import subdir, safe_path
from .dircache import FingerprintCache, subfile_fingerprint
from .runner import _load_run, get_result
from .schema import get_field_value

def _eval_dir(eval_id):
    return safe_path(subdir("evals"), eval_id)


_list_cache = FingerprintCache()

def list_evals():
    root = subdir("evals")
    fp = subfile_fingerprint(root, "eval.json")

    def compute():
        out = []
        for eid in sorted((os.listdir(root)), reverse=True):
            p = os.path.join(root, eid, "eval.json")
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        out.append(json.load(f))
                except Exception:
                    continue
        return out

    return _list_cache.get("all", fp, compute)


def get_eval(eval_id):
    with open((os.path.join(_eval_dir(eval_id), "eval.json")), "r", encoding="utf-8") as f:
        return json.load(f)


def delete_eval(eval_id):
    import shutil
    p = _eval_dir(eval_id)
    if os.path.isdir(p):
        shutil.rmtree(p)


def _vote(values):
    vals = [v for v in values if v]
    if not vals:
        return
    return Counter(vals).most_common(1)[0][0]


def _set_vote(sets):
    """跨复现集合投票：出现次数 >= 半数 的元素入最终集合"""
    if not sets:
        return set()
    c = Counter()
    for s in sets:
        c.update(s)

    threshold = max(1, (len(sets) + 1) // 2)
    return {k for k, v in c.items() if v >= threshold}


def run_eval(params):
    """params: {run_id, truth_task, field(默认overall_status),
    set_field(多标签任务的预测集合字段，默认 objects[].name，可填 custom.xxx[].yyy), name(可选)}"""
    run_id = params["run_id"]
    task_id = params["truth_task"]
    field = params.get("field") or "overall_status"
    set_field = params.get("set_field") or "objects[].name"
    run = _load_run(run_id)
    task = truth.get_task(task_id)
    label_map = truth.truth_label_map(task_id)
    if not label_map:
        raise ValueError("真值任务还没有已标注图片")
    details = []
    for rel_img, t_labels in sorted(label_map.items()):
        preds_raw = []
        pred_sets = []
        for r in range(1, run["repeat"] + 1):
            try:
                res = get_result(run_id, rel_img, r)
            except Exception:
                continue
            if not res.get("parse_ok"):
                continue
            if task["kind"] == "single":
                v = get_field_value(res, field)
                preds_raw.append(str(v) if v is not None else None)
            else:
                names = get_field_value(res, set_field) or []
                if not isinstance(names, list):
                    names = [names]
                pred_sets.append({str(n).strip() for n in names if n is not None and str(n).strip()})
        if task["kind"] == "single":
            pred = _vote(preds_raw)
            ok = pred is not None and pred in t_labels
            details.append({'image': rel_img, 'truth': t_labels, 'pred': pred,
                            'pred_all': preds_raw, 'correct': ok})
        else:
            pred_set = _set_vote(pred_sets)
            t_set = set(t_labels)
            details.append({'image': rel_img,
                            'truth': sorted(t_set), 'pred': sorted(pred_set),
                            'pred_all': [sorted(s) for s in pred_sets],
                            'correct': pred_set == t_set,
                            'tp': sorted(pred_set & t_set),
                            'fp': sorted(pred_set - t_set), 'fn': sorted(t_set - pred_set)})
    metrics = _metrics_single(task["labels"], details) if task["kind"] == "single" else _metrics_multi(task["labels"], details)
    eval_id = time.strftime("%Y%m%d-%H%M%S") + f'_{run["prompt_name"]}-V{run["prompt_version"]}'
    base, i = eval_id, 2
    while os.path.exists(_eval_dir(eval_id)):
        eval_id = f"{base}-{i}"
        i += 1
    record = {'id': eval_id,
              'name': params.get("name") or eval_id,
              'created': (time.strftime)("%Y-%m-%d %H:%M:%S"),
              'run_id': run_id, 'truth_task': task_id,
              'field': field,
              'set_field': set_field if (task["kind"] == "multi") else None,
              'kind': task["kind"],
              'prompt_name': run["prompt_name"],
              'prompt_version': run["prompt_version"],
              'model': run["model"], 'dataset': run["dataset"],
              'image_count': len(details), 'metrics': metrics, 'details': details}
    os.makedirs((_eval_dir(eval_id)), exist_ok=True)
    target = os.path.join(_eval_dir(eval_id), "eval.json")
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    os.replace(tmp, target)
    prompts.attach_metrics(run["prompt_name"], run["prompt_version"], run_id, metrics)
    return record


def _metrics_single(labels, details):
    matrix = {t: {p: 0 for p in labels + ["__未识别__"]} for t in labels}
    correct = 0
    for d in details:
        t = d["truth"][0]
        p = d["pred"] if d["pred"] in labels else "__未识别__"
        matrix[t][p] += 1
        if d["correct"]:
            correct += 1
    per_class = {}
    for l in labels:
        tp = matrix[l][l]
        fp = sum((matrix[t][l] for t in labels if t != l))
        fn = sum((matrix[l][p] for p in labels + ["__未识别__"] if p != l))
        per_class[l] = _prf(tp, fp, fn)
    n = len(details)
    return {'accuracy': round(correct / n, 4) if n else 0,
            'per_class': per_class, 'confusion_matrix': matrix,
            'support': {l: sum(matrix[l].values()) for l in labels}}


def _metrics_multi(labels, details):
    per_label = {}
    micro_tp = micro_fp = micro_fn = 0
    exact = 0
    for l in labels:
        tp = sum((1 for d in details if l in d["tp"]))
        fp = sum((1 for d in details if l in d["fp"]))
        fn = sum((1 for d in details if l in d["fn"]))
        per_label[l] = _prf(tp, fp, fn)
        micro_tp += tp
        micro_fp += fp
        micro_fn += fn

    exact = sum((1 for d in details if d["correct"]))
    n = len(details)
    return {'exact_match':round(exact / n, 4) if n else 0, 
     'micro':_prf(micro_tp, micro_fp, micro_fn), 
     'per_label':per_label, 
     'support':{l: sum((1 for d in details if l in d["truth"])) for l in labels}}


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {'precision':round(p, 4), 
     'recall':round(r, 4),  'f1':round(f1, 4), 
     'tp':tp,  'fp':fp,  'fn':fn}


def compare(eval_ids):
    """多条评估记录横评（通常用于同任务不同提示词版本对比）"""
    rows = []
    for eid in eval_ids:
        try:
            e = get_eval(eid)
        except Exception:
            continue
        row = {'id': e["id"], 'name': e["name"], 'kind': e["kind"],
               'prompt': f'{e["prompt_name"]} V{e["prompt_version"]}',
               'prompt_name': e["prompt_name"],
               'prompt_version': e["prompt_version"], 'model': e["model"],
               'created': e["created"], 'image_count': e["image_count"],
               'metrics': e["metrics"]}
        rows.append(row)
    return {"items": rows}
