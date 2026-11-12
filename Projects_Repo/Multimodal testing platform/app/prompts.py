"""提示词版本库：workspace/prompts/{name}/V{n}.txt + meta.json

- 每个提示词是一组版本（V1/V2/V3...）
- meta.json 记录每版的说明、创建时间、父版本
- diff 基于 difflib，返回逐行对比（增/删/改）供前端高亮
"""
import difflib, hashlib, json, os, re, time, threading
from functools import wraps
from typing import Dict, List, Optional
from .config import subdir, safe_path
from .schema import build_full_prompt
_meta_lock = threading.RLock()

def _locked(function):

    @wraps(function)
    def wrapper(*args, **kwargs):
        with _meta_lock:
            return function(*args, **kwargs)

    return wrapper


def extract_sections(content):
    """从常见 Markdown/中文标题中提取提示词五段，便于版本管理和裁判定位。"""
    content = content or ""
    aliases = {
      'role': "(?:ROLE|角色(?:人设)?|人设)",
      'task': "(?:TASK|任务(?:目标|描述)?|目标)",
      'definition': "(?:DEFINITION|判定定义|判定标准|定义)",
      'workflow': "(?:WORKFLOW|视觉思维链|工作流程|分析流程)",
      'output_format': "(?:OUTPUT\\s*FORMAT|输出格式(?:约束)?)"}
    found = []
    for key, title in aliases.items():
        match = re.search(f"(?im)^(?:#+\\s*|【)?\\s*{title}(?:\\s*/[^\\n]*)?\\s*(?:】|[:：])?\\s*$", content)
        if match:
            found.append((match.start(), key, match.end()))
    found.sort()
    sections = {k: "" for k in aliases}

    for idx, (start, key, end) in enumerate(found):
        stop = found[idx + 1][0] if idx + 1 < len(found) else len(content)
        sections[key] = content[end:stop].strip()

    return sections


SECTION_ORDER = [
 "role","task","definition","workflow","output_format"]
SECTION_TITLES = {
  'role': "ROLE / 角色人设",  'task': "TASK / 任务目标",
  'definition': "DEFINITION / 判定定义",  'workflow': "WORKFLOW / 视觉思维链",
  'output_format': "OUTPUT FORMAT / 输出格式约束"}

def compose_sections(sections):
    return "\n\n".join((f'## {SECTION_TITLES[key]}\n{str(sections.get(key) or "").strip()}' for key in SECTION_ORDER)).strip() + "\n"


def _output_hash(content):
    output = extract_sections(content).get("output_format") or ""
    return hashlib.sha256(output.encode("utf-8")).hexdigest()[:16]


def _meta_path(name):
    return safe_path(subdir("prompts"), name, "meta.json")


