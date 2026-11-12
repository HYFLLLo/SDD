def load_config():
    ensure_workspace()
    with _lock:
        if not os.path.exists(CONFIG_PATH):
            save_config(DEFAULT_CONFIG)
            return json.loads(json.dumps(DEFAULT_CONFIG))
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    changed = False
    for (k, v) in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
            changed = True
        elif isinstance(v, dict):
            for (kk, vv) in v.items():
                if kk not in cfg[k]:
                    cfg[k][kk] = vv
                    changed = True
    if changed:
        save_config(cfg)
    return cfg