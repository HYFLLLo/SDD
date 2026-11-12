"""开放式最小 JSON 协议与历史格式容错解析。

设计原则：
- 系统【不】自动修改用户提示词；提示词库中提供一份"参考输出格式"，
  由用户自行写进提示词（可直接照抄，也可改说明文字、增删子字段）；
- 最小协议为 scene_analysis / objects / analysis_summary；业务字段可以扩展；
- overall_status 是内部统一字段，可从场景二值结果和任务标签推导；
- 解析继续容错旧别名 overall_status、inspection_status、defect_list 等；
- objects 子字段认 label / category / confidence / bbox / value / description / evidence
  （容错 labelName / name / labelValue 等旧别名），其余子字段原样保留在 attributes；
- bbox 统一输出绝对像素坐标 + 归一化坐标，兼容 GLanLMM 1.5 及更早的绝对坐标、
  GLanLMM 1.6 及其余所有模型的 0-1000 相对坐标。
"""
import json, math, re
from typing import Any, Dict, List, Optional, Tuple
OUTPUT_REFERENCE = '【输出格式要求】\n你必须且只能输出一个标准 JSON 对象，不要 markdown 或解释文字。\n最小协议字段不可删除；业务字段可在 scene_analysis 和 objects 中扩展。\n{\n  "scene_analysis": {\n    "image_quality": "清晰/模糊/无法判断",\n    "是否存在目标/事件": "是/否"\n  },\n  "objects": [\n    {\n      "labelName": "任务定义的目标或事件名称",\n      "labelValue": "任务定义的结果标签",\n      "evidence": "详细视觉证据，疑罪从无",\n      "bbox": [x1, y1, x2, y2]\n    }\n  ],\n  "analysis_summary": "一句话总结"\n}\n规则：\n1. scene_analysis、objects、analysis_summary 必须存在；没有目标时 objects 输出 []；\n2. bbox 必须是一维四元数组 [左上角x, 左上角y, 右下角x, 右下角y]，坐标对应原图；\n3. labelName、labelValue 必须使用任务约定的枚举值；证据不足时不要臆测；\n4. 可增加自定义字段，但不得改变上述字段含义。'
HEAD_KEYS = [
 "scene_analysis", "objects", "analysis_summary"]
OBJECT_KEYS = ["labelName", "labelValue", "evidence", "bbox"]

def build_full_prompt(user_prompt):
    """历史兼容接口：系统不再追加任何内容，原样返回用户提示词。"""
    return user_prompt


_STATUS_ALIASES = [
 "overall_status", "inspection_status", "status", "result_status"]
_OBJECTS_ALIASES = ["objects","object_list","defect_list","detected_objects","targets"]
_CLASSIFICATION_ALIASES = ["classification", "class_result", "cls"]
_CLS_LABEL_ALIASES = ["label","name","class","category","result"]
_NAME_ALIASES = ["label","labelName","name","object_name","type","defect_type","violation_type"]
_BBOX_ALIASES = ["bbox","Vertex","vertex","box","bounding_box"]
_CONF_ALIASES = ["confidence", "score", "prob"]
_LABELVALUE_ALIASES = ["value", "labelValue", "label_value"]
_EVIDENCE_ALIASES = ["evidence", "Evidence", "visual_evidence"]
_DESC_ALIASES = ["description", "desc", "reasoning", "influence"]
_ABNORMAL_WORDS = {
 "abnormal","异常","违规","报警","有缺陷","true","是","有","存在"}
_NORMAL_WORDS = {"normal","正常","无违规","不报警","无缺陷","false","否","无","不存在"}

def _first_key(d, keys):
    for k in keys:
        if isinstance(d, dict):
            if k in d:
                if d[k] is not None:
                    return d[k]

    lower = {str(k).lower(): k for k in d.keys()} if isinstance(d, dict) else {}
    for k in keys:
        if k.lower() in lower:
            if d[lower[k.lower()]] is not None:
                return d[lower[k.lower()]]


_MISSING = object()


def _loads_any(text):
    """json.loads 的安全包装：失败返回 _MISSING 哨兵，便于区分 None/null。"""
    try:
        return json.loads(text)
    except Exception:
        return _MISSING


def _loads_object(text):
    """能解析成 JSON 对象就返回对象，否则 None。"""
    data = _loads_any(text)
    return data if isinstance(data, dict) else None


