# decompyle3 version 3.9.3
# Python bytecode version base 3.8.0 (3413)
# Decompiled from: Python 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
# Embedded file name: app\config.py
"""全局配置与工作区路径管理

所有数据都在 workspace/ 下，纯文件系统存储：
  workspace/
    config.json            全局配置（API、模型、并发等）
    datasets/{name}/       图片集
    prompts/{name}/        提示词库（V1.txt V2.txt ... + meta.json）
    runs/{run_id}/         测试运行（run.json + results/*.json + annotated/*.jpg）
    truth/{task}/          真值任务（task.json + {label}/*.jpg）
    evals/{eval_id}/       评估记录（eval.json）
    exports/{name}/        字段提取输出
"""
import json, os, sys, threading
from urllib.parse import urlparse
_lock = threading.RLock()
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.environ.get("MMTEST_WORKSPACE", os.path.join(BASE_DIR, "workspace"))
CONFIG_PATH = os.path.join(WORKSPACE, "config.json")
DEFAULT_CONFIG = {'api':{"sites": [
            {'name':"海康MaaS", 
             'base_url':"https://maas.hikvision.com.cn/v1", 
             'api_keys':[],  'models':[
              "GLanLMM_V1.5", "Qwen3.5-397B-A17B-FP8"]}]}, 
 'defaults':{
   'site': "",
   'model': "GLanLMM_V1.5",
   'concurrency': 3,
   'key_concurrency': 1,
   'key_cooldown': 10,
   'auto_concurrency': True,
   'max_retries': 3,
   'retry_delay': 2,
   'timeout': 120,
   'max_tokens': 4096,
   'temperature': None,
   'seed': None,
   'judge_temperature': 0.3,
   'optimizer_max_tokens': 8192,
   'optimizer_timeout': 600,
   'judge_max_tokens': 8192,
   'prompt_max_tokens': 8192}}
_SITE_NAME_FORBIDDEN = '\\/:*?"<>|'
SUBDIRS = [
 "datasets", "prompts", "runs", "truth", "evals", "exports", "reviews",
 "judgments", "prompt_sessions", "prompt_profiles", "prompt_optimizations",
 "workflows"]

def ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)
    for d in SUBDIRS:
        os.makedirs((os.path.join(WORKSPACE, d)), exist_ok=True)


def load_config() -> dict:
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
        if isinstance(v, dict):
            for (kk, vv) in v.items():
                if kk not in cfg[k]:
                    cfg[k][kk] = vv
                    changed = True

    if changed:
        save_config(cfg)
    return cfg


def save_config(cfg: dict):
    ensure_workspace()
    cfg = normalize_config(cfg)
    with _lock:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)


def normalize_config(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        raise ValueError("配置必须是对象")
    api = cfg.get("api") if isinstance(cfg.get("api"), dict) else {}
    defaults = cfg.get("defaults") if isinstance(cfg.get("defaults"), dict) else {}
    result = json.loads(json.dumps(DEFAULT_CONFIG))
    sites = api.get("sites")
    if sites or "base_url" in api or "base_url" in api or "models" in api:
        sites = [
         {'name':str(api.get("site_name") or "默认站点"),  'base_url':api.get("base_url") or DEFAULT_CONFIG["api"]["sites"][0]["base_url"], 
          'api_keys':api.get("api_keys") or [], 
          'models':api.get("models") or []}]
    if not (isinstance(sites, list) and sites):
        sites = json.loads(json.dumps(DEFAULT_CONFIG["api"]["sites"]))
    norm_sites = []
    seen_names = set()
    for (index, raw) in enumerate(sites):
        if not isinstance(raw, dict):
            raise ValueError("站点配置必须是对象")
        else:
            name = str(raw.get("name") or "").strip() or f"站点{index + 1}"
            if any((c in name for c in _SITE_NAME_FORBIDDEN)) or "::" in name:
                raise ValueError(f"站点名称非法：{name}")
            if name in seen_names:
                raise ValueError(f"站点名称重复：{name}")
            seen_names.add(name)
            base_url = str(raw.get("base_url") or "").strip().rstrip("/")
            parsed = urlparse(base_url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                raise ValueError(f"站点「{name}」的 Base URL 必须是有效的 http/https 地址")
            keys = raw.get("api_keys") or []
            models = raw.get("models") or []
            if not (isinstance(keys, list) and isinstance(models, list)):
                raise ValueError(f"站点「{name}」的 API Keys 和模型列表必须是数组")
            keys = [str(value).strip() for value in keys if str(value).strip()]
            models = [str(value).strip() for value in models if str(value).strip()]
            if not models:
                raise ValueError(f"站点「{name}」至少配置一个模型")
            norm_sites.append({'name':name,  'base_url':base_url,  'api_keys':keys, 
             'models':models})

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
    all_models = [m for s in norm_sites for m in iter((s["models"]))]
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


def all_models(cfg: dict) -> list:
    """全部站点的模型并集（保持顺序去重）"""
    seen, out = set(), []
    for site in cfg.get("api", {}).get("sites") or []:
        for m in site.get("models", []):
            if m not in seen:
                seen.add(m)
                out.append(m)

        return out


def total_keys(cfg: dict) -> int:
    return sum((len(s.get("api_keys") or []) for s in cfg.get("api", {}).get("sites") or []))


def subdir(name: str) -> str:
    ensure_workspace()
    return os.path.join(WORKSPACE, name)


def safe_path(base: str, *parts: str) -> str:
    """拼接路径并校验不越出 base，防止路径穿越"""
    p = os.path.realpath((os.path.join)(base, *parts))
    if not p.startswith(os.path.realpath(base) + os.sep):
        if p != os.path.realpath(base):
            raise ValueError("非法路径")
        return p
