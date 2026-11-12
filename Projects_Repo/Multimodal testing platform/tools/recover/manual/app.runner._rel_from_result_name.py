def _rel_from_result_name(filename):
    """results 目录里的结果文件名 → 原始相对图片路径。"""
    name = os.path.splitext(filename)[0]
    if "__r" not in name:
        return None
    rel = name.rsplit("__r", 1)[0]
    return rel or None
