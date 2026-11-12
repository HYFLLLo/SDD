def run_eval(params):
    """params: {run_id, truth_task, field(默认overall_status),
    set_field(多标签任务的预测集合字段，默认 objects[].name，可填 custom.xxx[].yyy), name(可选)}"""
    run_id = params["run_id"]
    task_id = params["truth_task"]
    field = params.get("field") or "overall_status"
    set_field = params.get("set_field") or "objects[].name"
    run = _load_run(run_id)
    task = truth.get_task(task_id)
    label_map = truth.truth_label_map(task_id)
    if not label_map:
        raise ValueError("真值任务还没有已标注图片")
    details = []
    for rel_img, t_labels in sorted(label_map.items()):
        preds_raw = []
        pred_sets = []
        for r in range(1, run["repeat"] + 1):
            try:
                res = get_result(run_id, rel_img, r)
            except Exception:
                continue
            if not res.get("parse_ok"):
                continue
            if task["kind"] == "single":
                v = get_field_value(res, field)
                preds_raw.append(str(v) if v is not None else None)
            else:
                names = get_field_value(res, set_field) or []
                if not isinstance(names, list):
                    names = [names]
                pred_sets.append({str(n).strip() for n in names if n is not None and str(n).strip()})
        if task["kind"] == "single":
            pred = _vote(preds_raw)
            ok = pred is not None and pred in t_labels
            details.append({'image': rel_img, 'truth': t_labels, 'pred': pred,
                            'pred_all': preds_raw, 'correct': ok})
        else:
            pred_set = _set_vote(pred_sets)
            t_set = set(t_labels)
            details.append({'image': rel_img,
                            'truth': sorted(t_set), 'pred': sorted(pred_set),
                            'pred_all': [sorted(s) for s in pred_sets],
                            'correct': pred_set == t_set,
                            'tp': sorted(pred_set & t_set),
                            'fp': sorted(pred_set - t_set), 'fn': sorted(t_set - pred_set)})
    metrics = _metrics_single(task["labels"], details) if task["kind"] == "single" else _metrics_multi(task["labels"], details)
    eval_id = time.strftime("%Y%m%d-%H%M%S") + f'_{run["prompt_name"]}-V{run["prompt_version"]}'
    base, i = eval_id, 2
    while os.path.exists(_eval_dir(eval_id)):
        eval_id = f"{base}-{i}"
        i += 1
    record = {'id': eval_id,
              'name': params.get("name") or eval_id,
              'created': (time.strftime)("%Y-%m-%d %H:%M:%S"),
              'run_id': run_id, 'truth_task': task_id,
              'field': field,
              'set_field': set_field if (task["kind"] == "multi") else None,
              'kind': task["kind"],
              'prompt_name': run["prompt_name"],
              'prompt_version': run["prompt_version"],
              'model': run["model"], 'dataset': run["dataset"],
              'image_count': len(details), 'metrics': metrics, 'details': details}
    os.makedirs((_eval_dir(eval_id)), exist_ok=True)
    target = os.path.join(_eval_dir(eval_id), "eval.json")
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    os.replace(tmp, target)
    prompts.attach_metrics(run["prompt_name"], run["prompt_version"], run_id, metrics)
    return record