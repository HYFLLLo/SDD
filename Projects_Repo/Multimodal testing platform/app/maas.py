"""多站点模型调用客户端（OpenAI 兼容协议）

- 支持多个站点（base_url），每个站点独立的多 API Key 轮询与模型列表
- 失败重试：仅对 限流(429)/服务端5xx/网络超时 重试，参数类 4xx 错误直接失败不浪费重试
- 返回原始文本 + token 用量 + 耗时
"""
import base64, io, itertools, os, threading, time
from typing import Any, Dict, Optional
import httpx
from openai import OpenAI

def _openai_client(api_key, base_url, timeout):
    """创建 OpenAI 客户端；trust_env=False 仅此客户端不走系统代理，不影响其他网络请求"""
    http = httpx.Client(trust_env=False, timeout=timeout)
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, http_client=http)


_MIME = {
  '.jpg': "image/jpeg", '.jpeg': "image/jpeg", '.png': "image/png",
  '.bmp': "image/bmp",  '.webp': "image/webp"}

def _image_mime(path):
    return _MIME.get(os.path.splitext(path)[1].lower(), "image/jpeg")


_MODEL_PARAMS = {"qwen3.5-397b-a17b-fp8": {"max_tokens": 16384}}
_IMAGE_REENCODE_THRESHOLD = 716800
_IMAGE_JPEG_QUALITY = 85

def _model_max_tokens_floor(model):
    params = _MODEL_PARAMS.get((model or "").strip().lower())
    if params:
        return params.get("max_tokens")


def _reencode_jpeg(image_path):
    """按原始分辨率重编码为 JPEG；逐步降质量直到低于阈值。失败返回 None。"""
    try:
        from PIL import Image, ImageOps
    except Exception:
        return

    try:
        with Image.open(image_path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                background = Image.new("RGB", im.size, (255, 255, 255))
                rgba = im.convert("RGBA")
                background.paste(rgba, mask=rgba.split()[-1])
                im = background
            elif im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            best = None
            for quality in (_IMAGE_JPEG_QUALITY, 75, 65, 55):
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=quality, optimize=True)
                data = buf.getvalue()
                if not data:
                    continue
                if best is None or len(data) < len(best):
                    best = data
                if len(data) <= _IMAGE_REENCODE_THRESHOLD:
                    break
        return best
    except Exception:
        return


def _should_retry(e):
    """429 限流 / 5xx 服务端 / 网络超时 值得重试；其余 4xx（参数、鉴权）重试无意义"""
    status = getattr(e, "status_code", None)
    if status is None:
        return True
    return status == 429 or status >= 500


