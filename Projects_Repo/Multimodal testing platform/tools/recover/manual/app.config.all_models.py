def all_models(cfg):
    """全部站点的模型并集（保持顺序去重）"""
    seen, out = set(), []
    for site in cfg.get("api", {}).get("sites") or []:
        for m in site.get("models", []):
            if m not in seen:
                seen.add(m)
                out.append(m)
    return out