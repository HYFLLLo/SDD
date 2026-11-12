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