def _reconcile_counts(run):
    """按磁盘上的结果文件重算 done/failed，避免停止-恢复后计数漂移。"""
    base = os.path.join(_run_dir(run["id"]), "results")
    done = failed = parse_failed = 0
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            p = os.path.join(dirpath, fn)
            ok, broken = _result_status(p)
            if ok:
                done += 1
            else:
                failed += 1
            if broken:
                parse_failed += 1
    run["done"] = done
    run["failed"] = failed
    run["parse_failed"] = parse_failed
