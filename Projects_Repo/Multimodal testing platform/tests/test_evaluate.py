from app.evaluate import _metrics_multi, _metrics_single, _prf


def test_prf_basic():
    assert _prf(2, 1, 1) == {"precision": 0.6667, "recall": 0.6667, "f1": 0.6667, "tp": 2, "fp": 1, "fn": 1}


def test_prf_all_zero_has_no_division_error():
    assert _prf(0, 0, 0) == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0}


def test_prf_perfect():
    assert _prf(3, 0, 0)["f1"] == 1.0


def test_metrics_single_accuracy_and_confusion():
    details = [
        {"truth": ["a"], "pred": "a", "correct": True},
        {"truth": ["a"], "pred": "b", "correct": False},
        {"truth": ["b"], "pred": "b", "correct": True},
    ]
    m = _metrics_single(["a", "b"], details)
    assert m["accuracy"] == 0.6667
    assert m["support"] == {"a": 2, "b": 1}
    assert m["confusion_matrix"]["a"]["a"] == 1
    assert m["confusion_matrix"]["a"]["b"] == 1
    assert m["per_class"]["a"]["tp"] == 1
    assert m["per_class"]["a"]["fn"] == 1
    assert m["per_class"]["b"]["fp"] == 1


def test_metrics_single_unknown_prediction_bucket():
    details = [{"truth": ["a"], "pred": "zzz", "correct": False}]
    m = _metrics_single(["a"], details)
    assert m["confusion_matrix"]["a"]["__未识别__"] == 1
    assert m["accuracy"] == 0.0


def test_metrics_single_empty_details():
    m = _metrics_single(["a"], [])
    assert m["accuracy"] == 0
    assert m["support"] == {"a": 0}
    assert m["per_class"]["a"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0}


def test_metrics_multi_micro_and_exact():
    details = [
        {"truth": ["a"], "tp": ["a"], "fp": [], "fn": [], "correct": True},
        {"truth": ["a", "b"], "tp": ["a"], "fp": ["c"], "fn": ["b"], "correct": False},
    ]
    m = _metrics_multi(["a", "b"], details)
    assert m["exact_match"] == 0.5
    assert m["micro"] == {"precision": 1.0, "recall": 0.6667, "f1": 0.8, "tp": 2, "fp": 0, "fn": 1}
    assert m["per_label"]["a"]["f1"] == 1.0
    assert m["per_label"]["b"]["f1"] == 0.0
    assert m["support"] == {"a": 2, "b": 1}


def test_metrics_multi_empty_details():
    m = _metrics_multi(["a"], [])
    assert m["exact_match"] == 0
    assert m["micro"]["tp"] == 0
    assert m["per_label"]["a"]["f1"] == 0.0