def _manual_unescape(text):
    """整体被引号包裹、转义又不完整的载荷 → 还原成 JSON 文本。

    真实坏样本：模型输出 "{\"a\": 1}"，但结尾内部引号漏了反斜杠，
    json.loads 直接失败。这里只解反斜杠转义的双引号、反斜杠与斜杠三种，避免破坏 JSON 语义。
    """
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt in ('"', "\\", "/"):
                out.append(nxt)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _unwrap_string_payload(value, depth=3):
    """模型偶尔把整个 JSON 再序列化成字符串（外层多一层引号 + 转义）。

    逐层解包，最多 depth 层，避免异常数据无限递归。转义残缺时退化为手动
    反转义，再交给 JSON 解析器判断。
    """
    for _ in range(depth):
        if not isinstance(value, str):
            break
        stripped = value.strip()
        if not stripped or stripped[0] not in "{\"":
            break
        inner = _loads_any(stripped)
        if inner is _MISSING:
            if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
                repaired = _manual_unescape(stripped[1:-1])
                if _loads_any(repaired) is not _MISSING:
                    value = repaired
                    continue
            break
        if isinstance(inner, str) and inner.strip() == stripped:
            break
        if not isinstance(inner, (dict, str)):
            break
        value = inner
    return value


_BRACKET_PAIRS = {"}": "{", "]": "["}


def _drop_stray_closers(text):
    """扫描并删除「栈里没有对应开括号」或「类型不匹配」的右括号。

    模型常见坏样本：bbox 写成 [213,341,232,386]]，多一个 ]。这里按括号栈
    定位真正多余的字符，避免按总数误删到列表内部的合法括号。
    """
    stack = []
    stray = []
    in_string = False
    escaped = False
    for index, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack and stack[-1] == _BRACKET_PAIRS[ch]:
                stack.pop()
            else:
                stray.append(index)
    if not stray:
        return text, stack
    drop = set(stray)
    return "".join(ch for i, ch in enumerate(text) if i not in drop), stack


def _repair_trailing_closers(text):
    """修正括号问题：先删多余右括号，再补齐缺失的右括号。

    每一步都用 json.loads 验证，命中即返回；全部失败时返回最接近的候选，
    由调用方决定是否放弃解析。
    """
    cleaned, stack = _drop_stray_closers(text)
    candidates = [cleaned]
    if stack:
        candidates.append(cleaned + "".join("}" if c == "{" else "]" for c in reversed(stack)))
    for candidate in candidates:
        if _loads_object(candidate) is not None:
            return candidate
    return cleaned


def extract_json_block(text):
    """从模型输出中提取 JSON 文本（剥离代码块围栏，截取首个完整对象）"""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    if not t:
        return None
    if _loads_object(t) is not None:
        return t
    # 整体是被序列化的字符串（二次编码）：解包后重新判断
    unwrapped = _unwrap_string_payload(t)
    if isinstance(unwrapped, dict):
        return json.dumps(unwrapped, ensure_ascii=False)
    if isinstance(unwrapped, str) and _loads_object(unwrapped.strip()) is not None:
        return unwrapped.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end > start:
        candidate = t[start:end + 1]
        if _loads_object(candidate) is not None:
            return candidate
        inner = _unwrap_string_payload(candidate)
        if isinstance(inner, dict):
            return json.dumps(inner, ensure_ascii=False)
        fixed = _repair_trailing_closers(candidate)
        if _loads_object(fixed) is not None:
            return fixed
        return candidate
    return None

def parse_bbox(raw):
    """解析多种 bbox 形式为 [x1,y1,x2,y2] 数值列表"""
    if raw is None:
        return
    if isinstance(raw, str):
        nums = re.findall("-?\\d+\\.?\\d*", raw)
        if len(nums) >= 4:
            return [float(x) for x in nums[:4]]
        return
    if isinstance(raw, (list, tuple)):
        if len(raw) >= 4:
            if all((isinstance(x, (int, float)) for x in raw[:4])):
                return [float(x) for x in raw[:4]]
            if len(raw) > 0:
                if isinstance(raw[0], (list, tuple)):
                    return parse_bbox(raw[0])


def _coord_base(model):
    """按模型返回相对坐标的除数基值；None 表示该模型使用绝对像素坐标。

    - GLanLMM 1.5 及更早：绝对像素坐标
    - GLanLMM 1.6 及更新、其余所有模型：0-1000 相对坐标，除以 1000
      （0-999 与 0-1000 的口径差异折算后不足 1 像素，统一按 1000 处理）
    """
    m = (model or "").lower()
    if "glan" in m:
        match = re.search("glan[a-z_]*v?(\\d+(?:\\.\\d+)?)", m)
        if match and float(match.group(1)) <= 1.5:
            return
    return 1000.0


