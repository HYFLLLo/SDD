"""真值任务：按钮式标注，按文件夹归档

truth/{task}/
  task.json          {name, kind: single|multi, labels: [...], dataset, created}
  {label}/{图片}      标注结果（复制原图归档；single=只属于一个文件夹，multi=可属多个）
标注进度 = 已归档图片数 / 数据集图片数，支持随时续标。

与人工审核互通：审核时填写的期望状态/期望目标框可自动沉淀为真值
（每个图片集一个"审核沉淀"主任务，auto_sync=True）；真值任务里手动
标注/清除的图片不会被自动沉淀覆盖，两边信息互通。
"""
import json, os, re, shutil, time
from typing import Dict, List, Optional
from . import datasets
from .config import subdir, safe_path
from .dircache import FingerprintCache, fingerprint
_WIN_RESERVED = {
 "CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
_RESERVED_SEGMENTS = {
 "images", "task.json", "task"}

def _slug(name):
    """把任务名/标签名清洗成安全的单层目录名（避免 .. 越界、保留名与超长路径）。"""
    s = re.sub('[\\\\/:*?"<>|\\x00-\\x1f]', "_", str(name).strip())
    s = s.strip().strip(".")
    if not s:
        raise ValueError("名称非法")
    if s.upper() in _WIN_RESERVED or s.lower() in _RESERVED_SEGMENTS:
        s = "_" + s
    return s[:60]


def _task_dir(task):
    return safe_path(subdir("truth"), task)


def _task_json(task):
    return os.path.join(_task_dir(task), "task.json")


def list_tasks():
    root = subdir("truth")
    out = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name, "task.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                t = json.load(f)
            t["progress"] = get_progress(name)
            t["source_stats"] = _source_stats(t)
            out.append(t)
    return out


def create_task(name, kind, labels, dataset):
    if kind not in ('single', 'multi'):
        raise ValueError("kind 必须是 single 或 multi")
    labels = [_slug(l) for l in labels if l.strip()]
    return _create_task(name, kind, labels, dataset, min_labels=2)


def _create_task(name, kind, labels, dataset, min_labels=2, auto_sync=False, primary_for=""):
    if len(labels) < min_labels:
        raise ValueError(f"至少需要 {min_labels} 个标签")
    if len(set(labels)) != len(labels):
        raise ValueError("标签不能重复")
    if not datasets.dataset_exists(dataset):
        raise ValueError("图片集不存在")
    source_images = datasets.scan_images(dataset)
    if not source_images:
        raise ValueError("图片集为空")
    slug = _slug(name)
    if os.path.exists(_task_json(slug)):
        raise ValueError("同名任务已存在")
    task = {'id':slug, 
     'name':name,  'kind':kind,  'labels':labels,  'dataset':dataset, 
     'images_snapshot':[{'rel':item["rel"],  'name':item["name"]} for item in source_images], 
     'auto_sync':bool(auto_sync), 
     'primary_for':primary_for or "",  'sources':{},  'created':(time.strftime)("%Y-%m-%d %H:%M:%S")}
    try:
        os.makedirs((_task_dir(slug)), exist_ok=True)
        for label in labels:
            os.makedirs((os.path.join(_task_dir(slug), label)), exist_ok=True)

        for item in source_images:
            source = datasets.image_path(dataset, item["rel"])
            target = safe_path(_task_dir(slug), "images", item["rel"])
            os.makedirs((os.path.dirname(target)), exist_ok=True)
            shutil.copy2(source, target)

        tmp = _task_json(slug) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _task_json(slug))
    except Exception:
        shutil.rmtree((_task_dir(slug)), ignore_errors=True)
        raise
    return task


def get_task(task):
    with open((_task_json(task)), "r", encoding="utf-8") as f:
        t = json.load(f)
    t["progress"] = get_progress(task)
    t["source_stats"] = _source_stats(t)
    return t


def _source_stats(task_meta):
    """标注来源统计：manual=真值页手动标注，review=审核自动沉淀。"""
    stats = {'manual':0, 
     'review':0}
    for src in (task_meta.get("sources") or {}).values():
        if src in stats:
            stats[src] += 1
    return stats


def _save_task_meta(task, meta):
    tmp = _task_json(task) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _task_json(task))


def delete_task(task):
    p = _task_dir(task)
    if os.path.isdir(p):
        shutil.rmtree(p)


_labeled_cache = FingerprintCache()

