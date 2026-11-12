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