def normalize_bbox(bbox, model, img_w, img_h):
    """统一转绝对像素 + 归一化坐标

    - 值域 <=1.5：视为归一化坐标
    - GLanLMM 1.6 及其余模型且值域 <=1000：视为 0-1000 相对坐标
    - GLanLMM 1.5 及更早：绝对像素坐标
    - 其余：视为绝对像素坐标
    """
    x1, y1, x2, y2 = bbox
    mx = max(abs(x1), abs(y1), abs(x2), abs(y2))
    base = _coord_base(model)
    if mx <= 1.5:
        nx1, ny1, nx2, ny2 = (
         x1, y1, x2, y2)
        ax1, ay1 = nx1 * img_w, ny1 * img_h
        ax2, ay2 = nx2 * img_w, ny2 * img_h
    elif base is not None and mx <= base:
        ax1 = x1 / base * img_w
        ay1 = y1 / base * img_h
        ax2 = x2 / base * img_w
        ay2 = y2 / base * img_h
        nx1, ny1, nx2, ny2 = (ax1 / img_w, ay1 / img_h, ax2 / img_w, ay2 / img_h)
    else:
        ax1, ay1, ax2, ay2 = (
         x1, y1, x2, y2)
        nx1, ny1 = ax1 / img_w, ay1 / img_h
        nx2, ny2 = ax2 / img_w, ay2 / img_h
    ax1, ax2 = sorted((max(0.0, min(img_w - 1, ax1)), max(0.0, min(img_w - 1, ax2))))
    ay1, ay2 = sorted((max(0.0, min(img_h - 1, ay1)), max(0.0, min(img_h - 1, ay2))))
    nx1, nx2 = ax1 / max(1, img_w), ax2 / max(1, img_w)
    ny1, ny2 = ay1 / max(1, img_h), ay2 / max(1, img_h)
    abs_box = [int(round(v)) for v in (ax1, ay1, ax2, ay2)]
    norm_box = [round(max(0.0, min(1.0, v)), 4) for v in (nx1, ny1, nx2, ny2)]
    return (
     abs_box, norm_box)


def _status_labels(labels):
    if not labels or len(labels) < 2:
        return
    cleaned = [str(x).strip() for x in labels[:2] if str(x).strip()]
    if len(cleaned) != 2 or cleaned[0].casefold() == cleaned[1].casefold():
        return
    return (cleaned[0], cleaned[1])


def normalize_status(raw, objects, labels=None):
    """按任务配置的二值标签归一化；未配置时仅兼容旧别名并保留未知值。"""
    pair = _status_labels(labels)
    if pair:
        positive, negative = pair
        if raw is None:
            if objects:
                return positive
            return negative
        if isinstance(raw, bool):
            if raw:
                return positive
            return negative
        if isinstance(raw, (int, float)) and raw in (0, 1):
            if raw == 1:
                return positive
            return negative
        s = str(raw).strip()
        if s == "1":
            return positive
        if s == "0":
            return negative
        if s.casefold() in {positive.casefold(), negative.casefold()}:
            if s.casefold() == positive.casefold():
                return positive
            return negative
        if s.casefold() in _ABNORMAL_WORDS or "异常" in s or "违规" in s:
            return positive
        if s.casefold() in _NORMAL_WORDS or "正常" in s:
            return negative
        return s
    if raw is None:
        if objects:
            return "abnormal"
        return "normal"
    if isinstance(raw, bool):
        if raw:
            return "abnormal"
        return "normal"
    s = str(raw).strip().lower()
    if s in _ABNORMAL_WORDS:
        return "abnormal"
    if s in _NORMAL_WORDS:
        return "normal"
    if "abnormal" in s or "异常" in s or "违规" in s:
        return "abnormal"
    return s


def _scene_status(data):
    """从新协议 scene_analysis 中提取业务二值结论，跳过图像质量等描述字段。"""
    scene = data.get("scene_analysis")
    if not isinstance(scene, dict):
        return
    preferred = [value for key, value in scene.items() if any((token in str(key).casefold() for token in ('是否',
                                                                                                          '存在',
                                                                                                          '事件',
                                                                                                          'status',
                                                                                                          'result')))]
    for value in preferred:
        if isinstance(value, (str, bool, int, float)):
            return value

    for (key, value) in scene.items():
        if str(key).strip().casefold() in {'description', '场景描述', 'image_quality'}:
            pass
        else:
            if isinstance(value, (str, bool, int, float)):
                return value