def _labeled_map(task):
    """{图片 rel: [label,...]}，按当前文件夹归档状态扫描。

    遍历全部标签文件夹开销大，按任务目录指纹缓存。注意必须包含
    task.json：归档文件是 copy2 保留源 mtime 复制的，跨标签移动时
    文件数和最大 mtime 都可能不变，只有 task.json（记录 sources，
    每次 set_labels 都重写）的 mtime 能可靠反映归档变化。
    """
    fp = fingerprint((_task_dir(task)), suffix=None, recursive=True)

    def compute():
        t = get_task_meta(task)
        m = {}
        for label in t["labels"]:
            ldir = os.path.join(_task_dir(task), label)
            for dirpath, _, files in os.walk(ldir):
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in datasets.IMG_EXTS:
                        rel = os.path.relpath(os.path.join(dirpath, fn), ldir).replace("\\", "/")
                        m.setdefault(rel, []).append(label)
        return m

    return _labeled_cache.get(task, fp, compute)


def get_task_meta(task):
    with open((_task_json(task)), "r", encoding="utf-8") as f:
        return json.load(f)


def get_progress(task):
    t = get_task_meta(task)
    total = len(_source_images(t))
    labeled = len(_labeled_map(task))
    return {'total':total, 
     'labeled':labeled,  'percent':round(labeled / total * 100, 1) if total else 0}


def list_images(task, filter="all", offset=0, limit=50):
    """列出任务图片及标注状态。filter: all/unlabeled/labeled"""
    t = get_task_meta(task)
    lm = _labeled_map(task)
    sources = t.get("sources") or {}
    items = []
    for img in _source_images(t):
        labels = lm.get(img["rel"], [])
        status = "labeled" if labels else "unlabeled"
        if filter != "all" and status != filter:
            continue
        items.append({'rel':img["rel"],  'name':img["name"],  'labels':labels, 
         'status':status,  'source':sources.get(img["rel"]) or ""})
    total = len(items)
    return {'total':total,  'items':items[offset:offset + limit]}


def set_labels(task, rel, labels, source="manual"):
    """设置某张图片的真值标签（复制归档，标签外文件夹中的副本会被移除）。

    source="review"（审核自动沉淀）时，若该图已被手动标注/手动清除过，
    则跳过不覆盖——手动结论优先。手动清除（labels=[]）也会记录来源，
    阻止后续自动沉淀把这张图又写回来。
    """
    t = get_task_meta(task)
    labels = labels or []
    for l in labels:
        if l not in t["labels"]:
            raise ValueError(f"标签不存在：{l}")

    if t["kind"] == "single" and len(labels) > 1:
        raise ValueError("单分类任务只能有一个标签")
    sources = t.setdefault("sources", {})
    if source == "review" and sources.get(rel) == "manual":
        return {'rel':rel, 
         'labels':(_labeled_map(task).get)(rel, []),  'skipped':"manual"}
    src = image_path(task, rel)
    if not os.path.exists(src):
        raise ValueError("图片不存在")
    for l in t["labels"]:
        dst = os.path.join(_task_dir(task), l, rel)
        if l in labels:
            os.makedirs((os.path.dirname(dst)), exist_ok=True)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
        elif os.path.exists(dst):
            os.remove(dst)
    sources[rel] = source
    _save_task_meta(task, t)
    return {'rel':rel, 
     'labels':labels}


def truth_label_map(task):
    """评估用：{图片 rel(不带扩展名统一): [labels]}"""
    return _labeled_map(task)


def _source_images(task_meta):
    snapshot = task_meta.get("images_snapshot")
    if isinstance(snapshot, list):
        return snapshot
    return datasets.scan_images(task_meta["dataset"])


def image_path(task, rel):
    snapshot = safe_path(_task_dir(task), "images", rel)
    if os.path.isfile(snapshot):
        return snapshot
    meta = get_task_meta(task)
    return datasets.image_path(meta["dataset"], rel)


def _dataset_short_name(dataset):
    """dataset ref（项目::图片集）取图片集名，用于生成任务名。"""
    try:
        return datasets.split_ref(dataset)[1]
    except Exception:
        return dataset.split("::")[-1]


def _ensure_sync_task(dataset, sample_status, sample_objects):
    """找到（或创建）该图片集接收审核沉淀的真值任务，返回任务 id。

    优先使用 primary_for 匹配的主任务；没有主任务时，若该图片集恰好只有
    一个已有任务则把它升级为主任务；否则按首条沉淀内容自动创建
    （有目标框 → 多标签，只有状态 → 单分类）。
    """
    tasks = list_tasks()
    for t in tasks:
        if t.get("primary_for") == dataset:
            return t["id"]
    candidates = [t for t in tasks if t.get("dataset") == dataset]

    if len(candidates) == 1:
        meta = get_task_meta(candidates[0]["id"])
        meta["primary_for"] = dataset
        meta["auto_sync"] = True
        _save_task_meta(candidates[0]["id"], meta)
        return candidates[0]["id"]
    kind = "multi" if sample_objects else "single"
    labels = list(sample_objects) if kind == "multi" else [sample_status]
    base = _dataset_short_name(dataset)
    name, i = f"{base}-审核沉淀", 2
    while os.path.exists(_task_json(_slug(name))):
        name = f"{base}-审核沉淀{i}"
        i += 1

    task = _create_task(name, kind, labels, dataset, min_labels=1, auto_sync=True,
      primary_for=dataset)
    return task["id"]


