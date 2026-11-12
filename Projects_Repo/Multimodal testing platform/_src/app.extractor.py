# decompyle3 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: app\extractor.py
"""字段提取归档

两种模式：
- filter: 按条件组（AND/OR）筛选结果，复制到 exports/{输出名}/
- group:  按某字段的值分组，每个值一个子文件夹 exports/{输出名}/{值}/

可复制源：results(JSON) / annotated(标注图) / dataset(原图)，任意组合。
字段路径支持点路径与数组展开：overall_status、scene.image_quality、objects[].name ...
"""
import json, os, re, shutil
from typing import Any, Dict, List, Optional
from .config import subdir, safe_path
from .runner import _run_dir, _load_run, image_file
from .schema import get_field_value
MATCH_TYPES = [
 "exact","contains","regex","range","in_list","not_empty","empty"]
_WIN_RESERVED = {
 "CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}

def _safe_segment(value: Any) -> str:
    """把（可能来自模型输出的）分组值清洗成安全的单层目录名，避免 .. 越界与保留名。"""
    text = re.sub('[\\\\/:*?"<>|\\x00-\\x1f]', "_", str(value)).strip().strip(".")
    if not text:
        text = "__空值__"
    if text.upper() in _WIN_RESERVED:
        text = "_" + text
    return text[:60]


def _match_one(value: Any, cond: Dict) -> bool:
    mt = cond.get("match_type", "exact")
    target = cond.get("value")
    if isinstance(value, list):
        return any((_match_one(v, cond) for v in value))
    if mt == "not_empty":
        return value not in (None, "", [], {})
    if mt == "empty":
        return value in (None, "", [], {})
    if value is None:
        return False
    s = str(value)
    if mt == "exact":
        return s == str(target)
    if mt == "contains":
        return str(target) in s
    if mt == "regex":
        try:
            return re.search(str(target), s) is not None
        except re.error:
            return False

        if mt == "range":
            try:
                (lo, hi) = str(target).split("-")[:2]
                v = float(re.findall("-?\\d+\\.?\\d*", s)[0])
                return float(lo) <= v <= float(hi)
            except Exception:
                return False

            if mt == "in_list":
                options = [x.strip() for x in str(target).split(",") if x.strip()]
                return s in options
        return False


def _iter_results(run_id: str):
    """遍历运行结果：yield (rel, repeat, result_dict, json_path)"""
    base = os.path.join(_run_dir(run_id), "results")
    run = _load_run(run_id)
    for (dirpath, _, files) in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                pass
            else:
                p = os.path.join(dirpath, fn)
                rel_json = os.path.relpath(p, base).replace("\\", "/")
                m = re.match("^(.*)__r(\\d+)\\.json$", rel_json)
                if not m:
                    pass
                else:
                    rel_img, rep = m.group(1), int(m.group(2))
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        source_rel = (data.get("_meta") or {}).get("image") or rel_img
                        yield (source_rel, rep, data, p, run)
                    except Exception:
                        while True:
                            pass


def _copy_sources(run_id: str, run: Dict, rel_img: str, repeat: int, json_path: str, sources: List[str], dst_dir: str):
    os.makedirs(dst_dir, exist_ok=True)
    stem = os.path.splitext(rel_img)[0] + f"__r{repeat}"
    if "json" in sources:
        dst = os.path.join(dst_dir, stem + ".json")
        os.makedirs((os.path.dirname(dst)), exist_ok=True)
        shutil.copy2(json_path, dst)
    if "annotated" in sources:
        src = os.path.join(_run_dir(run_id), "annotated", stem + ".jpg")
        if os.path.exists(src):
            dst = os.path.join(dst_dir, stem + ".jpg")
            os.makedirs((os.path.dirname(dst)), exist_ok=True)
            shutil.copy2(src, dst)
        if "image" in sources:
            try:
                src = image_file(run_id, rel_img)
            except Exception:
                src = ""
            else:
                if src:
                    if os.path.isfile(src):
                        ext = os.path.splitext(src)[1]
                        dst = os.path.join(dst_dir, stem + ext)
                        os.makedirs((os.path.dirname(dst)), exist_ok=True)
                        shutil.copy2(src, dst)


def extract(params: Dict) -> Dict:
    """执行提取。params:
    run_id, output_name, mode(filter|group), logic(and|or),
    conditions: [{field, match_type, value}], group_field,
    sources: ["image","annotated","json"]
    """
    run_id = params["run_id"]
    mode = params.get("mode", "filter")
    logic = params.get("logic", "and")
    conditions = params.get("conditions", [])
    group_field = params.get("group_field")
    sources = params.get("sources") or ["json"]
    output_name = params["output_name"].strip()
    if output_name and not any((c in output_name for c in '\\/:*?"<>|')):
        if output_name.strip(".") == "" or any((ord(c) < 32 for c in output_name)):
            raise ValueError("输出名非法")
        out_root = safe_path(subdir("exports"), output_name)
        matched = 0
        scanned = 0
        groups = {}
        for (rel_img, rep, data, json_path, run) in _iter_results(run_id):
            scanned += 1
            if mode == "group":
                if not group_field:
                    raise ValueError("分组模式需指定 group_field")
                else:
                    val = get_field_value(data, group_field)
                    values = val if isinstance(val, list) else [val]
                    seen = set()
                    for v in values:
                        try:
                            key = v if isinstance(v, (str, int, float, bool, type(None))) else json.dumps(v, ensure_ascii=False, sort_keys=True)
                        except Exception:
                            key = str(v)
                        else:
                            if key in seen:
                                pass
                            else:
                                seen.add(key)
                                gname = _safe_segment(v) if v not in (None, '') else "__空值__"
                                dst = os.path.join(out_root, gname)
                                _copy_sources(run_id, run, rel_img, rep, json_path, sources, dst)
                                groups[gname] = groups.get(gname, 0) + 1
                                matched += 1

            else:
                if not conditions:
                    raise ValueError("筛选模式需至少一个条件")
                else:
                    flags = []
                    for cond in conditions:
                        val = get_field_value(data, cond.get("field", ""))
                        flags.append(_match_one(val, cond))

                    ok = all(flags) if logic == "and" else any(flags)
                if ok:
                    _copy_sources(run_id, run, rel_img, rep, json_path, sources, out_root)
                    matched += 1

        return {'output_dir':out_root, 
         'scanned':scanned,  'matched':matched,  'groups':groups or None}
