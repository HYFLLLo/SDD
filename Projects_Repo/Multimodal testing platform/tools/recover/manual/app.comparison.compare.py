def compare(result, review, iou_threshold):
    """仅依据结构化结果和人工期望生成客观 diff，不调用模型。"""
    expected_status_raw = review.get("expected_status")
    expected_status = _text(expected_status_raw) or None
    predicted_status = _text(result.get("overall_status")) or None
    status_match = None if expected_status is None else predicted_status == expected_status
    expected_all = [x for x in review.get("expected_objects") or [] if isinstance(x, dict)]
    expected = [x for x in expected_all if not _is_context(x)]
    predicted_all = [x for x in result.get("objects") or [] if isinstance(x, dict)]
    predicted = [x for x in predicted_all if not _is_context(x)]
    matched, unmatched_pred = _match_objects(expected, predicted, iou_threshold)
    unmatched_exp = max(0, len(expected) - len(matched))
    object_match = len(expected) == len(predicted) and not unmatched_exp and not unmatched_pred
    label_matches = [m for m in matched if m["label_value_match"] is not False]
    label_match = len(matched) == len(expected) and len(label_matches) == len(matched)
    bbox_match = len(matched) == len(expected) and all((m["iou"] >= iou_threshold for m in matched))
    parse_valid = bool(result.get("parse_ok")) and predicted_status != "error"
    result_protocol_valid = result.get("protocol_valid")
    if result_protocol_valid is False:
        source_json = result.get("source_json")
        if isinstance(source_json, str):
            try:
                source_json = json.loads(source_json)
            except (json.JSONDecodeError, TypeError):
                source_json = None
        if isinstance(source_json, dict) and source_json.get("objects"):
            try:
                from app.schema import validate_open_protocol
                revalidation = validate_open_protocol(source_json)
                protocol_valid = bool(revalidation.get("valid"))
            except Exception:
                protocol_valid = False
        else:
            protocol_valid = False
    else:
        protocol_valid = parse_valid and isinstance(result.get("objects"), list)
    human_verdict = _text(review.get("verdict")) or None
    human_verdict_normalized = None
    if human_verdict in {'部分正确', '正确', '误报', '漏报'}:
        human_verdict_normalized = human_verdict
    elif human_verdict in {'无法判断', '无法确定'}:
        human_verdict_normalized = "无法判断"
    deterministic_verdict = None
    if not (parse_valid and protocol_valid):
        deterministic_verdict = None
    elif expected_status is not None or expected or predicted:
        if status_match is False:
            if not expected and predicted:
                deterministic_verdict = "误报"
            elif expected and not predicted:
                deterministic_verdict = "漏报"
            else:
                deterministic_verdict = "部分正确"
        elif not object_match:
            if not expected and predicted:
                deterministic_verdict = "误报"
            elif expected and not predicted:
                deterministic_verdict = "漏报"
            elif not matched:
                deterministic_verdict = "部分正确"
            else:
                deterministic_verdict = "部分正确"
        elif not (label_match and bbox_match):
            deterministic_verdict = "部分正确"
        else:
            deterministic_verdict = "正确"
    if deterministic_verdict and human_verdict_normalized and human_verdict_normalized != "无法判断":
        if deterministic_verdict != human_verdict_normalized:
            if human_verdict_normalized == "正确" and deterministic_verdict != "正确":
                deterministic_verdict = "部分正确"
            elif deterministic_verdict == "正确" and human_verdict_normalized != "正确":
                deterministic_verdict = "部分正确"
            elif deterministic_verdict not in ('正确',) and human_verdict_normalized not in ('正确',):
                if deterministic_verdict == "部分正确":
                    deterministic_verdict = human_verdict_normalized
    return {'expected_status': expected_status,
            'predicted_status': predicted_status,
            'status_match': status_match,
            'expected_object_count': len(expected),
            'predicted_object_count': len(predicted),
            'context_object_count': (len(expected_all)) - (len(expected)),
            'predicted_context_object_count': (len(predicted_all)) - (len(predicted)),
            'object_match': object_match, 'label_match': label_match, 'bbox_match': bbox_match,
            'evidence_match': None, 'parse_valid': parse_valid, 'protocol_valid': protocol_valid,
            'iou_threshold': iou_threshold, 'matches': matched,
            'unmatched_expected': unmatched_exp,
            'unmatched_predicted': len(unmatched_pred),
            'deterministic_verdict': deterministic_verdict,
            'comparison_confidence': "high" if (expected_status is not None) or expected else "low",
            'human_verdict': human_verdict_normalized,
            'has_ground_truth': bool(expected_status is not None or expected_all)}