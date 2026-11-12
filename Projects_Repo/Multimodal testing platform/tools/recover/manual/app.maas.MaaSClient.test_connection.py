def test_connection(self, site=None):
    """探测站点连通性。site 为空时测试全部站点。"""
    if site:
        sites = [self._resolve(site=site)]
    else:
        sites = list(self.sites)
    if not sites:
        return {"ok": False, "error": "未配置任何站点", "results": []}
    results = []
    for s in sites:
        keys = s.get("api_keys") or []
        if not keys:
            results.append({"site": s["name"], "ok": False, "error": "未配置 API Key"})
            continue
        try:
            client = self._client_for(s, keys[0])
            ids = [m.id for m in client.models.list().data]
            results.append({"site": s["name"], "ok": True, "models": ids})
        except Exception as e:
            status = getattr(e, "status_code", getattr(e, "code", None))
            if str(status) != "404":
                cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
                detail = f"{e} [{type(cause).__name__}: {cause}]" if cause is not None and str(cause) != str(e) else str(e)
                results.append({"site": s["name"], "ok": False, "error": detail})
                continue
            probe_model = (s.get("models") or [""])[0]
            try:
                completion = client.chat.completions.create(
                    model=probe_model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=8,
                )
                if not getattr(completion, "choices", None):
                    raise ValueError("对话探测未返回 choices")
                results.append({"site": s["name"], "ok": True,
                                "models": list(s.get("models") or []), "probe": "chat"})
            except Exception as chat_error:
                results.append({"site": s["name"], "ok": False,
                                "error": f"模型列表接口 404，且对话探测失败：{chat_error}"})
    return {"ok": bool(results) and all(r["ok"] for r in results), "results": results}
