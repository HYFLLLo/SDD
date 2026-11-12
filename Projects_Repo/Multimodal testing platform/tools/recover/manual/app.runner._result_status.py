def _result_status(path):
    """读取结果文件的统计口径，返回 (reusable, parse_failed)。

    reusable：接口调用成功（断点续跑可跳过）
    parse_failed：接口成功但 JSON 解析失败。这类结果不会自动重试，
    但必须与 API 失败分开计数，否则界面会出现“失败 0 却有图没结论”。
    """
    if not os.path.exists(path):
        return False, False
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return False, False
    if (d.get("_meta") or {}).get("error"):
        return False, False
    return True, d.get("parse_ok") is False
