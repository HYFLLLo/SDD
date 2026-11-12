def _execute_job(job, targets, stop, client, cfg):
    run_id = job["run_id"]
    try:
        try:
            remaining = iter(targets)
            verdict_counts = Counter()
            with ThreadPoolExecutor(max_workers=job["concurrency"]) as pool:
                futures = {}

                def submit_next():
                    if stop.is_set():
                        return False
                    try:
                        rel, repeat = next(remaining)
                    except StopIteration:
                        return False
                    future = pool.submit(
                        judge_one, run_id, rel, repeat,
                        job.get("model") or None,
                        job.get("profile_name") or "",
                        job.get("site") or None,
                        client, cfg,
                    )
                    futures[future] = (rel, repeat)
                    job["active_workers"] = len(futures)
                    job["current"] = {"image": rel, "repeat": repeat, "active": len(futures)}
                    job["workers"] = [{"image": rel, "repeat": rep} for rel, rep in futures.values()]
                    job["heartbeat"] = time.time()
                    _save_job(job)
                    return True

                for _ in range(job["concurrency"]):
                    if not submit_next():
                        break
                while futures:
                    completed, _ = wait(futures, return_when=FIRST_COMPLETED)
                    for future in completed:
                        rel, repeat = futures.pop(future)
                        try:
                            result = future.result()
                            job["done"] += 1
                        except Exception as exc:
                            job["failed"] += 1
                            job["errors"].append({"image": rel, "repeat": repeat, "error": str(exc)})
                            job["errors"] = job["errors"][-100:]
                        else:
                            v = result.get("verdict") if isinstance(result, dict) else None
                            if v:
                                verdict_counts[v] += 1
                        job["pending"] = max(0, job.get("total", 0) - job.get("done", 0) - job.get("failed", 0))
                        job["active_workers"] = len(futures)
                        job["heartbeat"] = time.time()
                        job["workers"] = [{"image": rel, "repeat": rep} for rel, rep in futures.values()]
                        job["current"] = job["workers"][0] if job["workers"] else None
                        job["status_counts"] = dict(verdict_counts)
                        _save_job(job)
                        submit_next()
                    if stop.is_set() and not futures:
                        break
            job["status"] = "paused" if stop.is_set() else ("done" if not job["failed"] else "done_with_errors")
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
    finally:
        with _job_lock:
            current = _jobs.get(run_id)
            if current is not None and current.get("stop") is not stop:
                return
        if run_id in _deleted:
            with _job_lock:
                current = _jobs.get(run_id)
                if current is not None and current.get("stop") is stop:
                    _jobs.pop(run_id, None)
                _deleted.discard(run_id)
            return
        job["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        job["active_workers"] = 0
        job["current"] = None
        job["workers"] = []
        job["pending"] = max(0, job.get("total", 0) - job.get("done", 0) - job.get("failed", 0))
        counts = Counter(item.get("verdict") for item in list_judgments(run_id) if item.get("verdict"))
        job["counts"] = dict(counts)
        job["status_counts"] = dict(counts)
        eligible = _eligible_targets(run_id)
        job["eligible"] = eligible
        judged = len(list_judgments(run_id))
        job["coverage"] = judged / eligible if eligible else 1.0
        job["judge_coverage_threshold"] = job.get("coverage_threshold", 1.0)
        if job.get("total", 0) == 0 and job.get("skipped", 0) > 0 and not job.get("auto_forced"):
            if not job.get("note"):
                job["note"] = '所有样本已有裁判结果，已跳过。如需重新裁判请勾选"强制重新裁判"。'
        elif job.get("auto_forced") and not job.get("note"):
            job["note"] = "检测到裁判模型变更，已自动重新裁判"
        if client is not None:
            job["key_stats"] = client.key_stats(site=job.get("site") or None)
        if job.get("status") in {"done", "done_with_errors"} and job["coverage"] < job.get("coverage_threshold", 1.0):
            job["status"] = "done_with_errors"
            job["error"] = "裁判覆盖不足：{:.0%}，请继续任务或补充人工审核".format(job["coverage"])
        _save_job(job)
        with _job_lock:
            current = _jobs.get(run_id)
            if current is not None and current.get("stop") is stop:
                _jobs.pop(run_id, None)

