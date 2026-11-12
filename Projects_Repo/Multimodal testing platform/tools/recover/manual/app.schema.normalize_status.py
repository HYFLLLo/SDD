def normalize_status(raw, objects, labels):
    """按任务配置的二值标签归一化；未配置时仅兼容旧别名并保留未知值。"""
    pair = _status_labels(labels)
    if pair:
        positive, negative = pair
        if raw is None:
            if objects:
                return positive
            return negative
        if isinstance(raw, bool):
            if raw:
                return positive
            return negative
        if isinstance(raw, (int, float)) and raw in (0, 1):
            if raw == 1:
                return positive
            return negative
        s = str(raw).strip()
        if s == "1":
            return positive
        if s == "0":
            return negative
        if s.casefold() in {positive.casefold(), negative.casefold()}:
            if s.casefold() == positive.casefold():
                return positive
            return negative
        if s.casefold() in _ABNORMAL_WORDS or "异常" in s or "违规" in s:
            return positive
        if s.casefold() in _NORMAL_WORDS or "正常" in s:
            return negative
        return s
    if raw is None:
        if objects:
            return "abnormal"
        return "normal"
    if isinstance(raw, bool):
        if raw:
            return "abnormal"
        return "normal"
    s = str(raw).strip().lower()
    if s in _ABNORMAL_WORDS:
        return "abnormal"
    if s in _NORMAL_WORDS:
        return "normal"
    if "abnormal" in s or "异常" in s or "违规" in s:
        return "abnormal"
    return s