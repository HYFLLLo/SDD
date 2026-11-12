"""示例项目素材包：一键创建「防溺水」示例，供新用户参考学习。

素材包位置：开发场景在项目根目录 demo_pack/，exe 场景打包进 _MEIPASS。
素材内容：images/ 示例图片、prompt.txt 五模块提示词、truth.json 真值标签。
"""
import json, os, shutil, sys
from typing import Dict, List
from . import datasets, prompts, truth
from .config import BASE_DIR
DEMO_PROJECT = "示例项目"
DEMO_DATASET = "防溺水-水边人员检测"
DEMO_PROMPT = "防溺水-水边人员检测"
DEMO_TRUTH_TASK = "示例-防溺水真值"
DEMO_LABELS = ["危险", "安全"]
IMG_EXTS = {".jpg",".jpeg",".png",".bmp",".webp"}

def _pack_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "demo_pack")
    return os.path.join(BASE_DIR, "demo_pack")


def _pack_images():
    d = os.path.join(_pack_dir(), "images")
    if not os.path.isdir(d):
        return []
    return [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[1].lower() in IMG_EXTS]


def _dataset_ref():
    return datasets.dataset_ref(DEMO_PROJECT, DEMO_DATASET)


def status():
    imgs = _pack_images()
    ref = _dataset_ref()
    created = datasets.dataset_exists(ref)
    out = {'available':bool(imgs), 
     'image_count':len(imgs), 
     'created':created, 
     'dataset_ref':ref, 
     'prompt_name':DEMO_PROMPT}
    if created:
        out["created_images"] = len(datasets.scan_images(ref))
        try:
            out["truth_task"] = truth.get_task_meta(DEMO_TRUTH_TASK)["id"]
        except Exception:
            pass

    return out


def create():
    """把素材包实例化到工作区：图片集 + 提示词 + 预置真值。幂等。"""
    pack = _pack_dir()
    imgs = _pack_images()
    if not imgs:
        raise ValueError("示例素材包缺失（demo_pack/images 为空）")
    ref = _dataset_ref()
    if datasets.dataset_exists(ref) and datasets.scan_images(ref):
        return {
          'created': False, 'message': "示例项目已存在", 'dataset_ref': ref,
          'prompt_name': DEMO_PROMPT}
    datasets.create_dataset(DEMO_DATASET, project=DEMO_PROJECT)
    dst_dir = datasets._dataset_dir(ref, create=True)
    for fn in imgs:
        shutil.copy2(os.path.join(pack, "images", fn), os.path.join(dst_dir, fn))

    with open((os.path.join(pack, "prompt.txt")), "r", encoding="utf-8") as f:
        content = f.read().strip()
    existing = {p.get("name") for p in prompts.list_prompts()}
    if DEMO_PROMPT not in existing:
        prompts.create_prompt(DEMO_PROMPT, content, note="示例项目内置提示词", group="示例")
    prompts.update_settings(DEMO_PROMPT, {"status_labels": (list(DEMO_LABELS))})
    truth_file = os.path.join(pack, "truth.json")
    labeled = 0
    if os.path.isfile(truth_file):
        with open(truth_file, "r", encoding="utf-8") as f:
            table = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        try:
            truth.get_task_meta(DEMO_TRUTH_TASK)
        except Exception:
            truth.create_task(DEMO_TRUTH_TASK, "single", list(DEMO_LABELS), ref)
        for (fn, label) in table.items():
            if label in DEMO_LABELS:
                if fn in imgs:
                    truth.set_labels(DEMO_TRUTH_TASK, fn, [label])
                    labeled += 1

    return {'created':True, 
     'dataset_ref':ref,  'prompt_name':DEMO_PROMPT,  'images':len(imgs), 
     'truth_labeled':labeled}
