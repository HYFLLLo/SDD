# decompyle3 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: app\stats.py
"""稳定性统计：同一图片 × 同一提示词 × N 次复现的结果一致性"""
import json, os
from collections import Counter
from typing import Dict, List
from .runner import _run_dir, _load_run, list_run_images, get_result

def _mode(items: List):
    if not items:
        return (None, 0)
    c = Counter(items)
    (val, cnt) = c.most_common(1)[0]
    return (
     val, cnt / len(items))


def run_stability(run_id: str) -> Dict:
    """整轮运行的稳定性报告"""
    run = _load_run(run_id)
    images = list_run_images(run_id)
    per_image = []
    total_parse_ok = total_protocol_valid = total_results = 0
    (status_agree_sum, status_cnt) = (0.0, 0)
    (nameset_agree_sum, nameset_cnt) = (0.0, 0)
    (cls_agree_sum, cls_cnt) = (0.0, 0)
    status_counter = Counter()
    cls_counter = Counter()
    obj_counter = Counter()
    for img in images:
        results = []
        for rep in img["repeats"]:
            if not rep["exists"]:
                pass
            else:
                try:
                    results.append(get_result(run_id, img["rel"], rep["repeat"]))
                except Exception:
                    while True:
                        pass

        if not results:
            pass
        else:
            n = len(results)
            total_results += n
            parse_ok = sum((1 for r in results if r.get("parse_ok")))
            total_parse_ok += parse_ok
            total_protocol_valid += sum((1 for r in results if r.get("protocol_valid") is True))
            parsed = [r for r in results if r.get("parse_ok")]
            statuses = [r.get("overall_status") for r in parsed]
            (status_mode, status_agree) = _mode(statuses)
            if len(statuses) > 1:
                status_agree_sum += status_agree
                status_cnt += 1
            for r in parsed:
                status_counter[r.get("overall_status") or "?"] += 1
                cl = (r.get("classification") or {}).get("label")
                if cl:
                    cls_counter[cl] += 1
                for o in r.get("objects", []):
                    if o.get("name"):
                        obj_counter[o["name"]] += 1

                cls_labels = [cl for cl in ((r.get("classification") or {}).get("label") for r in parsed) if cl]
                (cls_mode, cls_agree) = _mode(cls_labels)

            if len(cls_labels) > 1:
                cls_agree_sum += cls_agree
                cls_cnt += 1
            name_sets = [frozenset((o.get("name") for o in r.get("objects", []))) for r in parsed]
            ns_agree = None
            if len(name_sets) > 1:
                pairs = 0
                acc = 0.0
                for i in range(len(name_sets)):
                    for j in range(i + 1, len(name_sets)):
                        a, b = name_sets[i], name_sets[j]
                        union = a | b
                        acc += len(a & b) / len(union) if union else 1.0
                        pairs += 1

                ns_agree = acc / pairs if pairs else 1.0
                nameset_agree_sum += ns_agree
                nameset_cnt += 1
            per_image.append({'rel':img["rel"], 
             'runs':n, 
             'parse_ok':parse_ok, 
             'status_mode':status_mode, 
             'status_agree':round(status_agree, 3) if statuses else None, 
             'cls_mode':cls_mode, 
             'cls_agree':round(cls_agree, 3) if cls_labels else None, 
             'nameset_agree':round(ns_agree, 3) if (ns_agree is not None) else None, 
             'flaky':bool(statuses and status_agree < 1.0)})

    return {'run_id':run_id, 
     'repeat':run["repeat"], 
     'image_count':len(per_image), 
     'parse_rate':round(total_parse_ok / total_results, 4) if total_results else None, 
     'protocol_valid_rate':round(total_protocol_valid / total_results, 4) if total_results else None, 
     'status_agree_avg':round(status_agree_sum / status_cnt, 4) if status_cnt else None, 
     'cls_agree_avg':round(cls_agree_sum / cls_cnt, 4) if cls_cnt else None, 
     'nameset_agree_avg':round(nameset_agree_sum / nameset_cnt, 4) if nameset_cnt else None, 
     'flaky_images':[p["rel"] for p in per_image if p["flaky"]], 
     'status_dist':dict(status_counter.most_common()), 
     'classification_dist':dict(cls_counter.most_common(20)), 
     'object_label_dist':dict(obj_counter.most_common(20)), 
     'object_total':sum(obj_counter.values()), 
     'per_image':per_image}
