"""快速试跑：提示词不存版本、不建运行，直接对少量图片调模型看效果

提示词调优的最高频路径：改一句 → 立刻在几张图上验证 → 再改。
试跑结果不落盘（标注图以 base64 内联返回），不产生任何运行记录。
"""
import base64, io, random
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from . import datasets
from .annotate import draw_objects, get_image_size
from .config import load_config
from .maas import MaaSClient
from .schema import parse_result
MAX_TRIAL_IMAGES = 4

def _pick_images(dataset, rels, sample):
    all_imgs = datasets.scan_images(dataset)
    if not all_imgs:
        raise ValueError("图片集为空")
    if rels:
        wanted = set(rels)
        chosen = [i for i in all_imgs if i["rel"] in wanted]
        if not chosen:
            raise ValueError("所选图片不在图片集中")
    else:
        n = min(max(1, sample or 2), len(all_imgs), MAX_TRIAL_IMAGES)
        chosen = random.sample(all_imgs, n)
        chosen.sort(key=(lambda x: x["rel"]))
    return chosen[:MAX_TRIAL_IMAGES]


def _trial_one(client, dataset, img, prompt, model, params, site=None):
    path = datasets.image_path(dataset, img["rel"])
    try:
        w, h = get_image_size(path)
    except Exception:
        w, h = (1, 1)
    resp = client.chat_image(path,
      prompt, model, site=site, temperature=(params.get("temperature")),
      seed=(params.get("seed")),
      max_tokens=(params.get("max_tokens")))
    item = {'rel':img["rel"], 
     'latency':(resp.get)("latency"),  'usage':(resp.get)("usage"), 
     'error':(resp.get)("error"),  'raw':(resp.get("text") or "")[:3000], 
     'parse_ok':False, 
     'overall_status':None,  'summary':"",  'object_count':0, 
     'result':None,  'annotated':None}
    if resp.get("error"):
        return item
    result = parse_result((resp["text"]), model=model, img_w=w, img_h=h, mapping=(params.get("map") or None),
      output_mode=(params.get("output_mode", "fixed")),
      status_labels=(params.get("status_labels")))
    item.update({'parse_ok':(result.get)("parse_ok"), 
     'overall_status':(result.get)("overall_status"), 
     'summary':result.get("summary") or "", 
     'object_count':len(result.get("objects", [])), 
     'result':{k: v for k, v in result.items() if k != "raw"}})
    if result.get("objects"):
        try:
            im = draw_objects(path, (result["objects"]), output_path=None, show_fields=(params.get("show_fields") or None))
            if im is not None:
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=88)
                item["annotated"] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            pass

    return item

def run_trial(params):
    """params: {dataset, images?[rel...], sample?, prompt_content, model?,
    temperature?, seed?, max_tokens?, output_mode?, map?, show_fields?}"""
    prompt = (params.get("prompt_content") or "").strip()
    if not prompt:
        raise ValueError("提示词内容为空")
    dataset = params.get("dataset") or ""
    cfg = load_config()
    model = params.get("model") or cfg["defaults"]["model"]
    site = params.get("site") or None
    client = MaaSClient(cfg)
    if not client.has_keys():
        raise ValueError("未配置 API Key，请先到「配置」页填写")
    chosen = _pick_images(dataset, params.get("images"), int(params.get("sample") or 0))
    with ThreadPoolExecutor(max_workers=(min(len(chosen), 4))) as pool:
        futs = [pool.submit(_trial_one, client, dataset, img, prompt, model, params, site) for img in chosen]
        items = [f.result() for f in futs]
    order = {c["rel"]: i for i, c in enumerate(chosen)}
    items.sort(key=(lambda x: order.get(x["rel"], 0)))
    return {'model':model, 
     'site':site or "",  'dataset':dataset,  'count':len(items), 
     'items':items}
