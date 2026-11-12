def _bbox(value):
    if isinstance(value, str):
        nums = re.findall("-?\\d+\\.?\\d*", value)
        if len(nums) < 4:
            return
        value = nums[:4]
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return
    try:
        vals = [float(x) for x in value]
    except (TypeError, ValueError):
        return
    x1, y1, x2, y2 = vals
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return [x1, y1, x2, y2]