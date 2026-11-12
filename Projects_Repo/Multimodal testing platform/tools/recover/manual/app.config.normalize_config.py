def normalize_config(cfg):
    if not isinstance(cfg, dict):
        raise ValueError("配置必须是对象")
    api = cfg.get("api") if isinstance(cfg.get("api"), dict) else {}
    defaults = cfg.get("defaults") if isinstance(cfg.get("defaults"), dict) else {}
    result = json.loads(json.dumps(DEFAULT_CONFIG))
    sites = api.get("sites")
    if not sites and ("base_url" in api or "api_keys" in api or "models" in api):
        sites = [{'name': str(api.get("site_name") or "默认站点"),
                  'base_url': api.get("base_url") or DEFAULT_CONFIG["api"]["sites"][0]["base_url"],
                  'api_keys': api.get("api_keys") or [],
                  'models': api.get("models") or []}]
    if not (isinstance(sites, list) and sites):
        sites = json.loads(json.dumps(DEFAULT_CONFIG["api"]["sites"]))
    norm_sites = []
    seen_names = set()
    for index, raw in enumerate(sites):
        if not isinstance(raw, dict):
            raise ValueError("站点配置必须是对象")
        name = str(raw.get("name") or "").strip() or f"站点{index + 1}"
        if any(c in name for c in _SITE_NAME_FORBIDDEN) or "::" in name:
            raise ValueError(f"站点名称非法：{name}")
        if name in seen_names:
            raise ValueError(f"站点名称重复：{name}")
        seen_names.add(name)
        base_url = str(raw.get("base_url") or "").strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {'https', 'http'} or not parsed.netloc:
            raise ValueError(f"站点「{name}」的 Base URL 必须是有效的 http/https 地址")
        keys = raw.get("api_keys") or []
        models = raw.get("models") or []
        if not (isinstance(keys, list) and isinstance(models, list)):
            raise ValueError(f"站点「{name}」的 API Keys 和模型列表必须是数组")
        keys = [str(value).strip() for value in keys if str(value).strip()]
        models = [str(value).strip() for value in models if str(value).strip()]
        if not models:
            raise ValueError(f"站点「{name}」至少配置一个模型")
        norm_sites.append({'name': name, 'base_url': base_url,
                           'api_keys': keys, 'models': models})
    result["api"] = {"sites": norm_sites}

    def integer(key, minimum, maximum):
        try:
            value = int(defaults.get(key, result["defaults"][key]))
        except (TypeError, ValueError):
            raise ValueError(f"{key} 必须是整数")
        else:
            if not minimum <= value <= maximum:
                raise ValueError(f"{key} 必须在 {minimum}-{maximum} 之间")
            result["defaults"][key] = value

    integer("concurrency", 1, 20)
    integer("key_concurrency", 1, 8)
    integer("key_cooldown", 0, 600)
    result["defaults"]["auto_concurrency"] = bool(defaults.get("auto_concurrency", True))
    integer("max_retries", 1, 10)
    integer("retry_delay", 0, 60)
    integer("timeout", 5, 600)
    integer("max_tokens", 128, 131072)
    integer("optimizer_max_tokens", 128, 131072)
    integer("optimizer_timeout", 30, 1800)
    integer("judge_max_tokens", 128, 131072)
    integer("prompt_max_tokens", 128, 131072)
    all_models = [m for s in norm_sites for m in s["models"]]
    model = str(defaults.get("model") or all_models[0]).strip()
    if model not in all_models:
        model = all_models[0]
    result["defaults"]["model"] = model
    site = str(defaults.get("site") or "").strip()
    if site not in seen_names:
        site = next((s["name"] for s in norm_sites if model in s["models"]), norm_sites[0]["name"])
    result["defaults"]["site"] = site
    temperature = defaults.get("temperature")
    if temperature is not None:
        temperature = float(temperature)
        if not 0 <= temperature <= 2:
            raise ValueError("temperature 必须在 0-2 之间")
    result["defaults"]["temperature"] = temperature
    seed = defaults.get("seed")
    result["defaults"]["seed"] = None if seed is None else int(seed)
    judge_temp = defaults.get("judge_temperature")
    if judge_temp is not None:
        judge_temp = float(judge_temp)
        if not 0 <= judge_temp <= 2:
            raise ValueError("judge_temperature 必须在 0-2 之间")
    result["defaults"]["judge_temperature"] = judge_temp
    return result