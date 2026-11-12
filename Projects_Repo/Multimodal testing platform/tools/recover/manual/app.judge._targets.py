def _targets(run_id, force=False):
    targets = []
    skipped = 0
    for image in runner.list_run_images(run_id):
        for item in image.get("repeats", []):
            repeat = int(item["repeat"])
            if not item.get("exists") or item.get("error"):
                continue
            if item.get("parse_ok") is False:
                continue
            if not reviews.get_review(run_id, image["rel"], repeat):
                continue
            if not force and get_judgment(run_id, image["rel"], repeat):
                skipped += 1
                continue
            targets.append((image["rel"], repeat))
    return (targets, skipped)
