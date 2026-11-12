def compute():
    out = []
    for eid in sorted((os.listdir(root)), reverse=True):
        p = os.path.join(root, eid, "eval.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    out.append(json.load(f))
            except Exception:
                continue
    return out