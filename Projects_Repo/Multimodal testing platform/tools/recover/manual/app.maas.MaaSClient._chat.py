def _chat(self, messages, model=None, temperature=None, seed=None, max_tokens=None,
          site=None, timeout=None, max_retries=None):
    site_cfg = self._resolve(model=model, site=site)
    effective_max_tokens = int(max_tokens or self.max_tokens)
    floor = _model_max_tokens_floor(model)
    if floor and effective_max_tokens < floor:
        effective_max_tokens = floor
    kwargs = {"model": model, "messages": messages, "max_tokens": effective_max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if seed is not None:
        kwargs["seed"] = seed
    last_err = None
    retries = max_retries if max_retries is not None else self.max_retries
    for attempt in range(retries):
        key = self._acquire_key(site_cfg)
        if timeout is not None and timeout != self.timeout:
            client = _openai_client(key, site_cfg["base_url"], timeout)
        else:
            client = self._client_for(site_cfg, key)
        t0 = time.time()
        try:
            completion = client.chat.completions.create(**kwargs)
            usage = None
            if getattr(completion, "usage", None):
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }
            self._release_key(site_cfg, key)
            message = completion.choices[0].message
            text = (message.content or getattr(message, "reasoning_content", None) or "")
            return {
                "text": text,
                "usage": usage,
                "latency": round(time.time() - t0, 2),
                "error": None,
                "site": site_cfg["name"],
                "key_suffix": key[-6:],
            }
        except Exception as e:
            self._release_key(site_cfg, key, e)
            cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
            if cause is not None and str(cause) != str(e):
                last_err = f"{e} [{type(cause).__name__}: {cause}]"
            else:
                last_err = str(e)
            if not _should_retry(e):
                break
            time.sleep(self.retry_delay * (attempt + 1))
    return {
        "text": "",
        "usage": None,
        "latency": 0,
        "error": last_err,
        "site": site_cfg.get("name", ""),
        "key_suffix": key[-6:] if "key" in locals() else "",
    }
