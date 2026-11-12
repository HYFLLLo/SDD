"""项目/图片集管理。

新结构：workspace/datasets/{project}/{dataset}/；旧的 workspace/datasets/{dataset}/
继续可读，并在界面归入“未归档项目”。数据集引用使用 project::dataset，避免 URL 中的斜杠。
"""
import json, os, shutil, threading, time
from functools import wraps
from typing import Dict, List, Optional, Tuple
from .config import subdir, safe_path
IMG_EXTS = {
 ".jpg",".jpeg",".png",".bmp",".webp"}
MAX_UPLOAD_BYTES = 52428800
PROJECT_META = "project.json"
DATASET_META = "dataset.json"
LEGACY_PROJECT = "未归档项目"
_data_lock = threading.RLock()
_project_cache = {'at':0.0,  'items':None}

def _locked(function):

    @wraps(function)
    def wrapper(*args, **kwargs):
        with _data_lock:
            result = function(*args, **kwargs)
            _project_cache["at"] = 0.0
            _project_cache["items"] = None
            return result

    return wrapper


def _clean_name(name):
    name = str(name or "").strip()
    if not name or any((c in name for c in "\\/:*?\"<>|")) or "::" in name:
        raise ValueError("名称非法")
    return name


def dataset_ref(project, dataset):
    return f"{_clean_name(project)}::{_clean_name(dataset)}"


def split_ref(ref):
    ref = str(ref or "").strip()
    if "::" in ref:
        project, dataset = ref.split("::", 1)
        return (
         _clean_name(project), _clean_name(dataset))
    return (LEGACY_PROJECT, _clean_name(ref))


def _project_dir(project):
    return safe_path(subdir("datasets"), _clean_name(project))


def _is_project_dir(path):
    return os.path.isfile(os.path.join(path, PROJECT_META))


def _dataset_dir(ref, create=False):
    project, dataset = split_ref(ref)
    root = subdir("datasets")
    if project == LEGACY_PROJECT:
        legacy = safe_path(root, dataset)
        if os.path.isdir(legacy) or not create:
            return legacy
        project = LEGACY_PROJECT
    return safe_path(root, project, dataset)


@_locked
def create_project(name, description=''):
    name = _clean_name(name)
    p = _project_dir(name)
    if os.path.isdir(p) and not _is_project_dir(p):
        raise ValueError("该名称已被旧图片集占用")
    os.makedirs(p, exist_ok=True)
    meta = {'name':name, 'description':str(description or "").strip(), 'created':time.strftime("%Y-%m-%d %H:%M:%S")}
    old = os.path.join(p, PROJECT_META)
    if os.path.exists(old):
        raise ValueError("同名项目已存在")
    with open(old, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def list_projects():
    with _data_lock:
        if _project_cache["items"] is not None:
            if time.time() - _project_cache["at"] < 3:
                return json.loads(json.dumps((_project_cache["items"]), ensure_ascii=False))
    root = subdir("datasets")
    projects = []
    legacy = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isdir(p):
            pass
        elif _is_project_dir(p):
            try:
                with open((os.path.join(p, PROJECT_META)), "r", encoding="utf-8") as f:
                    meta = json.load(f)
                items = _project_datasets(name)
            except Exception:
                continue

            else:
                projects.append({**meta, **{'id':name,  'datasets':items,  'dataset_count':len(items), 
                 'image_count':sum((x["count"] for x in items))}})
        else:
            legacy.append(_dataset_item(LEGACY_PROJECT, name, legacy=True))

    if legacy:
        projects.append({'id':LEGACY_PROJECT,  'name':LEGACY_PROJECT,  'description':"兼容升级前创建的图片集", 
         'legacy':True,  'datasets':legacy, 
         'dataset_count':len(legacy),  'image_count':sum((x["count"] for x in legacy))})
    result = sorted(projects, key=(lambda x: (bool(x.get("legacy")), x["name"])))
    with _data_lock:
        _project_cache["items"] = result
        _project_cache["at"] = time.time()
    return json.loads(json.dumps(result, ensure_ascii=False))


def get_project(name):
    item = next((x for x in list_projects() if x["name"] == name), None)
    if not item:
        raise ValueError("项目不存在")
    return item


@_locked
def delete_project(name):
    name = _clean_name(name)
    if name == LEGACY_PROJECT:
        raise ValueError("未归档项目不能整体删除")
    p = _project_dir(name)
    if not _is_project_dir(p):
        raise ValueError("项目不存在")
    if _project_datasets(name):
        raise ValueError("项目中仍有图片集，请先逐个处理")
    shutil.rmtree(p)


def _load_dataset_meta(ref):
    p = os.path.join(_dataset_dir(ref), DATASET_META)
    if not os.path.exists(p):
        return {"splits": {}}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"splits": {}}
    except Exception:
        return {"splits": {}}


def _save_dataset_meta(ref, meta):
    p = os.path.join(_dataset_dir(ref), DATASET_META)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def get_dataset(ref):
    project, name = split_ref(ref)
    path = _dataset_dir(ref)
    if not os.path.isdir(path):
        raise ValueError("图片集不存在")
    item = _dataset_item(project, name, legacy=(project == LEGACY_PROJECT))
    item["metadata"] = _load_dataset_meta(ref)
    return item


def dataset_exists(ref):
    return os.path.isdir(_dataset_dir(ref))


@_locked
def update_dataset_meta(ref, updates):
    if not os.path.isdir(_dataset_dir(ref)):
        raise ValueError("图片集不存在")
    meta = _load_dataset_meta(ref)
    for key, value in (updates or {}).items():
        if key == "splits":
            continue
        meta[key] = value
    _save_dataset_meta(ref, meta)
    return meta