class MaaSClient:
    """MaaSClient"""

    def __init__(self, config, site=None):
        api = config.get("api", {})
        defaults = config.get("defaults", {})
        self.sites = api.get("sites") or []
        self.default_site = site or defaults.get("site") or (self.sites[0]["name"] if self.sites else "")
        self.max_retries = int(defaults.get("max_retries", 3))
        self.retry_delay = float(defaults.get("retry_delay", 2))
        self.timeout = float(defaults.get("timeout", 120))
        self.max_tokens = int(defaults.get("max_tokens", 4096))
        self.default_concurrency = max(1, min(20, int(defaults.get("concurrency", 3))))
        self.auto_concurrency = bool(defaults.get("auto_concurrency", True))
        self.key_concurrency = max(1, int(defaults.get("key_concurrency", 1)))
        self.key_cooldown = max(0.0, float(defaults.get("key_cooldown", 10)))
        self._cycles = {}
        self._clients = {}
        self._lock = threading.RLock()
        self._key_state = {}
        self._key_cv = threading.Condition(threading.RLock())

    def _resolve(self, model=None, site=None):
        """定位站点：显式 site 优先；否则按模型归属；否则默认站点"""
        if not self.sites:
            raise ValueError("未配置任何站点，请先到配置页添加")
        if site:
            for s in self.sites:
                if s["name"] == site:
                    return s
            raise ValueError(f"站点不存在：{site}")

        if model:
            for s in self.sites:
                if model in (s.get("models") or []):
                    return s

        for s in self.sites:
            if s["name"] == self.default_site:
                return s
        return self.sites[0]

    def has_keys(self, site=None):
        if site:
            try:
                return bool(self._resolve(site=site).get("api_keys"))
            except ValueError:
                return False

        return any((s.get("api_keys") for s in self.sites))

    def _client_for(self, site, key):
        cache_key = (
         site["name"], key)
        with self._lock:
            if cache_key not in self._clients:
                self._clients[cache_key] = _openai_client(key, site["base_url"], self.timeout)
            return self._clients[cache_key]

    def _key_state_for(self, site, key):
        identity = (
         site["name"], key)
        state = self._key_state.get(identity)
        if state is None:
            state = {
              'inflight': 0, 'cooldown_until': 0.0, 'failures': 0,
              'last_error': "",  'last_used': 0.0}
            self._key_state[identity] = state
        return state

    def _acquire_key(self, site):
        keys = [str(k).strip() for k in site.get("api_keys") or [] if str(k).strip()]
        if not keys:
            raise ValueError(f'站点「{site.get("name", "")}」未配置 API Key')
        with self._key_cv:
            while True:
                now = time.time()
                candidates = []
                for key in keys:
                    state = self._key_state_for(site, key)
                    if state["cooldown_until"] <= now:
                        if state["inflight"] < self.key_concurrency:
                            candidates.append((state["inflight"], state["last_used"], key))

                if candidates:
                    _, _, key = min(candidates)
                    state = self._key_state_for(site, key)
                    state["inflight"] += 1
                    state["last_used"] = now
                    return key
                else:
                    waits = [max(0.05, self._key_state_for(site, key)["cooldown_until"] - now) for key in keys]
                    self._key_cv.wait(timeout=(min(waits + [0.5])))

    def _release_key(self, site, key, error=None):
        status = getattr(error, "status_code", None) if error else None
        with self._key_cv:
            state = self._key_state_for(site, key)
            state["inflight"] = max(0, state["inflight"] - 1)
            if error:
                state["failures"] += 1
                state["last_error"] = str(error)
                if status == 429:
                    state["cooldown_until"] = max(state["cooldown_until"], time.time() + self.key_cooldown)
            else:
                state["failures"] = 0
                state["last_error"] = ""
                state["cooldown_until"] = 0.0
            self._key_cv.notify_all()

    def recommended_concurrency(self, requested=None, site=None):
        """给出 worker 数；自动模式按 Key 槽位收敛，手动模式保留用户上限。

            无论 worker 数如何，_acquire_key 都会继续执行单 Key 并发槽位限制，
            因此关闭自动模式只会增加等待中的 worker，不会绕过 Key 限流保护。
            """
        cfg_sites = [self._resolve(site=site)] if site else self.sites
        key_count = max([len([k for k in s.get("api_keys") or [] if str(k).strip()]) for s in cfg_sites] or [1])
        key_capacity = max(1, min(20, key_count * self.key_concurrency))
        requested_value = max(1, min(20, int(requested or self.default_concurrency)))
        if self.auto_concurrency:
            return min(requested_value, key_capacity)
        return requested_value

    def key_stats(self, site=None):
        """返回脱敏后的 Key 状态，不返回明文 Key。"""
        out = {}
        with self._key_cv:
            for (site_name, key), state in self._key_state.items():
                if site and site_name != site:
                    pass
                else:
                    label = f"{site_name}:{key[-6:]}"
                    out[label] = {'site':site_name,  'key_suffix':key[-6:],  'inflight':state["inflight"], 
                     'failures':state["failures"],  'cooldown_until':state["cooldown_until"], 
                     'last_error':state["last_error"]}

        return out

    @staticmethod
    @staticmethod
    def _payload(image_path):
        """返回 (base64, mime)。图片过大时按同分辨率重编码为 JPEG 以规避请求体上限。"""
        try:
            size = os.path.getsize(image_path)
        except OSError:
            size = 0
        else:
            if size > _IMAGE_REENCODE_THRESHOLD:
                data = _reencode_jpeg(image_path)
                if data is not None:
                    if len(data) < size:
                        return (
                         base64.b64encode(data).decode("utf-8"), "image/jpeg")
            with open(image_path, "rb") as f:
                return (base64.b64encode(f.read()).decode("utf-8"), _image_mime(image_path))

    @staticmethod
    @staticmethod
    def _b64(image_path):
        """仅返回 base64（保留旧签名）。"""
        return MaaSClient._payload(image_path)[0]

    @staticmethod
    @staticmethod
    def _data_url(image_path):
        b64, mime = MaaSClient._payload(image_path)
        return f"data:{mime};base64,{b64}"

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

    def chat_image(self, image_path, prompt, model, site=None, temperature=None, seed=None, max_tokens=None):
        """调用多模态模型识别单张图片，返回 {text, usage, latency, error}"""
        messages = [
         {'role':"user", 
          'content':[
           {'type':"image_url", 
            'image_url':{"url": (self._data_url(image_path))}},
           {'type':"text", 
            'text':prompt}]}]
        return self._chat(messages, model, temperature, seed, max_tokens, site=site)

    def chat_text(self, prompt, model, system=None, site=None, temperature=None, seed=None, max_tokens=None, timeout=None, max_retries=None):
        """调用文本模型，用于提示词生成和裁判建议。"""
        messages = []
        if system:
            messages.append({'role':"system",  'content':system})
        messages.append({'role':"user",  'content':prompt})
        return self._chat(messages, model, temperature, seed, max_tokens, site=site, timeout=timeout,
          max_retries=max_retries)

    def chat_multimodal(self, image_paths, prompt, model, system=None, site=None, temperature=None, seed=None, max_tokens=None):
        """同时发送原图/标注图与文字，供多模态模型使用。"""
        content = []
        for path in image_paths or []:
            if path and os.path.exists(path):
                content.append({'type':"image_url",  'image_url':{"url": (self._data_url(path))}})
        content.append({'type':"text",  'text':prompt})
        messages = []
        if system:
            messages.append({'role':"system",  'content':system})
        messages.append({'role':"user",  'content':content})
        return self._chat(messages, model, temperature, seed, max_tokens, site=site)

    def chat_messages(self, messages, model, system=None, site=None, temperature=None, seed=None, max_tokens=None):
        """发送已构造好的多轮消息（content 可为文本或含 image_url 的数组）。"""
        full = []
        if system:
            full.append({'role':"system",  'content':system})
        full.extend(messages)
        return self._chat(full, model, temperature, seed, max_tokens, site=site)

    def image_part(self, image_path):
        """构造 OpenAI 兼容的 image_url content 片段"""
        return {'type':"image_url", 
         'image_url':{"url": (self._data_url(image_path))}}

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
