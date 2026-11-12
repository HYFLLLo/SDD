def get_result(run_id, rel, repeat):
    for name in _result_candidates(rel, repeat):
        p = safe_path(_run_dir(run_id), "results", name)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise ValueError("结果不存在")
