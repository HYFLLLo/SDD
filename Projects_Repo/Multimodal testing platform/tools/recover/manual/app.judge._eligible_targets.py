def _eligible_targets(run_id):
    """只统计有人工审核且模型结果有效的样本，作为裁判覆盖率分母。

    解析失败（parse_ok=False）的样本模型没有给出可比较结论，裁判无从判定，
    因此不进入分母，否则覆盖率永远到不了 100%。
    """
    reviewed = {(
     r.get("image"), int(r.get("repeat") or 1)) for r in reviews.list_reviews(run_id)}
    total = 0
    for image in runner.list_run_images(run_id):
        for item in image.get("repeats", []):
            if item.get("exists"):
                if not item.get("error"):
                    if item.get("parse_ok") is not False:
                        if (image["rel"], int(item["repeat"])) in reviewed:
                            total += 1
    return total


def _parse_failed_targets(run_id):
    """统计已审核但因解析失败被排除出裁判范围的样本数（用于界面解释分母）。"""
    reviewed = {(
     r.get("image"), int(r.get("repeat") or 1)) for r in reviews.list_reviews(run_id)}
    total = 0
    for image in runner.list_run_images(run_id):
        for item in image.get("repeats", []):
            if not item.get("exists") or item.get("error"):
                continue
            if item.get("parse_ok") is False:
                if (image["rel"], int(item["repeat"])) in reviewed:
                    total += 1
    return total


def _safe_parse_failed_targets(run_id):
    """界面展示用的容错包装：统计失败不影响裁判启动。"""
    try:
        return _parse_failed_targets(run_id)
    except Exception:
        return 0