def _load_meta(name):
    p = _meta_path(name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {'name':name, 
     'versions':[]}


def _save_meta(name, meta):
    p = _meta_path(name)
    os.makedirs((os.path.dirname(p)), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def list_prompts():
    root = subdir("prompts")
    out = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isdir(p):
            pass
        else:
            meta = _load_meta(name)
            versions = meta.get("versions", [])
            latest_entry = versions[-1] if versions else {}
            best_acc = None
            for v in versions:
                if v.get("status") == "rejected":
                    pass
                else:
                    acc = (v.get("metrics") or {}).get("accuracy")
                    if isinstance(acc, (int, float)):
                        if not isinstance(acc, bool):
                            if best_acc is None or acc > best_acc:
                                best_acc = acc

            out.append({'name':name, 
             'group':meta.get("group") or "", 
             'versions':versions, 
             'latest':(latest_entry.get)("version"), 
             'latest_status':latest_entry.get("status") or "draft", 
             'version_count':len(versions), 
             'best_accuracy':best_acc, 
             'updated':latest_entry.get("created") or ""})
    return out


_PROMPT_RESERVED = {
 "CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}

def _clean_name(name):
    """校验提示词名称，拒绝路径穿越（. / ..）、保留名、控制字符与超长名称。"""
    text = str(name or "").strip()
    if not text or any((c in text for c in '\\/:*?"<>|')) or any(
            (ord(c) < 32 for c in text)) or text.strip(".") == "" or text.upper() in _PROMPT_RESERVED:
        raise ValueError("名称非法")
    if len(text) > 80:
        raise ValueError("名称过长")
    return text


@_locked
def rename_prompt(old, new):
    """重命名提示词（目录整体改名，历史版本与指标保留）"""
    new = _clean_name(new)
    if new == old:
        raise ValueError("新名称与原名称相同")
    src = safe_path(subdir("prompts"), old)
    dst = safe_path(subdir("prompts"), new)
    if not os.path.isdir(src):
        raise ValueError("提示词不存在")
    if os.path.exists(dst):
        raise ValueError("同名提示词已存在")
    os.rename(src, dst)
    return {"name": new}


@_locked
def duplicate_prompt(name, new_name):
    """复制提示词（含全部版本文件与 meta，副本状态重置为 draft）"""
    import shutil
    new_name = _clean_name(new_name)
    src = safe_path(subdir("prompts"), name)
    dst = safe_path(subdir("prompts"), new_name)
    if not os.path.isdir(src):
        raise ValueError("提示词不存在")
    if os.path.exists(dst):
        raise ValueError("同名提示词已存在")
    shutil.copytree(src, dst)
    meta = _load_meta(new_name)
    for v in meta.get("versions", []):
        if v.get("status") == "released":
            v["status"] = "tested"
    meta.pop("released_version", None)
    _save_meta(new_name, meta)
    return {'name':new_name,
         'versions':len(meta.get("versions", []))}


@_locked
def create_prompt(name, content="", note="", group="", use_template=False):
    name = _clean_name(name)
    safe_path(subdir("prompts"), name)
    if os.path.exists(_meta_path(name)):
        raise ValueError("同名提示词已存在")
    os.makedirs((os.path.join(subdir("prompts"), name)), exist_ok=True)
    if not content:
        content = _default_template()
    entry = add_version(name, content, note or "初始版本")
    if group:
        if group.strip():
            update_meta(name, group=(group.strip()))
    return entry


@_locked
def update_meta(name, group=None):
    """修改提示词级属性（目前仅分组）。group 传空字符串表示移出分组。"""
    meta = _load_meta(name)
    if not meta.get("versions"):
        raise ValueError("提示词不存在")
    if group is not None:
        group = group.strip()
        if any((c in group for c in '\\/:*?"<>|')):
            raise ValueError("分组名非法")
        meta["group"] = group
    _save_meta(name, meta)
    return {'name':name, 
     'group':meta.get("group") or ""}


@_locked
def delete_version(name, version):
    """删除单个历史版本（运行记录含提示词快照，不影响历史结果查看）。
    最后一个版本不可删，应改为删除整个提示词。"""
    meta = _load_meta(name)
    versions = meta.get("versions", [])
    victim = next((v for v in versions if v["version"] == version), None)
    if not victim:
        raise ValueError("版本不存在")
    if len(versions) <= 1:
        raise ValueError("仅剩一个版本，请改为删除整个提示词")
    if victim.get("status") == "released":
        raise ValueError("已发布版本不能直接删除，请先发布其他版本或归档")
    p = safe_path(subdir("prompts"), name, f"V{version}.txt")
    if os.path.exists(p):
        os.remove(p)
    meta["versions"] = [v for v in versions if v["version"] != version]
    _save_meta(name, meta)


def _default_template():
    from .schema import OUTPUT_REFERENCE
    return compose_sections({
      'role': "你是严谨的多模态视觉分析专家，只依据图片中可见证据作答。",
      'task': "请识别图片中的目标或事件，并按本任务的二值标签给出结论。",
      'definition': "在此填写阳性、阴性的判定标准、合法标签枚举、边界情况与疑罪从无规则。",
      'workflow': "1. 检查图像质量；2. 定位目标；3. 逐项核对判定标准；4. 给出证据和矩形框；5. 自检 JSON。",
      'output_format': OUTPUT_REFERENCE})


@_locked
def add_version(name, content, note='', parent=None, metadata=None):
    metadata = metadata or {}
    if metadata.get("sections") is not None:
        content = compose_sections(metadata["sections"])
    if not str(content or "").strip():
        raise ValueError("提示词内容不能为空")
    meta = _load_meta(name)
    if not meta.get("versions") and parent:
        raise ValueError("尚无版本，无法指定父版本")
    versions = meta.get("versions") or []
    highest = max([int(v.get("version") or 0) for v in versions] or [0])
    counter = int(meta.get("next_version") or 0)
    version = max(counter, highest + 1)
    meta["next_version"] = version + 1
    p = safe_path(subdir("prompts"), name, f"V{version}.txt")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, p)
    entry = {'version':version,
     'note':note,
     'parent':parent if (parent is not None) else (version - 1 if version > 1 else None),
     'created':(time.strftime)("%Y-%m-%d %H:%M:%S"),
     'chars':len(content),
     'branch':str(metadata.get("branch") or "main"),
     'status':str(metadata.get("status") or "draft"),
     'change_summary':str(metadata.get("change_summary") or note or ""),
     'expected_effect':str(metadata.get("expected_effect") or ""),
     'changed_modules':[key for key in metadata.get("changed_modules") or [] if key in SECTION_ORDER],
     'source_run':(metadata.get)("source_run"),
     'judge_refs':list(metadata.get("judge_refs") or []),
     'metrics':dict(metadata.get("metrics") or {}),
     'output_format_hash':_output_hash(content)}
    meta.setdefault("versions", []).append(entry)
    _save_meta(name, meta)
    return entry


@_locked
def update_version(name, version, note=None, content=None, status=None):
    """只允许改 note；改内容请新建版本（保证历史运行可溯源）"""
    meta = _load_meta(name)
    for v in meta.get("versions", []):
        if v["version"] == version:
            if note is not None:
                v["note"] = note
            if status is not None:
                if status not in ('draft', 'tested', 'released', 'archived'):
                    raise ValueError("版本状态非法")
                if status == "released":
                    for other in meta.get("versions", []):
                        if other.get("status") == "released":
                            other["status"] = "tested"
                    meta["released_version"] = version
                v["status"] = status
            _save_meta(name, meta)
            return None
    raise ValueError("版本不存在")


def get_version(name, version):
    p = safe_path(subdir("prompts"), name, f"V{version}.txt")
    if not os.path.exists(p):
        raise ValueError(f"版本 V{version} 不存在")
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    meta = _load_meta(name)
    info = next((v for v in meta.get("versions", []) if v["version"] == version), {})
    return {'name':name, 
     'version':version,  'content':content,  'sections':extract_sections(content), 
     'full_prompt':build_full_prompt(content), 
     'info':info}


@_locked
def delete_prompt(name):
    import shutil
    p = safe_path(subdir("prompts"), name)
    if os.path.isdir(p):
        shutil.rmtree(p)


def diff_versions(name, v1, v2):
    """逐行 diff：返回 [{tag: equal/add/del/change, v1_lines, v2_lines}]"""
    a = get_version(name, v1)["content"].splitlines()
    b = get_version(name, v2)["content"].splitlines()
    sm = difflib.SequenceMatcher(a=a, b=b)
    rows = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        rows.append({'tag':tag, 
         'v1_start':i1 + 1, 
         'v2_start':j1 + 1,  'v1_lines':a[i1:i2], 
         'v2_lines':b[j1:j2]})

    return rows


def summary_diff(name, v1, v2):
    """版本差异摘要：新增/删除/修改行数"""
    rows = diff_versions(name, v1, v2)
    add = sum((len(r["v2_lines"]) for r in rows if r["tag"] == "insert"))
    dele = sum((len(r["v1_lines"]) for r in rows if r["tag"] == "delete"))
    chg = sum((max(len(r["v1_lines"]), len(r["v2_lines"])) for r in rows if r["tag"] == "replace"))
    return {'added':add, 
     'deleted':dele,  'changed':chg}


def diff_sections(name, v1, v2):
    a = get_version(name, v1)["sections"]
    b = get_version(name, v2)["sections"]
    return {key: {'changed':a.get(key) != b.get(key),  'before':(a.get)(key, ""),  'after':(b.get)(key, "")} for key in SECTION_ORDER}


@_locked
def rollback(name, target, note=''):
    source = get_version(name, target)
    latest = _load_meta(name).get("versions", [])[-1]["version"]
    return add_version(name, source["content"], note or f"回滚到 V{target}", latest, {'branch':(source["info"].get)("branch", "main"), 
     'change_summary':f"从 V{latest} 回滚到 V{target}", 
     'changed_modules':SECTION_ORDER})


@_locked
def merge_versions(name, sources, note='', branch='main'):
    if not sources:
        raise ValueError("请选择至少一个模块来源")
    versions = _load_meta(name).get("versions", [])
    if not versions:
        raise ValueError("提示词不存在")
    latest = versions[-1]["version"]
    sections = dict(get_version(name, latest)["sections"])
    changed = []
    for key, version in sources.items():
        if key not in SECTION_ORDER:
            raise ValueError(f"未知模块：{key}")
        sections[key] = get_version(name, int(version))["sections"].get(key, "")
        changed.append(key)

    return add_version(name, "", note or "模块合并", latest, {'sections':sections, 
     'branch':branch,  'change_summary':note or "模块合并", 
     'changed_modules':changed})


@_locked
def attach_metrics(name, version, run_id, metrics):

    def merge(base: Dict, incoming: Dict) -> Dict:
        out = dict(base or {})
        for key, value in (incoming or {}).items():
            if value is not None:
                out[key] = value
        return out

    meta = _load_meta(name)
    for item in meta.get("versions", []):
        if item["version"] == version:
            previous_run = item.setdefault("run_metrics", {}).get(run_id) or {}
            item["run_metrics"][run_id] = merge(previous_run, metrics)
            item["metrics"] = merge(item.get("metrics") or {}, metrics)
            if item.get("status") == "draft":
                item["status"] = "tested"
            _save_meta(name, meta)
            return None
    raise ValueError("提示词版本不存在")


@_locked
def mark_version_status(name, version, status):
    """标记版本为 accepted/rejected，供 best_version 排除被拒候选。"""
    if status not in ('accepted', 'rejected', 'tested'):
        raise ValueError("无效的版本状态")
    meta = _load_meta(name)
    for item in meta.get("versions", []):
        if item["version"] == version:
            item["status"] = status
            _save_meta(name, meta)
            return None
    raise ValueError("提示词版本不存在")


def _metric_value(metrics, path):
    value = metrics
    for key in str(path or "").split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def best_version(name, metric='accuracy'):
    meta = _load_meta(name)
    ranked = []
    for item in meta.get("versions", []):
        if item.get("status") == "rejected":
            pass
        else:
            value = _metric_value(item.get("metrics") or {}, metric)
            if value is not None:
                ranked.append((float(value), item["version"], item))

    if not ranked:
        return {'metric':metric,  'version':None,  'value':None}
    (value, version, info) = max(ranked, key=(lambda x: (x[0], x[1])))
    return {
      'metric': metric, 'version': version, 'value': value, 'info': info}


def safe_version_ref(name, version):
    return f"{name}/V{version}"


def output_format_hash(content):
    return _output_hash(content)


DEFAULT_SETTINGS = {'output_mode':"fixed", 
 'status_labels':[
  "abnormal", "normal"], 
 'map':{
   'status_field': "",
   'objects_path': "",
   'name_field': "",
   'bbox_field': ""}}

def get_settings(name):
    meta = _load_meta(name)
    s = meta.get("settings") or {}
    out = json.loads(json.dumps(DEFAULT_SETTINGS))
    out["output_mode"] = s.get("output_mode", "fixed")
    labels = s.get("status_labels")
    if isinstance(labels, list):
        if len(labels) >= 2:
            out["status_labels"] = [
             str(labels[0]).strip(), str(labels[1]).strip()]
    out["map"].update(s.get("map") or {})
    return out


def update_settings(name, settings):
    meta = _load_meta(name)
    if not meta.get("versions"):
        raise ValueError("提示词不存在")
    mode = settings.get("output_mode", "fixed")
    if mode not in ('fixed', 'custom'):
        raise ValueError("output_mode 必须是 fixed 或 custom")
    cur = get_settings(name)
    cur["output_mode"] = mode
    labels = settings.get("status_labels")
    if labels is not None:
        if not isinstance(labels, list) or len(labels) != 2:
            raise ValueError("status_labels 必须包含两个结果标签")
        labels = [str(x).strip() for x in labels]
        if not all(labels) or labels[0].casefold() == labels[1].casefold():
            raise ValueError("两个结果标签必须非空且不能相同")
        cur["status_labels"] = labels
    for k in ('status_field', 'objects_path', 'name_field', 'bbox_field'):
        if k in (settings.get("map") or {}):
            cur["map"][k] = str(settings["map"][k]).strip()
    meta["settings"] = cur
    _save_meta(name, meta)
    return cur
