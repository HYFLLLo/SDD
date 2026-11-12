from app.comparison import compare, iou


def _result(status="abnormal", objects=None, parse_ok=True, protocol_valid=True):
    return {
        "overall_status": status,
        "parse_ok": parse_ok,
        "protocol_valid": protocol_valid,
        "objects": objects or [],
    }


def _review(status="abnormal", objects=None, **extra):
    data = {"expected_status": status, "expected_objects": objects or []}
    data.update(extra)
    return data


def test_iou_basic_and_invalid():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert iou([0, 0, 10, 10], [0, 0, 5, 10]) == 0.5
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert iou(None, [0, 0, 1, 1]) == 0.0
    assert iou([1, 2, 3], [0, 0, 1, 1]) == 0.0


def test_iou_normalizes_reversed_boxes():
    assert iou([10, 10, 0, 0], [0, 0, 10, 10]) == 1.0


def test_compare_exact_match():
    r = _result(objects=[{"name": "car", "bbox": [0, 0, 10, 10]}])
    rev = _review(objects=[{"labelName": "car", "bbox": [0, 0, 10, 10]}])
    c = compare(r, rev, 0.5)
    assert c["status_match"] is True
    assert c["object_match"] is True
    assert c["label_match"] is True
    assert c["bbox_match"] is True
    assert c["deterministic_verdict"] == "正确"
    assert c["has_ground_truth"] is True
    assert c["comparison_confidence"] == "high"


def test_compare_iou_threshold_boundary_is_inclusive():
    r = _result(objects=[{"name": "car", "bbox": [0, 0, 10, 10]}])
    rev = _review(objects=[{"labelName": "car", "bbox": [0, 0, 5, 10]}])
    assert compare(r, rev, 0.5)["bbox_match"] is True
    assert compare(r, rev, 0.6)["bbox_match"] is False


def test_compare_false_positive_and_false_negative():
    fp = compare(
        _result(objects=[{"name": "car", "bbox": [0, 0, 10, 10]}]),
        _review("normal", []),
        0.5,
    )
    assert fp["deterministic_verdict"] == "误报"
    assert fp["unmatched_predicted"] == 1

    fn = compare(_result("normal", []), _review("abnormal", [{"labelName": "car", "bbox": [0, 0, 10, 10]}]), 0.5)
    assert fn["deterministic_verdict"] == "漏报"
    assert fn["unmatched_expected"] == 1


def test_compare_context_objects_are_excluded_from_counts():
    r = _result(objects=[
        {"name": "car", "bbox": [0, 0, 10, 10]},
        {"name": "辅助框", "bbox": [0, 0, 5, 5]},
    ])
    rev = _review(objects=[
        {"labelName": "car", "bbox": [0, 0, 10, 10]},
        {"labelName": "辅助框", "object_type": "context"},
    ])
    c = compare(r, rev, 0.5)
    assert c["expected_object_count"] == 1
    assert c["context_object_count"] == 1
    assert c["predicted_context_object_count"] == 1
    assert c["object_match"] is True
    assert c["deterministic_verdict"] == "正确"


def test_compare_label_value_mismatch_is_partial():
    r = _result(objects=[{"name": "car", "bbox": [0, 0, 10, 10], "label_value": "2"}])
    rev = _review(objects=[{"labelName": "car", "labelValue": "1", "bbox": [0, 0, 10, 10]}])
    c = compare(r, rev, 0.5)
    assert c["label_match"] is False
    assert c["deterministic_verdict"] == "部分正确"


def test_compare_parse_failure_has_no_deterministic_verdict():
    c = compare(_result("error", [], parse_ok=False), _review(), 0.5)
    assert c["parse_valid"] is False
    assert c["deterministic_verdict"] is None


def test_compare_human_verdict_cannot_override_to_correct():
    r = _result(objects=[{"name": "car", "bbox": [0, 0, 10, 10]}])
    rev = _review(objects=[{"labelName": "car", "bbox": [0, 0, 10, 10]}], verdict="误报")
    assert compare(r, rev, 0.5)["deterministic_verdict"] == "部分正确"


def test_compare_human_verdict_passthrough():
    c = compare(_result(), _review(verdict="无法判断"), 0.5)
    assert c["human_verdict"] == "无法判断"


def test_compare_without_ground_truth():
    c = compare(_result("normal", []), {}, 0.5)
    assert c["has_ground_truth"] is False
    assert c["status_match"] is None
    assert c["deterministic_verdict"] is None
    assert c["comparison_confidence"] == "low"