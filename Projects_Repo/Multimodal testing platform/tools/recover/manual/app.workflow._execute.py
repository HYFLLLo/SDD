def _execute(job_id, stop):
    try:
        try:
            state = get_job(job_id)
            while len(state["rounds"]) < state["max_rounds"]:
                if stop.is_set():
                    state["status"] = "paused"
                    state["stop_reason"] = "用户暂停"
                    _save(state)
                    return
                current_run = state["current_run_id"]
                pending = state.get("pending_round")
                if pending and pending.get("run_id") == current_run:
                    current_run_state = runner.get_run(current_run)
                    processed = current_run_state.get("done", 0) + current_run_state.get("failed", 0)
                    if current_run_state.get("status") != "done" or processed < current_run_state.get("total", 0):
                        state["phase"] = "继续候选版本运行"
                        _save(state)
                        completed_run = _wait_run(current_run, stop, state=state)
                        if stop.is_set():
                            continue
                        if completed_run.get("done", 0) == 0:
                            raise ValueError("候选版本没有产生有效结果")
                        if not reviews.list_reviews(current_run):
                            state["phase"] = "复用人工基线"
                            _save(state)
                            reuse = reviews.reuse_baseline(state["baseline_run_id"], current_run, overwrite=False)
                            if reuse["copied"] == 0 and not reviews.list_reviews(current_run):
                                state["status"] = "waiting_for_review"
                                state["stop_reason"] = "候选运行与基线没有重合样本，请人工审核候选运行后继续"
                                _save(state)
                                return
                        state["phase"] = "补齐当前版本裁判"
                        _save(state)
                        if not reviews.list_reviews(current_run):
                            state["status"] = "waiting_for_review"
                            state["stop_reason"] = "当前运行没有人工审核；请先审核，或从已有基线复用审核"
                            _save(state)
                            return
                        _wait_judge(
                            current_run,
                            state["judge_model"],
                            state["judge_concurrency"],
                            stop,
                            state.get("judge_profile") or "",
                            state.get("judge_site") or "",
                            state=state,
                            coverage_threshold=state["judge_coverage_threshold"],
                        )
                        if stop.is_set():
                            continue
                        current_job = judge.get_job(current_run)
                        current_coverage = float(current_job.get("coverage") or 0.0)
                        if current_job.get("status") == "paused":
                            state["status"] = "paused"
                            state["stop_reason"] = "裁判任务已暂停，可继续执行"
                            _save(state)
                            return
                        if current_job.get("status") != "done" or current_coverage < state["judge_coverage_threshold"]:
                            state["status"] = "waiting_for_judge"
                            state["stop_reason"] = "裁判未完成或覆盖率不足，未进入优化"
                            _save(state)
                            return
                if not state.get("rounds"):
                    (is_model_dom, model_detail) = _is_model_dominant(current_run)
                    if is_model_dom:
                        state["status"] = "stable"
                        state["stop_reason"] = "裁判报告主要指向模型能力不足（{}）。提示词可优化空间有限，建议更换更强的分析模型后重试。".format(model_detail)
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                current_metrics = _quality(current_run)
                state["thresholds"]["judge_coverage"] = state["judge_coverage_threshold"]
                prompts.attach_metrics(state["prompt_name"], state["current_version"], current_run, current_metrics)
                if state.get("pending_round"):
                    if _finish_pending_round(state, current_metrics):
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                _save(state)
                if len(state["rounds"]) >= state["max_rounds"]:
                    state["status"] = "done"
                    state["stop_reason"] = "达到最大迭代轮数"
                    state["phase"] = "完成"
                    state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    _save(state)
                    return
                else:
                    if state["best_score"] is None and current_metrics.get("quality_score") is not None:
                        state["best_score"] = current_metrics["quality_score"]
                        state["best_version"] = state["current_version"]
                        state["best_run_id"] = current_run
                        state["best_metrics"] = current_metrics
                        state["baseline_metrics"] = current_metrics
                        _save(state)
                state["thresholds"]["judge_coverage"] = state["judge_coverage_threshold"]
                if not state.get("rounds") and _meets_thresholds(current_metrics, state["thresholds"]):
                    state["status"] = "stable"
                    state["stop_reason"] = "当前版本已达到稳定阈值且无高严重度回归"
                    state["phase"] = "完成"
                    state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    _save(state)
                    return
                state["phase"] = "生成并保存候选版本"
                _save(state)
                if stop.is_set():
                    continue
                state["optimizer_started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                state["optimizer_sub_phase"] = "正在调用优化器模型 {}…".format(
                    state.get("optimizer_model") or state["model"]
                )
                _save(state)
                candidate = prompt_ai.optimize(
                    state["prompt_name"],
                    state["current_version"],
                    current_run,
                    state.get("optimizer_model") or state["model"],
                    50,
                    state.get("optimizer_profile") or "",
                    site=state.get("optimizer_site") or state.get("site") or None,
                    trajectory=state.get("rounds", []),
                )
                state["optimizer_sub_phase"] = ""
                state["optimizer_started_at"] = ""
                _save(state)
                version = prompt_ai.save_candidate(candidate["id"], branch=f"auto/{job_id}")
                state["phase"] = "运行候选版本"
                state["candidate_record_id"] = candidate["id"]
                source_version = state["current_version"]
                source_run_id = state["current_run_id"]
                _save(state)
                run = runner.create_run({
                    "dataset": state["dataset"],
                    "split": state.get("split"),
                    "prompt_name": state["prompt_name"],
                    "prompt_version": version["version"],
                    "model": state["model"],
                    "repeat": 1,
                    "concurrency": state["analysis_concurrency"],
                    "site": state.get("site") or "",
                })
                state["current_run_id"] = run["id"]
                state["current_version"] = version["version"]
                state["pending_round"] = {
                    "version": version["version"],
                    "run_id": run["id"],
                    "optimization_id": candidate["id"],
                    "source_version": source_version,
                    "source_run_id": source_run_id,
                    "candidate_index": 1,
                    "candidate_count_requested": state.get("candidates_per_round", 1),
                    "candidate_count_executed": 1,
                    "candidate_execution_note": "当前版本每轮实际执行 1 个候选；多候选配置已保留，尚未启用并行候选搜索",
                }
                _save(state)
                quick_test_size = state.get("quick_test_size") or 0
                if quick_test_size > 0:
                    qt_run = runner.get_run(run["id"])
                    if not qt_run.get("is_active") and qt_run.get("status") != "running":
                        runner.start_run(run["id"])
                    qt_ready = False
                    while not stop.is_set():
                        qt_run = runner.get_run(run["id"])
                        qt_done = qt_run.get("done", 0) + qt_run.get("failed", 0)
                        qt_total = qt_run.get("total", 0)
                        state["progress"] = "快测进度 {}/{}".format(qt_done, qt_total)
                        try:
                            _save(state)
                        except Exception:
                            pass
                        if qt_done >= quick_test_size:
                            qt_ready = True
                            break
                        if not qt_run.get("is_active") and qt_run.get("status") != "running":
                            qt_ready = True
                            break
                        time.sleep(0.5)
                    if qt_ready and not stop.is_set():
                        qt_stability = stats.run_stability(run["id"])
                        qt_parse_rate = qt_stability.get("parse_rate")
                        if qt_parse_rate is not None and qt_parse_rate < 0.3:
                            runner.stop_run(run["id"])
                            state["phase"] = "快测拒绝：解析率 {:.0%}，跳过全量运行".format(qt_parse_rate)
                            _save(state)
                            reject_metrics = _quality(run["id"])
                            prompts.attach_metrics(state["prompt_name"], version["version"], run["id"], reject_metrics)
                            state["pending_round"] = {
                                "version": version["version"],
                                "run_id": run["id"],
                                "optimization_id": candidate["id"],
                                "source_version": source_version,
                                "source_run_id": source_run_id,
                                "candidate_index": 1,
                                "candidate_count_requested": state.get("candidates_per_round", 1),
                                "candidate_count_executed": 1,
                                "candidate_execution_note": "quick test rejected",
                            }
                            _finish_pending_round(state, reject_metrics)
                            _save(state)
                            if state.get("status") in ("stable", "done"):
                                state["phase"] = "完成"
                                state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                                _save(state)
                                return
                            continue
                completed_run = _wait_run(run["id"], stop, state=state)
                if stop.is_set():
                    continue
                if completed_run.get("done", 0) == 0:
                    raise ValueError("候选版本没有产生有效结果")
                state["phase"] = "复用人工基线"
                _save(state)
                reuse = reviews.reuse_baseline(state["baseline_run_id"], run["id"], overwrite=False)
                if reuse["copied"] == 0 and not reviews.list_reviews(run["id"]):
                    state["status"] = "waiting_for_review"
                    state["stop_reason"] = "候选运行与基线没有重合样本，请人工审核候选运行后继续"
                    _save(state)
                    return
                candidate_stability = stats.run_stability(run["id"])
                candidate_parse_rate = candidate_stability.get("parse_rate")
                baseline_metrics = state.get("baseline_metrics") or {}
                baseline_parse_rate = baseline_metrics.get("parse_rate")
                quick_reject = False
                if candidate_parse_rate is not None and candidate_parse_rate < 0.3:
                    quick_reject = True
                    quick_reason = "候选版本解析率仅为 {:.0%}，跳过裁判直接拒绝".format(candidate_parse_rate)
                elif candidate_parse_rate is not None and baseline_parse_rate is not None and candidate_parse_rate < baseline_parse_rate * 0.5:
                    quick_reject = True
                    quick_reason = "候选版本解析率仅为基线的 {:.0%}，跳过裁判直接拒绝".format(
                        candidate_parse_rate / baseline_parse_rate
                    )
                if quick_reject:
                    state["phase"] = quick_reason
                    _save(state)
                    reject_metrics = _quality(run["id"])
                    prompts.attach_metrics(state["prompt_name"], version["version"], run["id"], reject_metrics)
                    state["pending_round"] = {
                        "version": version["version"],
                        "run_id": run["id"],
                        "optimization_id": candidate["id"],
                        "source_version": source_version,
                        "source_run_id": source_run_id,
                        "candidate_index": 1,
                        "candidate_count_requested": state.get("candidates_per_round", 1),
                        "candidate_count_executed": 1,
                        "candidate_execution_note": "quick rejected",
                    }
                    _finish_pending_round(state, reject_metrics)
                    _save(state)
                    if state.get("status") in ("stable", "done"):
                        state["phase"] = "完成"
                        state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        _save(state)
                        return
                    continue
                state["phase"] = "裁判候选版本"
                _save(state)
                _wait_judge(
                    run["id"],
                    state["judge_model"],
                    state["judge_concurrency"],
                    stop,
                    state.get("judge_profile") or "",
                    state.get("judge_site") or "",
                    state=state,
                    coverage_threshold=state["judge_coverage_threshold"],
                )
                if stop.is_set():
                    continue
                metrics = _quality(run["id"])
                prompts.attach_metrics(state["prompt_name"], version["version"], run["id"], metrics)
                score = metrics.get("quality_score")
                if score is not None and score == 0.0 and len(state.get("rounds", [])) >= 1:
                    state["status"] = "stable"
                    state["stop_reason"] = "候选版本质量评分为 0，优化方向可能有问题。建议：1) 检查裁判归因是否准确；2) 手动优化提示词后重试；3) 更换分析模型或裁判模型。"
                    state["phase"] = "完成"
                    state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    _save(state)
                    return
                finished = _finish_pending_round(state, metrics)
                _save(state)
                if finished:
                    continue
            state["status"] = "done"
            state["stop_reason"] = "达到最大迭代轮数"
            state["phase"] = "完成"
            state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save(state)
        except JudgeIncompleteError as exc:
            try:
                state = get_job(job_id)
                state["status"] = "waiting_for_judge"
                state["stop_reason"] = str(exc)
                state["phase"] = "等待裁判补齐"
                state["error"] = ""
                _save(state)
            except Exception:
                pass
        except OptimizationError as exc:
            try:
                state = get_job(job_id)
                state["status"] = "stable"
                state["stop_reason"] = str(exc)
                state["phase"] = "完成"
                state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                state["optimizer_sub_phase"] = ""
                state["optimizer_started_at"] = ""
                _save(state)
            except Exception:
                pass
        except Exception as exc:
            try:
                state = get_job(job_id)
                state["status"] = "failed"
                err_msg = str(exc)
                if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
                    err_msg = "优化器模型调用超时。建议：1) 在配置页增大 optimizer_timeout（当前 {} 秒）；2) 更换更快的优化器模型；3) 减少 optimizer_max_tokens。".format(
                        state.get("optimizer_timeout", 600)
                    )
                state["error"] = err_msg
                state["phase"] = "失败"
                state["optimizer_sub_phase"] = ""
                state["optimizer_started_at"] = ""
                _save(state)
            except Exception:
                pass
    finally:
        with _lock:
            current = _active.get(job_id)
            if current is not None and current.get("stop") is stop:
                _active.pop(job_id, None)
