@app.get("/api/extract/fields")
@app.get('/api/extract/fields')
def api_extract_fields(run_id):
    """扫描部分结果，把 JSON 扁平化为可用字段路径建议（含 custom 原始结构）"""
    import json as _json
    from .schema import flatten_paths
    fields = set()
    base = os.path.join(runner._run_dir(run_id), "results")
    count = 0
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".json"):
                pass
            else:
                try:
                    with open((os.path.join(dirpath, fn)), "r", encoding="utf-8") as f:
                        d = _json.load(f)
                except Exception:
                    continue

                else:
                    fields.update(flatten_paths(d))
                    count += 1
                    if count >= 20:
                        break

        if count >= 20:
            break
    return {"fields": (sorted(fields))}