def _add_labels(task, new_labels):
    """给已有任务扩充标签（审核沉淀遇到新标签时自动长大）。"""
    meta = get_task_meta(task)
    added = []
    for raw in new_labels:
        label = _slug(raw)
        if label:
            if label not in meta["labels"]:
                meta["labels"].append(label)
                os.makedirs((os.path.join(_task_dir(task), label)), exist_ok=True)
                added.append(label)

    if added:
        _save_task_meta(task, meta)
    return added


def sync_from_review(dataset, rel, expected_status=None, expected_objects=None):
    """把一条人工审核的期望（状态/目标框）沉淀为该图片集的真值。

    返回 None 表示没有可沉淀的内容；返回 dict 带 task/skipped 等结果。
    手动标注过的图片不会被覆盖（skipped="manual"）。
    """
    status = str(expected_status or "").strip()
    obj_names = []
    for obj in expected_objects or []:
        if not isinstance(obj, dict):
            continue
        name = str(obj.get("labelName") or obj.get("name") or "").strip()
        if name and name not in obj_names:
            obj_names.append(name)
    if not status and not obj_names:
        return None
    task_id = _ensure_sync_task(dataset, status, obj_names)
    meta = get_task_meta(task_id)
    if meta["kind"] == "single":
        if not status:
            return {'task':task_id,  'task_name':meta.get("name"),  'skipped':"单分类任务只沉淀期望状态"}
        labels = [status]
    else:
        if not obj_names:
            return {'task':task_id,  'task_name':meta.get("name"),  'skipped':"多标签任务只沉淀期望目标框"}
        labels = obj_names
    new_labels = _add_labels(task_id, labels)
    result = set_labels(task_id, rel, [_slug(l) for l in labels], source="review")
    return {'task':task_id, 
     'task_name':meta.get("name"),  'labels':result.get("labels"), 
     'new_labels':new_labels,  'skipped':result.get("skipped")}


def sync_run(run_id):
    """把某次运行的全部人工审核批量沉淀为真值（历史数据迁移用）。

    同一图多次复现的审核取一份：优先取填了期望内容的那份。
    """
    from . import reviews, runner
    run = runner.get_run(run_id)
    dataset = run["dataset"]
    by_image = {}
    for row in reviews.list_reviews(run_id):
        rel = row.get("image")
        if not rel:
            continue
        has_content = bool(str(row.get("expected_status") or "").strip() or row.get("expected_objects"))
        if rel not in by_image or (has_content and not by_image[rel][1]):
            by_image[rel] = (row, has_content)
    stats = {
      'dataset': dataset, 'task': None, 'task_name': "",
      'synced': 0,  'skipped_manual': 0,  'empty': 0}

    for rel, (row, _) in sorted(by_image.items()):
        r = sync_from_review(dataset, rel, row.get("expected_status"), row.get("expected_objects") or [])
        if not r:
            stats["empty"] += 1
        else:
            stats["task"] = r.get("task")
            stats["task_name"] = r.get("task_name") or ""
            if r.get("skipped") == "manual":
                stats["skipped_manual"] += 1
            elif r.get("skipped"):
                stats["empty"] += 1
            else:
                stats["synced"] += 1

    return stats


def labels_for_image(dataset, rel):
    """审核页预填用：查某张图在该图片集关联真值任务中的标签。"""
    tasks = list_tasks()
    task_id = None
    for t in tasks:
        if t.get("primary_for") == dataset:
            task_id = t["id"]
            break

    if not task_id:
        candidates = [t for t in tasks if t.get("dataset") == dataset]
        if len(candidates) == 1:
            task_id = candidates[0]["id"]
    if not task_id:
        return {}
    meta = get_task_meta(task_id)
    labels = _labeled_map(task_id).get(rel, [])
    return {'task':task_id, 
     'task_name':(meta.get)("name"),  'kind':meta["kind"], 
     'labels':labels,  'source':(meta.get("sources") or {}).get(rel) or ""}
