def parse_result(text, model, img_w, img_h, mapping, output_mode, status_labels):
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