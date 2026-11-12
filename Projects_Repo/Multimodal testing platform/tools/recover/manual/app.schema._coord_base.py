def _coord_base(model):
    """按模型返回相对坐标的除数基值；None 表示该模型使用绝对像素坐标。

    - GLanLMM 1.5 及更早：绝对像素坐标
    - GLanLMM 1.6 及更新、其余所有模型：0-1000 相对坐标，除以 1000
      （0-999 与 0-1000 的口径差异折算后不足 1 像素，统一按 1000 处理）
    """
    m = (model or "").lower()
    if "glan" in m:
        match = re.search("glan[a-z_]*v?(\\d+(?:\\.\\d+)?)", m)
        if match and float(match.group(1)) <= 1.5:
            return
    return 1000.0