def validate_open_protocol(data):
    """校验开放式标准 JSON，返回状态和可读错误，不阻断旧格式解析。"""
    errors = []
    if not isinstance(data, dict):
        return {'valid': False, 'errors': ["顶层必须是 JSON 对象"]}
    for required in ('scene_analysis', 'objects'):
        if required not in data:
            errors.append(f"缺少必填字段：{required}")
    scene = data.get("scene_analysis")
    if scene is not None and not isinstance(scene, dict):
        errors.append("scene_analysis 必须是对象")
    elif isinstance(scene, dict):
        quality = scene.get("image_quality")
        if quality is not None and quality not in {'清晰', '模糊', '无法判断'}:
            errors.append("scene_analysis.image_quality 必须是 清晰/模糊/无法判断")
        target_value = None
        for (k, v) in scene.items():
            if k.startswith("是否存在"):
                target_value = v
                break
        if target_value is not None and target_value not in {'是', '否'}:
            errors.append("scene_analysis.是否存在…事件 必须是 是/否")
    objects = data.get("objects")
    if objects is not None and not isinstance(objects, list):
        errors.append("objects 必须是数组")
    if isinstance(objects, list):
        for (i, obj) in enumerate(objects):
            if not isinstance(obj, dict):
                errors.append(f"objects[{i}] 必须是对象")
                continue
            for required in ('labelName', 'labelValue', 'evidence', 'bbox'):
                if required not in obj:
                    errors.append(f"objects[{i}] 缺少必填字段：{required}")
            if "bbox" in obj:
                raw_box = obj.get("bbox")
                parsed = parse_bbox(raw_box)
                if parsed is None or len(parsed) < 4:
                    errors.append(f"objects[{i}].bbox 必须是 [x1,y1,x2,y2]")
                elif parsed[2] <= parsed[0] or parsed[3] <= parsed[1]:
                    errors.append(f"objects[{i}].bbox 坐标顺序无效，必须满足 x2>x1 且 y2>y1")
        if isinstance(scene, dict):
            target_value = None
            for (k, v) in scene.items():
                if k.startswith("是否存在"):
                    target_value = v
                    break
            if target_value == "否" and objects:
                errors.append("scene_analysis 判定为否时 objects 必须为空数组")
            if target_value == "是" and not objects:
                errors.append("scene_analysis 判定为是时 objects 至少需要一个目标或事件")
    if "analysis_summary" in data and not isinstance(data.get("analysis_summary"), str):
        errors.append("analysis_summary 必须是字符串")
    return {'valid': not errors, 'errors': errors}


