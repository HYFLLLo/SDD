def reparse_results(run_id, backup=True):
    """用当前解析器重解析「接口成功但解析失败」的历史结果。

    只处理 _meta 无 error 且仍有 raw 的样本：这类是解析器容错不足导致的
    假失败，模型其实给了结论。原始 raw 原样保留，改动前的 JSON 先备份，
    便于核对与回退。
    """
    run = _load_run(run_id)
    st = run.get("prompt_settings") or {}
    base = _run_dir(run_id)
    results_dir = os.path.join(base, "results")
    backup_dir = None
    repaired = failed = 0
    details = []
    for dirpath, _, files in os.walk(results_dir):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, "r", encoding="utf-8") as f:
                old = json.load(f)
            if old.get("parse_ok") is not False:
                continue
            if (old.get("_meta") or {}).get("error"):
                failed += 1
                continue
            raw = old.get("raw") or ""
            rel = _rel_from_result_name(fn)
            if not raw or not rel:
                failed += 1
                continue
            rel_dir = os.path.relpath(dirpath, results_dir)
            if rel_dir != ".":
                rel = os.path.join(rel_dir, rel)
            try:
                (w, h) = get_image_size(image_file(run_id, rel))
            except Exception:
                (w, h) = (1, 1)
            fresh = parse_result(raw, model=run.get("model", ""), img_w=w, img_h=h,
                                 mapping=(st.get("map") or None),
                                 output_mode=st.get("output_mode", "fixed"),
                                 status_labels=st.get("status_labels"))
            if not fresh.get("parse_ok"):
                failed += 1
                continue
            if backup:
                if backup_dir is None:
                    backup_dir = os.path.join(base, "results_backup_" + time.strftime("%Y%m%d-%H%M%S"))
                target = os.path.join(backup_dir, os.path.relpath(path, results_dir))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                if not os.path.exists(target):
                    shutil.copy2(path, target)
            meta = dict(old.get("_meta") or {})
            meta["parse_repaired"] = time.strftime("%Y-%m-%d %H:%M:%S")
            fresh["_meta"] = meta
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(fresh, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            repaired += 1
            details.append({"image": rel, "objects": len(fresh.get("objects") or [])})
    if repaired:
        try:
            with open(_run_json_path(run_id), "r", encoding="utf-8") as f:
                current = json.load(f)
            _reconcile_counts(current)
            _save_run(current)
        except Exception:
            pass
    return {"run_id": run_id, "repaired": repaired, "still_failed": failed,
            "backup": backup_dir or "", "items": details}