def _dataset_item(project, name, legacy=False):
    ref = name if legacy else dataset_ref(project, name)
    imgs = scan_images(ref)
    counts = {}
    for image in imgs:
        split = image.get("split") or "未分组"
        counts[split] = counts.get(split, 0) + 1

    return {'name':name,  'project':project,  'ref':ref,  'legacy':legacy,  'count':len(imgs), 
     'split_counts':counts}


def _project_datasets(project):
    p = _project_dir(project)
    out = []
    if not os.path.isdir(p):
        return out
    for name in sorted(os.listdir(p)):
        dp = os.path.join(p, name)
        if os.path.isdir(dp):
            out.append(_dataset_item(project, name))
    return out


def list_datasets():
    return [dataset for project in list_projects() for dataset in project["datasets"]]


@_locked
def create_dataset(name, project=''):
    name = _clean_name(name)
    if project:
        project = _clean_name(project)
        if not _is_project_dir(_project_dir(project)):
            create_project(project)
        ref = dataset_ref(project, name)
        p = _dataset_dir(ref, create=True)
    else:
        p = safe_path(subdir("datasets"), name)
    if os.path.isfile(p):
        raise ValueError("同名文件占用了图片集路径")
    if os.path.isdir(p) and any((True for _ in os.scandir(p))):
        return p
    os.makedirs(p, exist_ok=True)
    ref = dataset_ref(project, name) if project else name
    meta = _load_dataset_meta(ref)
    if not meta.get("created"):
        meta["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save_dataset_meta(ref, meta)
    return p


def scan_images(dataset, split=None):
    """递归扫描图片，返回 [{rel, name}]，rel 为相对数据集根目录的路径"""
    base = _dataset_dir(dataset)
    if not os.path.isdir(base):
        return []
    out = []
    split_map = _load_dataset_meta(dataset).get("splits") or {}
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() in IMG_EXTS:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, base).replace("\\", "/")
                image_split = split_map.get(rel, "未分组")
                if split and image_split != split:
                    continue
                out.append({'rel':rel,  'name':os.path.splitext(fn)[0],  'sub':(os.path.dirname)(rel),
                 'split':image_split})
    out.sort(key=(lambda x: x["rel"]))
    return out


def image_path(dataset, rel):
    return safe_path(_dataset_dir(dataset), rel)


def import_from_path(dataset, src_dir):
    """从本机目录导入图片（复制，保持子目录结构）"""
    if not os.path.isdir(src_dir):
        raise ValueError("源目录不存在")
    project, name = split_ref(dataset)
    base = create_dataset(name, "" if project == LEGACY_PROJECT else project)
    source_real = os.path.realpath(src_dir)
    base_real = os.path.realpath(base)
    try:
        common = os.path.commonpath([source_real, base_real])
    except ValueError:
        common = ""
    if source_real == base_real or common in {source_real, base_real}:
        raise ValueError("导入目录不能与目标图片集互相包含")
    n = 0
    for dirpath, _, files in os.walk(src_dir):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in IMG_EXTS:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, src_dir)
                dst = os.path.join(base, rel)
                os.makedirs((os.path.dirname(dst)), exist_ok=True)
                shutil.copy2(src, dst)
                n += 1
    return n

def save_upload(dataset, filename, data, sub=''):
    project, name = split_ref(dataset)
    base = create_dataset(name, "" if project == LEGACY_PROJECT else project)
    filename = os.path.basename(filename)
    if not filename or os.path.splitext(filename)[1].lower() not in IMG_EXTS:
        raise ValueError("仅支持 jpg/jpeg/png/bmp/webp 图片")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("单张图片不能超过 50MB")
    dst_dir = base if (not sub) else (safe_path(base, sub))
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, filename)
    if os.path.exists(dst):
        stem, ext = os.path.splitext(filename)
        index = 2
        while os.path.exists(os.path.join(dst_dir, f"{stem}_{index}{ext}")):
            index += 1

        dst = os.path.join(dst_dir, f"{stem}_{index}{ext}")
    with open(dst, "wb") as f:
        f.write(data)
    try:
        from .annotate import get_image_size
        get_image_size(dst)
    except Exception:
        os.remove(dst)
        raise ValueError("上传文件不是可读取的图片")
    else:
        return dst


@_locked
def delete_dataset(name):
    p = _dataset_dir(name)
    if os.path.isdir(p):
        shutil.rmtree(p)


@_locked
def delete_image(dataset, rel):
    """删除数据集中的单张图片（历史运行的结果 JSON 仍保留，但原图/标注图将不可见）"""
    p = image_path(dataset, rel)
    if not os.path.isfile(p):
        raise ValueError("图片不存在")
    os.remove(p)
    meta = _load_dataset_meta(dataset)
    if rel in (meta.get("splits") or {}):
        meta["splits"].pop(rel, None)
        _save_dataset_meta(dataset, meta)
    base = _dataset_dir(dataset)
    d = os.path.dirname(p)
    while d != base and os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)
        d = os.path.dirname(d)


@_locked
def set_image_split(dataset, rel, split):
    allowed = {
     "未分组","优化集","验证集","测试集","回归集"}
    split = str(split or "未分组").strip()
    if split not in allowed:
        raise ValueError("数据分组必须是：" + "/".join(sorted(allowed)))
    if not os.path.isfile(image_path(dataset, rel)):
        raise ValueError("图片不存在")
    meta = _load_dataset_meta(dataset)
    meta.setdefault("splits", {})[rel] = split
    _save_dataset_meta(dataset, meta)
    return {'rel':rel, 
     'split':split}
