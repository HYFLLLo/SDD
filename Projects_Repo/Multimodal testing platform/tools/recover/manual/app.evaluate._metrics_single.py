def _metrics_single(labels, details):
    matrix = {t: {p: 0 for p in labels + ["__未识别__"]} for t in labels}
    correct = 0
    for d in details:
        t = d["truth"][0]
        p = d["pred"] if d["pred"] in labels else "__未识别__"
        matrix[t][p] += 1
        if d["correct"]:
            correct += 1
    per_class = {}
    for l in labels:
        tp = matrix[l][l]
        fp = sum((matrix[t][l] for t in labels if t != l))
        fn = sum((matrix[l][p] for p in labels + ["__未识别__"] if p != l))
        per_class[l] = _prf(tp, fp, fn)
    n = len(details)
    return {'accuracy': round(correct / n, 4) if n else 0,
            'per_class': per_class, 'confusion_matrix': matrix,
            'support': {l: sum(matrix[l].values()) for l in labels}}