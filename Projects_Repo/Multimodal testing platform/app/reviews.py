"""人工审核结果：与模型结果分离保存，支持逐张复核和裁判追溯。"""
import json, hashlib, math, os, re, time
from typing import Dict, List
from .config import safe_path, subdir
from . import comparison
from .dircache import FingerprintCache, fingerprint
VERDICTS = [
 "正确","误报","漏报","部分正确","无法判断"]

def _stem(rel, repeat):
    value = os.path.splitext(rel.replace("\\", "/"))[0]
    value = re.sub("[^\\w\\-\\u4e00-\\u9fff./]+", "_", value).replace("/", "__")
    digest = hashlib.sha1(rel.replace("\\", "/").encode("utf-8")).hexdigest()[:10]
    return f"{value}__{digest}__r{int(repeat)}.json"


def _path(run_id, rel, repeat):
    return safe_path(subdir("reviews"), run_id, _stem(rel, repeat))


def save_review(run_id, rel, repeat, payload):
    verdict = str(payload.get("verdict") or "").strip()
    if verdict not in VERDICTS:
        raise ValueError("审核结论必须是：" + "/".join(VERDICTS))
    expected_objects = _normalize_objects(run_id, rel, payload.get("expected_objects") or [])
    out = {'run_id':run_id, 
     'image':rel,  'repeat':int(repeat),  'verdict':verdict, 
     'expected_status':str(payload.get("expected_status")).strip() if (payload.get("expected_status") not in (None,
                                                                                       '')) else None, 
     'expected_objects':expected_objects, 
     'reason':(str(payload.get("reason") or "").strip)(), 
     'reviewer':(str(payload.get("reviewer") or "").strip)(), 
     'source_review':(payload.get)("source_review"), 
     'source_run_id':str(payload.get("source_run_id") or (payload.get("source_review") or {}).get("run_id") or ""), 
     'source_review_id':str(payload.get("source_review_id") or (payload.get("source_review") or {}).get("id") or ""), 
     'auto_derived':bool(payload.get("auto_derived", False)), 
     'updated':(time.strftime)("%Y-%m-%d %H:%M:%S")}
    p = _path(run_id, rel, repeat)
    os.makedirs((os.path.dirname(p)), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    _draw_review(out)
    return out


def _normalize_objects(run_id, rel, objects):
    from . import runner
    from .annotate import get_image_size
    run = runner.get_run(run_id)
    source = runner.image_file(run_id, rel)
    if not os.path.isfile(source):
        raise ValueError("原图不存在")
    width, height = get_image_size(source)
    out = []
    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            raise ValueError(f"第 {index + 1} 个人工目标格式错误")
        raw = obj.get("bbox")
        if isinstance(raw, list):
            if not (len(raw) == 4 and all((isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in raw))):
                raise ValueError(f"第 {index + 1} 个 bbox 必须是四个数字")
            x1, y1, x2, y2 = [float(v) for v in raw]
            x1, x2 = sorted((max(0, min(width - 1, x1)), max(0, min(width - 1, x2))))
            y1, y2 = sorted((max(0, min(height - 1, y1)), max(0, min(height - 1, y2))))
            if x2 - x1 < 2 or y2 - y1 < 2:
                raise ValueError(f"第 {index + 1} 个 bbox 面积过小")
            object_type = str(obj.get("object_type") or obj.get("type") or "object").strip().lower()
            if object_type not in {'辅助', 'object', '区域框', '辅助框', 'context_region', '区域', 'context'}:
                object_type = "object"
            out.append({'labelName':str(obj.get("labelName") or obj.get("name") or f"目标{index + 1}"),  'labelValue':str(obj.get("labelValue") or ""), 
             'evidence':str(obj.get("evidence") or ""), 
             'object_type':object_type, 
             'bbox':[
              round(x1), round(y1), round(x2), round(y2)]})
    return out


def _draw_review(review):
    objects = []
    for obj in review.get("expected_objects") or []:
        if not isinstance(obj, dict):
            pass
        else:
            objects.append({'name':obj.get("labelName") or obj.get("name") or "人工标注",  'bbox':(obj.get)("bbox"), 
             'bbox_normalized':(obj.get)("bbox_normalized"),  'attributes':{"labelValue": (obj.get("labelValue", ""))}})
    target = review_file((review["run_id"]), (review["image"]), (review["repeat"]), "annotated", create=True)

    if not objects:
        if os.path.isfile(target):
            os.remove(target)
        return
    try:
        from . import runner
        from .annotate import draw_objects
        run = runner.get_run(review["run_id"])
        source = runner.image_file(review["run_id"], review["image"])
        draw_objects(source, objects, target, show_fields=["labelValue"])
    except Exception:
        pass


def review_file(run_id, rel, repeat, kind='json', create=False):
    if kind == "annotated":
        name = os.path.splitext(_stem(rel, repeat))[0] + ".jpg"
        p = safe_path(subdir("reviews"), run_id, "annotated", name)
        if create:
            os.makedirs((os.path.dirname(p)), exist_ok=True)
        if create or os.path.exists(p):
            return p
        return
    p = _path(run_id, rel, repeat)
    if create or os.path.exists(p):
        return p


def get_review(run_id, rel, repeat):
    p = _path(run_id, rel, repeat)
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


_list_cache = FingerprintCache()

def list_reviews(run_id):
    root = safe_path(subdir("reviews"), run_id)
    fp = fingerprint(root)

    def compute():
        if not os.path.isdir(root):
            return []
        out = []
        for fn in os.listdir(root):
            if fn.endswith(".json"):
                try:
                    with open((os.path.join(root, fn)), "r", encoding="utf-8") as f:
                        out.append(json.load(f))
                except Exception:
                    continue
        return sorted(out, key=(lambda x: (x.get("image", ""), x.get("repeat", 0))))

    return _list_cache.get(run_id, fp, compute)


def summary(run_id):
    rows = list_reviews(run_id)
    counts = {v: 0 for v in VERDICTS}
    for row in rows:
        if row.get("verdict") in counts:
            counts[row["verdict"]] += 1
    return {'total':len(rows),  'counts':counts,  'metrics':metrics(run_id),  'items':rows}


def metrics(run_id):
    rows = list_reviews(run_id)
    counts = {verdict: 0 for verdict in VERDICTS}
    for row in rows:
        verdict = row.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
    reviewed = len(rows)
    correct = counts["正确"]
    decisive = reviewed - counts["无法判断"]

    return {'reviewed':reviewed, 
     'decisive':decisive,  'correct':correct,  'accuracy':round(correct / decisive, 4) if decisive else None, 
     'error_rate':round((decisive - correct) / decisive, 4) if decisive else None, 
     'false_positive':counts["误报"], 
     'false_negative':counts["漏报"],  'partial':counts["部分正确"], 
     'uncertain':counts["无法判断"],  'counts':counts}


def batch_save(run_id, verdict, scope='unreviewed'):
    """批量标记审核结论（如"剩余未审全部标正确"）。

    - 只处理已有结果且未调用失败的 (图片, 复现) 组合；
    - 标记"正确"时跳过解析失败的结果（解析失败不可能是正确）；
    - scope="unreviewed" 时跳过已有审核结论的条目，不覆盖人工劳动；
    - 期望状态/期望框自动取模型输出（标"正确"即认可模型结果），
      并在 repeat=1 时同步沉淀真值（沉淀失败不影响审核保存）。
    """
    from . import runner, truth
    if verdict not in VERDICTS:
        raise ValueError("审核结论必须是：" + "/".join(VERDICTS))
    run = runner.get_run(run_id)
    saved = 0
    skipped = 0
    for im in runner.list_run_images(run_id):
        rel = im.get("rel")
        if not rel:
            continue
        for rep in im.get("repeats") or []:
            if not rep.get("exists") or rep.get("error"):
                continue
            if verdict == "正确" and rep.get("parse_ok") is False:
                skipped += 1
                continue
            repeat = int(rep.get("repeat") or 1)
            if scope == "unreviewed" and get_review(run_id, rel, repeat).get("verdict"):
                skipped += 1
                continue
            result = {}
            try:
                result = runner.get_result(run_id, rel, repeat)
            except Exception:
                pass
            expected_objects = []
            for o in result.get("objects") or []:
                if isinstance(o, dict):
                    if not o.get("bbox"):
                        continue
                    expected_objects.append({'labelName':o.get("name") or "目标",
                     'labelValue':o.get("label_value") or "",
                     'evidence':o.get("evidence") or "",
                     'bbox':(o.get)("bbox")})
            save_review(run_id, rel, repeat, {'verdict':verdict,
             'expected_status':(result.get)("overall_status"),
             'expected_objects':expected_objects,
             'reason':"批量标记",
             'reviewer':"批量"})
            if repeat == 1:
                try:
                    truth.sync_from_review(run["dataset"], rel, result.get("overall_status"), expected_objects)
                except Exception:
                    pass
            saved += 1
    return {'saved':saved,
     'skipped':skipped}


def derive_verdict(result, expected_status, expected_objects, iou_threshold=0.5):
    """复用与裁判一致的确定性比较，避免两套规则产生冲突。

    没有足够人工期望时不强行给出“正确”，保守标记为“无法判断”。
    """
    diff = comparison.compare(result, {'expected_status':expected_status, 
     'expected_objects':expected_objects or []},
      iou_threshold=iou_threshold)
    return diff.get("deterministic_verdict") or "无法判断"


def reuse_baseline(source_run_id, target_run_id, overwrite=False):
    from . import runner
    source_rows = list_reviews(source_run_id)
    if not source_rows:
        raise ValueError("源运行没有人工审核基线")
    target_images = {item["rel"]: item for item in runner.list_run_images(target_run_id)}
    source_by_image = {}
    for row in source_rows:
        source_by_image.setdefault(row.get("image"), row)

    copied = skipped = unavailable = 0
    for rel, image in target_images.items():
        baseline = source_by_image.get(rel)
        if not baseline or not _same_image(source_run_id, target_run_id, rel):
            unavailable += 1
            continue
        for repeat_item in image.get("repeats", []):
            repeat = int(repeat_item["repeat"])
            if not repeat_item.get("exists") or repeat_item.get("error"):
                continue
            existing = get_review(target_run_id, rel, repeat)
            if existing and not overwrite:
                skipped += 1
                continue
            result = runner.get_result(target_run_id, rel, repeat)
            expected_objects = baseline.get("expected_objects") or []
            verdict = derive_verdict(result, baseline.get("expected_status"), expected_objects)
            save_review(target_run_id, rel, repeat, {'verdict':verdict,
             'expected_status':(baseline.get)("expected_status"),  'expected_objects':expected_objects,
             'reason':f"复用 {source_run_id} 的人工基线后自动比对；请在必要时人工复核",
             'reviewer':"基线复用",
             'source_review':{'run_id':source_run_id,
              'image':(baseline.get)("image"),  'repeat':(baseline.get)("repeat"),
              'id':_stem(str(baseline.get("image") or rel), int(baseline.get("repeat") or 1))},
             'source_run_id':source_run_id,
             'source_review_id':_stem(str(baseline.get("image") or rel), int(baseline.get("repeat") or 1)),
             'auto_derived':True})
            copied += 1
    return {'source_run_id':source_run_id,
     'target_run_id':target_run_id,  'copied':copied,
     'skipped':skipped,  'unavailable_images':unavailable,  'metrics':metrics(target_run_id)}


def _same_image(source_run_id, target_run_id, rel):
    from . import runner
    try:
        source = runner.image_file(source_run_id, rel)
        target = runner.image_file(target_run_id, rel)
        if os.path.getsize(source) != os.path.getsize(target):
            return False
        def digest(path):
            value = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1048576), b""):
                    value.update(chunk)
            return value.digest()
        return digest(source) == digest(target)
    except Exception:
        return False
