def safe_path(base, *parts):
    """拼接路径并校验不越出 base，防止路径穿越"""
    p = os.path.realpath((os.path.join)(base, *parts))
    if not p.startswith(os.path.realpath(base) + os.sep):
        if p != os.path.realpath(base):
            raise ValueError("非法路径")
    return p