def parse_result(text, model='', img_w=1, img_h=1, mapping=None, output_mode='fixed', status_labels=None):
    """把模型原始输出解析为固定 head 结构。parse_ok=False 时返回空结构+raw。

    mapping（自定义输出模式时提供）：
      status_field  分类结论字段路径（如 "是否异常"），设置后按原值保留，不做 abnormal/normal 归一
      objects_path  目标列表字段路径（如 "缺陷列表" 或 "result.items"）
      name_field    目标名称子字段（如 "类型"）
      bbox_field    目标框子字段（如 "位置"）
    output_mode == "custom" 时，原始解析 JSON 会完整保存在结果的 "custom" 字段中，
    供字段提取/评估按任意路径取值。
    """
    mapping = mapping or {}
    result = {'overall_status': None, 'summary': "", 'classification': {},
              'scene': {}, 'objects': [], 'parse_ok': False, 'raw': text or ""}
    block = extract_json_block(text or "")
    if not block:
        return result
    try:
        data = json.loads(block)
    except Exception:
        return result
    if not isinstance(data, dict):
        return result
    objects_path = mapping.get("objects_path")
    if objects_path:
        raw_objects = get_field_value(data, objects_path) or []
    else:
        raw_objects = _first_key(data, _OBJECTS_ALIASES) or []
    if isinstance(raw_objects, dict):
        raw_objects = [raw_objects]
    if not isinstance(raw_objects, list):
        raw_objects = []
    name_f = mapping.get("name_field")
    bbox_f = mapping.get("bbox_field")
    objects = []
    for (i, o) in enumerate(raw_objects):
        if not isinstance(o, dict):
            continue
        name = (o.get(name_f) if name_f else None) or _first_key(o, _NAME_ALIASES) or f"目标{i + 1}"
        bbox_raw = o.get(bbox_f) if bbox_f else None
        if bbox_raw is None:
            bbox_raw = _first_key(o, _BBOX_ALIASES)
        bbox = parse_bbox(bbox_raw)
        (abs_box, norm_box) = (None, None)
        if bbox and img_w > 1 and img_h > 1:
            (abs_box, norm_box) = normalize_bbox(bbox, model, img_w, img_h)
        obj = {'name': str(name),
               'category': str(o.get("category", o.get("class", ""))),
               'bbox': abs_box, 'bbox_normalized': norm_box,
               'confidence': _first_key(o, _CONF_ALIASES),
               'label_value': _first_key(o, _LABELVALUE_ALIASES),
               'description': str(_first_key(o, _DESC_ALIASES) or ""),
               'evidence': str(_first_key(o, _EVIDENCE_ALIASES) or "")}
        known = set(_NAME_ALIASES + _BBOX_ALIASES + _CONF_ALIASES + _DESC_ALIASES +
                    _LABELVALUE_ALIASES + _EVIDENCE_ALIASES +
                    ["category", "class", "bbox_normalized"])
        if name_f:
            known.add(name_f)
        if bbox_f:
            known.add(bbox_f)
        extra = {k: v for k, v in o.items() if k not in known}
        if extra:
            obj["attributes"] = extra
        objects.append(obj)
    status_f = mapping.get("status_field")
    if status_f:
        raw_status = get_field_value(data, status_f)
        status = str(raw_status).strip() if raw_status is not None else ""
        if not status:
            status = normalize_status(None, objects, status_labels)
    else:
        status = normalize_status(_first_key(data, _STATUS_ALIASES), objects, status_labels)
    scene = data.get("scene") or data.get("scene_analysis") or {}
    if not isinstance(scene, dict):
        scene = {"value": scene}
    classification = {}
    cls_raw = _first_key(data, _CLASSIFICATION_ALIASES)
    if isinstance(cls_raw, dict):
        label = _first_key(cls_raw, _CLS_LABEL_ALIASES)
        classification = {'label': str(label).strip() if (label is not None) else "",
                          'confidence': _first_key(cls_raw, _CONF_ALIASES)}
        extra = {k: v for k, v in cls_raw.items() if k not in _CLS_LABEL_ALIASES + _CONF_ALIASES}
        if extra:
            classification["extra"] = extra
    elif cls_raw is not None:
        classification = {'label': str(cls_raw).strip(), 'confidence': None}
    result.update({'overall_status': status,
                   'summary': str(data.get("summary", data.get("analysis_summary", data.get("conclusion", ""))) or ""),
                   'classification': classification, 'scene': scene, 'objects': objects,
                   'parse_ok': True, 'source_json': data})
    protocol = validate_open_protocol(data)
    result["protocol_valid"] = protocol["valid"]
    result["protocol_errors"] = protocol["errors"]
    if not status_f and _first_key(data, _STATUS_ALIASES) is None:
        status = normalize_status(_scene_status(data), objects, status_labels)
        result["overall_status"] = status
    if output_mode == "custom":
        result["custom"] = data
    return result


def get_field_value(data, path):
    """按点路径取值，支持 objects[].name 这类数组展开语法，返回单值或值列表"""
    parts = path.split(".")
    values = [data]
    for part in parts:
        next_values = []
        expand = part.endswith("[]")
        key = part[:-2] if expand else part
        for v in values:
            if isinstance(v, dict) and key in v:
                val = v[key]
                if expand and isinstance(val, list):
                    next_values.extend(val)
                    continue
                next_values.append(val)
        values = next_values
    if not values:
        return
    if len(values) == 1:
        return values[0]
    return values


def flatten_paths(obj, max_depth=4, max_items=300):
    """把任意 JSON 扁平化为可用的字段路径列表（字段提取建议用）

    列表生成 [] 展开语法；跳过 _meta / raw 等系统字段与长文本值。
    """
    paths = set()

    def walk(v: Any, prefix: str, depth: int):
        if depth > max_depth or len(paths) >= max_items:
            return
        if isinstance(v, dict):
            for k, val in v.items():
                if depth == 0 and k in ('_meta', 'raw'):
                    continue
                p = f"{prefix}.{k}" if prefix else str(k)
                if not isinstance(val, (dict, list)):
                    paths.add(p)
                walk(val, p, depth + 1)
        elif isinstance(v, list):
            p = prefix + "[]"
            if v and not isinstance(v[0], (dict, list)):
                paths.add(p)
            for item in v[:3]:
                walk(item, p, depth + 1)

    walk(obj, "", 0)
    return sorted(paths)
