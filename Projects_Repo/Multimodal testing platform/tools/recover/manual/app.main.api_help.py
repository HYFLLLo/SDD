def api_help():
    """应用内帮助：返回操作指南全文。

    exe 场景读打包进 _MEIPASS 的资源（build_exe.py 通过 --add-data 内置），
    开发场景读项目根目录的 操作指南.txt。
    """
    import sys
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(sys._MEIPASS, "操作指南.txt"))
    candidates.append(os.path.join(BASE_DIR, "操作指南.txt"))
    for p in candidates:
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return {"text": f.read().lstrip("\ufeff")}
    return {"text": "未找到操作指南文件（操作指南.txt）。"}
