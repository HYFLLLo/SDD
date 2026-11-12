def compare(eval_ids):
    """多条评估记录横评（通常用于同任务不同提示词版本对比）"""
    rows = []
    for eid in eval_ids:
        try:
            e = get_eval(eid)
        except Exception:
            continue
        row = {'id': e["id"], 'name': e["name"], 'kind': e["kind"],
               'prompt': f'{e["prompt_name"]} V{e["prompt_version"]}',
               'prompt_name': e["prompt_name"],
               'prompt_version': e["prompt_version"], 'model': e["model"],
               'created': e["created"], 'image_count': e["image_count"],
               'metrics': e["metrics"]}
        rows.append(row)
    return {"items": rows}