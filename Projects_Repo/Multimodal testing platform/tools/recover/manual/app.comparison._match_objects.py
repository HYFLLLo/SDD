def _match_objects(expected, predicted, iou_threshold):
    unmatched = set(range(len(predicted)))
    matched = []
    for exp in expected:
        name = _norm_name(_expected_name(exp))
        candidates = []
        for idx in unmatched:
            pred = predicted[idx]
            pred_name = _norm_name(_predicted_name(pred))
            if name and pred_name and name != pred_name:
                continue
            overlap = iou(exp.get("bbox"), pred.get("bbox"))
            candidates.append((overlap, idx))
        if candidates:
            overlap, idx = max(candidates)
            if not exp.get("bbox") or overlap >= iou_threshold:
                unmatched.remove(idx)
                expected_value = _text(exp.get("labelValue"))
                pred_value = _text(predicted[idx].get("label_value") or predicted[idx].get("labelValue"))
                matched.append({'expected_index': len(matched), 'predicted_index': idx,
                                'iou': overlap,
                                'label_value_match': None if not expected_value else (expected_value == pred_value)})
    return (matched, sorted(unmatched))