def _execute(run_id, stop):
    try:
        try:
            run = _load_run(run_id)
            run["status"] = "running"
            _save_run(run)

            cfg = load_config()
            client = MaaSClient(cfg)
            if not client.has_keys():
                run["status"] = "failed"
                run["error"] = "未配置 API Key"
                _save_run(run)
                return
            images = run.get("images_snapshot") or datasets.scan_images(run["dataset"], split=run.get("dataset_split"))
            tasks = [(img, r) for img in images for r in range(1, run["repeat"] + 1)]
            with ThreadPoolExecutor(max_workers=max(1, run["concurrency"])) as pool:
                futures = []
                for img, rep in tasks:
                    if stop.is_set():
                        break
                    if _result_reusable(_existing_result_path(run_id, img["rel"], rep)):
                        continue
                    futures.append(pool.submit(_process_one, run_id, run, client, img, rep, stop))
                for f in futures:
                    if stop.is_set():
                        break
                    try:
                        ok = f.result()
                    except Exception:
                        ok = False
                    with _run_lock:
                        run = _load_run(run_id)
                        if ok:
                            run["done"] += 1
                        else:
                            run["failed"] += 1
                        _save_run(run)
            run = _load_run(run_id)
            run["status"] = "stopped" if stop.is_set() else "done"
            run["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _reconcile_counts(run)
            _save_run(run)
        except Exception as e:
            try:
                run = _load_run(run_id)
                run["status"] = "failed"
                run["error"] = str(e)
                _save_run(run)
            except Exception:
                pass
    finally:
        with _run_lock:
            _runners.pop(run_id, None)
