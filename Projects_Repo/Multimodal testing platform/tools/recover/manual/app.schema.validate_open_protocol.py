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