"""测试运行引擎

一次运行 = 图片集 × 提示词版本 × 重复次数 N × 采样参数
目录结构：
  runs/{run_id}/
    run.json                         运行配置快照 + 进度状态
    results/{子目录}/{图名}__r{n}.json  解析后的固定头结果（含 _meta）
    annotated/{子目录}/{图名}__r{n}.jpg 标注图
    raw/{子目录}/{图名}__r{n}.txt       模型原始输出（解析失败时兜底排查）
支持断点续跑：已存在的结果文件自动跳过。
"""
import json, os, shutil, threading, time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from . import datasets, prompts
from .annotate import draw_objects, get_image_size
from .config import load_config, subdir, safe_path
from .dircache import FingerprintCache, fingerprint, subfile_fingerprint
from .maas import MaaSClient
from .schema import build_full_prompt, parse_result
_run_lock = threading.Lock()
_runners: Dict[(str, Dict)] = {}
_RUN_LIST_OMIT = {
 "images_snapshot",
 "user_prompt_snapshot",
 "full_prompt_snapshot",
 "prompt_settings"}

def _run_dir(run_id):
    return safe_path(subdir("runs"), run_id)


def _run_json_path(run_id):
    return os.path.join(_run_dir(run_id), "run.json")


def _load_run(run_id):
    with open((_run_json_path(run_id)), "r", encoding="utf-8") as f:
        return json.load(f)


def _save_run(run):
    tmp = _run_json_path(run["id"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(run, f, ensure_ascii=False, indent=2)
    target = _run_json_path(run["id"])
    for attempt in range(5):
        try:
            os.replace(tmp, target)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.3 * (attempt + 1))


def _result_rel(rel, repeat):
    stem, ext = os.path.splitext(rel)
    return f"{stem}{ext.lower()}__r{repeat}.json"


def _legacy_result_rel(rel, repeat):
    """旧命名（丢弃扩展名），仅用于读取历史结果，保证向后兼容。"""
    return f"{os.path.splitext(rel)[0]}__r{repeat}.json"


def _result_candidates(rel, repeat):
    """新命名优先，其次回退旧命名，避免升级后找不到历史结果。"""
    new = _result_rel(rel, repeat)
    old = _legacy_result_rel(rel, repeat)
    if new == old:
        return (new,)
    return (new, old)


def _existing_result_path(run_id, rel, repeat):
    """返回该图/该次复现的结果文件路径（优先已存在的新命名，兼容旧命名）。"""
    for name in _result_candidates(rel, repeat):
        p = os.path.join(_run_dir(run_id), "results", name)
        if os.path.exists(p):
            return p
    return os.path.join(_run_dir(run_id), "results", _result_rel(rel, repeat))


def _result_reusable(path):
    """断点续跑时是否可跳过：结果存在且不是 API 错误结果（错误结果续跑时自动重试）"""
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return not (d.get("_meta") or {}).get("error")
    except Exception:
        return False


def _result_status(path):
    """读取结果文件的统计口径，返回 (reusable, parse_failed)。

    reusable：接口调用成功（断点续跑可跳过）
    parse_failed：接口成功但 JSON 解析失败。这类结果不会自动重试，
    但必须与 API 失败分开计数，否则界面会出现“失败 0 却有图没结论”。
    """
    if not os.path.exists(path):
        return False, False
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return False, False
    if (d.get("_meta") or {}).get("error"):
        return False, False
    return True, d.get("parse_ok") is False


def create_run(params):
    dataset = params["dataset"]
    prompt_name = params["prompt_name"]
    prompt_version = int(params["prompt_version"])
    repeat = max(1, int(params.get("repeat", 1)))
    model = params.get("model") or load_config()["defaults"]["model"]
    site = params.get("site") or ""
    pv = prompts.get_version(prompt_name, prompt_version)
    settings = prompts.get_settings(prompt_name)
    split = params.get("split") or None
    images = datasets.scan_images(dataset, split=split)
    if not images:
        raise ValueError("图片集为空")
    run_id = time.strftime("%Y%m%d-%H%M%S") + f"_{prompt_name}-V{prompt_version}_x{repeat}"
    base, i = run_id, 2
    while os.path.exists(_run_dir(run_id)):
        run_id = f"{base}-{i}"
        i += 1

    cfg = load_config()
    defaults = cfg["defaults"]
    full_prompt = pv["content"]
    run = {'id':run_id, 
     'dataset':dataset, 
     'dataset_project':datasets.split_ref(dataset)[0], 
     'dataset_name':datasets.split_ref(dataset)[1], 
     'dataset_split':split, 
     'prompt_name':prompt_name, 
     'prompt_version':prompt_version, 
     'prompt_settings':settings, 
     'model':model, 
     'site':site, 
     'repeat':repeat, 
     'temperature':(params.get)("temperature", defaults.get("temperature")), 
     'seed':(params.get)("seed", defaults.get("seed")), 
     'max_tokens':(params.get)("max_tokens", defaults.get("max_tokens")), 
     'concurrency':int(params.get("concurrency", defaults.get("concurrency", 3))), 
     'show_fields':(params.get)("show_fields", []), 
     'created':(time.strftime)("%Y-%m-%d %H:%M:%S"), 
     'status':"pending", 
     'total':(len(images)) * repeat, 
     'done':0, 
     'failed':0, 
     'image_count':len(images), 
     'images_snapshot':[{'rel':x["rel"], 
      'name':x["name"],  'split':(x.get)("split")} for x in images], 
     'user_prompt_snapshot':pv["content"], 
     'full_prompt_snapshot':full_prompt}
    try:
        os.makedirs((os.path.join(_run_dir(run_id), "images")), exist_ok=True)
        for image in images:
            source = datasets.image_path(dataset, image["rel"])
            target = safe_path(_run_dir(run_id), "images", image["rel"])
            os.makedirs((os.path.dirname(target)), exist_ok=True)
            shutil.copy2(source, target)

        os.makedirs((os.path.join(_run_dir(run_id), "results")), exist_ok=True)
        os.makedirs((os.path.join(_run_dir(run_id), "annotated")), exist_ok=True)
        os.makedirs((os.path.join(_run_dir(run_id), "raw")), exist_ok=True)
        _save_run(run)
    except Exception:
        shutil.rmtree((_run_dir(run_id)), ignore_errors=True)
        raise
    return run


_runs_cache = FingerprintCache()

_parse_failed_cache = FingerprintCache()


def _scan_parse_failed(run_id):
    """统计「接口成功但 JSON 解析失败」的结果数（只读，不写盘）。

    历史运行没有 parse_failed 字段，只能扫 results 目录；按目录指纹缓存，
    避免运行列表轮询时反复读全部结果文件。
    """
    base = os.path.join(_run_dir(run_id), "results")
    count = 0
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            _, broken = _result_status(os.path.join(dirpath, fn))
            if broken:
                count += 1
    return count


def _cached_parse_failed(run_id):
    base = os.path.join(_run_dir(run_id), "results")
    return _parse_failed_cache.get(run_id, fingerprint(base), lambda: _scan_parse_failed(run_id))


def list_runs():
    r"""返回运行摘要。

    列表接口只做读取。历史运行的状态对账只在返回结果中完成，不能在这里
    同步写 run.json：运行中的任务会频繁更新状态文件，并发轮询时反复重试
    写盘会让一次列表请求阻塞数秒。
    结果按 runs/*\/run.json 指纹缓存：运行进度写盘会改变指纹，自动重算。
    """
    root = subdir("runs")
    fp = subfile_fingerprint(root, "run.json")

    def compute():
        out = []
        for rid in sorted((os.listdir(root)), reverse=True):
            p = os.path.join(root, rid, "run.json")
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        r = _reconcile_run_state(json.load(f))
                    if not isinstance(r.get("parse_failed"), int):
                        try:
                            r["parse_failed"] = _cached_parse_failed(rid)
                        except Exception:
                            r["parse_failed"] = 0
                    out.append({k: v for k, v in r.items() if k not in _RUN_LIST_OMIT})
                except Exception:
                    continue
        return out

    return _runs_cache.get("all", fp, compute)


def _reconcile_run_state(run):
    """把"标记运行中但其实没有线程在跑"的历史运行纠正为 interrupted。

    服务重启 / 进程异常退出后 run.json 会永久停留在 running，前端既显示"停止"
    又给不出"继续"。这里仅在内存中修正返回值，避免读接口产生写盘副作用；
    后续真正继续运行时，_execute 会重新写入正确的状态。
    """
    if run.get("status") == "running" and run.get("id") not in _runners:
        run["status"] = "interrupted"
        if not run.get("error"):
            run["error"] = "进程中断，可点击继续从断点续跑"
    return run


def get_run(run_id):
    run = _reconcile_run_state(_load_run(run_id))
    run["is_active"] = run_id in _runners
    return run


def delete_run(run_id):
    import shutil
    stop_run(run_id)
    p = _run_dir(run_id)
    if os.path.isdir(p):
        shutil.rmtree(p)


def stop_run(run_id):
    with _run_lock:
        r = _runners.get(run_id)
        if r:
            r["stop"].set()


def start_run(run_id):
    with _run_lock:
        if run_id in _runners:
            raise ValueError("该运行正在执行中")
        run = _load_run(run_id)
        stop = threading.Event()
        t = threading.Thread(target=_execute, args=(run_id, stop), daemon=True)
        _runners[run_id] = {'stop':stop,  'thread':t}
        t.start()
        run["status"] = "running"
        return run


def _execute(run_id, stop):
    try:
        try:
            run = _load_run(run_id)
            run["status"] = "running"
            _save_run(run)

            cfg = load_config()
            client = MaaSClient(cfg)
            if not client.has_keys():
                run["status"] = "failed"
                run["error"] = "未配置 API Key"
                _save_run(run)
                return
            images = run.get("images_snapshot") or datasets.scan_images(run["dataset"], split=run.get("dataset_split"))
            tasks = [(img, r) for img in images for r in range(1, run["repeat"] + 1)]
            with ThreadPoolExecutor(max_workers=max(1, run["concurrency"])) as pool:
                futures = []
                for img, rep in tasks:
                    if stop.is_set():
                        break
                    if _result_reusable(_existing_result_path(run_id, img["rel"], rep)):
                        continue
                    futures.append(pool.submit(_process_one, run_id, run, client, img, rep, stop))
                for f in futures:
                    if stop.is_set():
                        break
                    try:
                        ok = f.result()
                    except Exception:
                        ok = False
                    with _run_lock:
                        run = _load_run(run_id)
                        if ok:
                            run["done"] += 1
                        else:
                            run["failed"] += 1
                        _save_run(run)
            run = _load_run(run_id)
            run["status"] = "stopped" if stop.is_set() else "done"
            run["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _reconcile_counts(run)
            _save_run(run)
        except Exception as e:
            try:
                run = _load_run(run_id)
                run["status"] = "failed"
                run["error"] = str(e)
                _save_run(run)
            except Exception:
                pass
    finally:
        with _run_lock:
            _runners.pop(run_id, None)


def _reconcile_counts(run):
    """按磁盘上的结果文件重算 done/failed，避免停止-恢复后计数漂移。"""
    base = os.path.join(_run_dir(run["id"]), "results")
    done = failed = parse_failed = 0
    for dirpath, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            p = os.path.join(dirpath, fn)
            ok, broken = _result_status(p)
            if ok:
                done += 1
            else:
                failed += 1
            if broken:
                parse_failed += 1
    run["done"] = done
    run["failed"] = failed
    run["parse_failed"] = parse_failed


def _process_one(run_id, run, client, img, repeat, stop):
    if stop.is_set():
        return False
    img_path = image_file(run_id, img["rel"])
    try:
        (w, h) = get_image_size(img_path)
    except Exception:
        (w, h) = (1, 1)
    resp = client.chat_image(img_path,
      (run["full_prompt_snapshot"]), (run["model"]), site=(run.get("site") or None),
      temperature=(run.get("temperature")),
      seed=(run.get("seed")),
      max_tokens=(run.get("max_tokens")))
    out_rel = _result_rel(img["rel"], repeat)
    base = _run_dir(run_id)
    raw_path = os.path.join(base, "raw", os.path.splitext(out_rel)[0] + ".txt")
    os.makedirs((os.path.dirname(raw_path)), exist_ok=True)
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(resp.get("text") or resp.get("error") or "")
    if resp.get("error"):
        result = {'overall_status':"error",  'summary':"",  'scene':{},  'objects':[],  'parse_ok':False, 
         'raw':"",  '_meta':_meta(run, img, repeat, resp, error=(resp["error"]))}
    else:
        st = run.get("prompt_settings") or {}
        result = parse_result((resp["text"]), model=(run["model"]), img_w=w, img_h=h, mapping=(st.get("map") or None),
          output_mode=(st.get("output_mode", "fixed")),
          status_labels=(st.get("status_labels")))
        result["_meta"] = _meta(run, img, repeat, resp)
    out_path = os.path.join(base, "results", out_rel)
    os.makedirs((os.path.dirname(out_path)), exist_ok=True)
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, out_path)
    if result.get("objects"):
        ann_path = os.path.join(base, "annotated", os.path.splitext(out_rel)[0] + ".jpg")
        os.makedirs((os.path.dirname(ann_path)), exist_ok=True)
        try:
            draw_objects(img_path, (result["objects"]), ann_path, show_fields=(run.get("show_fields") or None))
        except Exception:
            pass
    return not resp.get("error")


def _meta(run, img, repeat, resp, error=None):
    m = {'run_id':run["id"], 
     'dataset':run["dataset"], 
     'image':img["rel"], 
     'repeat':repeat, 
     'prompt_name':run["prompt_name"], 
     'prompt_version':run["prompt_version"], 
     'model':run["model"], 
     'temperature':(run.get)("temperature"), 
     'seed':(run.get)("seed"), 
     'timestamp':(time.strftime)("%Y-%m-%d %H:%M:%S"), 
     'latency':(resp.get)("latency"), 
     'usage':(resp.get)("usage")}
    if error:
        m["error"] = error
    return m


_images_cache = FingerprintCache()

def list_run_images(run_id):
    """列出运行中每张图片及各次复现的结果状态。

    结果文件逐张读取开销大，按 (run.json mtime, results 目录指纹) 缓存：
    运行推进会写结果文件和 run.json，指纹变化自动重算。
    """
    run_json = os.path.join(_run_dir(run_id), "run.json")
    try:
        run_mtime = os.stat(run_json).st_mtime_ns
    except OSError:
        run_mtime = 0
    base = os.path.join(_run_dir(run_id), "results")
    fp = (run_mtime, fingerprint(base))

    def compute():
        run = _load_run(run_id)
        images = []
        for img in run.get("images_snapshot") or datasets.scan_images((run["dataset"]), split=(run.get("dataset_split"))):
            repeats = []
            for r in range(1, run["repeat"] + 1):
                p = None
                for cand in _result_candidates(img["rel"], r):
                    path = os.path.join(base, cand)
                    if os.path.exists(path):
                        p = path
                        break
                item = {'repeat':r, 
                 'exists':bool(p)}
                if p:
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            d = json.load(f)
                        item["overall_status"] = d.get("overall_status")
                        item["parse_ok"] = d.get("parse_ok")
                        item["object_count"] = len(d.get("objects", []))
                        item["object_names"] = [o.get("name") for o in d.get("objects", [])]
                        err = (d.get("_meta") or {}).get("error")
                        if err:
                            item["error"] = err
                    except Exception:
                        pass
                repeats.append(item)
            images.append({'rel':img["rel"],  'name':img["name"],  'repeats':repeats})
        return images

    return _images_cache.get(run_id, fp, compute)

def export_csv(run_id):
    """导出运行结果为 CSV（utf-8-sig，Excel 直接打开不乱码），返回文件路径"""
    import csv
    run = _load_run(run_id)
    rows = []
    for img in run.get("images_snapshot") or datasets.scan_images((run["dataset"]), split=(run.get("dataset_split"))):
        for r in range(1, run["repeat"] + 1):
            p = _existing_result_path(run_id, img["rel"], r)
            if not os.path.exists(p):
                pass
            else:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        d = json.load(f)
                except Exception:
                    continue

                else:
                    meta = d.get("_meta", {})
                    usage = meta.get("usage") or {}
                    rows.append([
                     img["rel"], r,
                     d.get("overall_status", ""),
                     "是" if d.get("parse_ok") else "否",
                     len(d.get("objects", [])),
                     "、".join((str(o.get("name")) for o in d.get("objects", []) if o.get("name"))),
                     (d.get("summary") or "").replace("\n", " ").strip(),
                     meta.get("model", ""), meta.get("latency", ""),
                     usage.get("prompt_tokens", ""), usage.get("completion_tokens", ""),
                     meta.get("timestamp", ""), (meta.get("error") or "").replace("\n", " ")])

        out = os.path.join(_run_dir(run_id), "export.csv")

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["图片","复现序号","整体状态","解析成功","目标数","目标列表",
         "总结", "模型", "耗时(秒)", "输入tokens", "输出tokens", "时间", "错误"])
        w.writerows(rows)
    return out


def _rel_from_result_name(filename):
    """results 目录里的结果文件名 → 原始相对图片路径。"""
    name = os.path.splitext(filename)[0]
    if "__r" not in name:
        return None
    rel = name.rsplit("__r", 1)[0]
    return rel or None


def reparse_results(run_id, backup=True):
    """用当前解析器重解析「接口成功但解析失败」的历史结果。

    只处理 _meta 无 error 且仍有 raw 的样本：这类是解析器容错不足导致的
    假失败，模型其实给了结论。原始 raw 原样保留，改动前的 JSON 先备份，
    便于核对与回退。
    """
    run = _load_run(run_id)
    st = run.get("prompt_settings") or {}
    base = _run_dir(run_id)
    results_dir = os.path.join(base, "results")
    backup_dir = None
    repaired = failed = 0
    details = []
    for dirpath, _, files in os.walk(results_dir):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, "r", encoding="utf-8") as f:
                old = json.load(f)
            if old.get("parse_ok") is not False:
                continue
            if (old.get("_meta") or {}).get("error"):
                failed += 1
                continue
            raw = old.get("raw") or ""
            rel = _rel_from_result_name(fn)
            if not raw or not rel:
                failed += 1
                continue
            rel_dir = os.path.relpath(dirpath, results_dir)
            if rel_dir != ".":
                rel = os.path.join(rel_dir, rel)
            try:
                (w, h) = get_image_size(image_file(run_id, rel))
            except Exception:
                (w, h) = (1, 1)
            fresh = parse_result(raw, model=run.get("model", ""), img_w=w, img_h=h,
                                 mapping=(st.get("map") or None),
                                 output_mode=st.get("output_mode", "fixed"),
                                 status_labels=st.get("status_labels"))
            if not fresh.get("parse_ok"):
                failed += 1
                continue
            if backup:
                if backup_dir is None:
                    backup_dir = os.path.join(base, "results_backup_" + time.strftime("%Y%m%d-%H%M%S"))
                target = os.path.join(backup_dir, os.path.relpath(path, results_dir))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                if not os.path.exists(target):
                    shutil.copy2(path, target)
            meta = dict(old.get("_meta") or {})
            meta["parse_repaired"] = time.strftime("%Y-%m-%d %H:%M:%S")
            fresh["_meta"] = meta
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(fresh, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            repaired += 1
            details.append({"image": rel, "objects": len(fresh.get("objects") or [])})
    if repaired:
        try:
            with open(_run_json_path(run_id), "r", encoding="utf-8") as f:
                current = json.load(f)
            _reconcile_counts(current)
            _save_run(current)
        except Exception:
            pass
    return {"run_id": run_id, "repaired": repaired, "still_failed": failed,
            "backup": backup_dir or "", "items": details}


def get_result(run_id, rel, repeat):
    for name in _result_candidates(rel, repeat):
        p = safe_path(_run_dir(run_id), "results", name)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise ValueError("结果不存在")


def result_file(run_id, rel, repeat, kind):
    """kind: results/annotated/raw，返回实际文件路径（不存在则 None）"""
    folder, ext = {'annotated':('annotated', '.jpg'), 
     'raw':('raw', '.txt')}.get(kind, ('results', '.json'))
    for name in _result_candidates(rel, repeat):
        p = safe_path(_run_dir(run_id), folder, os.path.splitext(name)[0] + ext)
        if os.path.exists(p):
            return p


def image_file(run_id, rel):
    """优先返回运行时原图快照；兼容升级前没有快照的历史运行。"""
    snapshot = safe_path(_run_dir(run_id), "images", rel)
    if os.path.isfile(snapshot):
        return snapshot
    run = _load_run(run_id)
    return datasets.image_path(run["dataset"], rel)


def diff_runs(run1_id, run2_id):
    """逐图对比两个运行的结果差异，用于版本迭代时检测识别变化。"""
    run1 = _load_run(run1_id)
    run2 = _load_run(run2_id)
    images1 = {im["rel"]: im for im in list_run_images(run1_id)}
    images2 = {im["rel"]: im for im in list_run_images(run2_id)}
    common = sorted(set(images1) & set(images2))
    only1 = sorted(set(images1) - set(images2))
    only2 = sorted(set(images2) - set(images1))
    items = []
    changed_count = 0
    for rel in common:
        r1 = r2 = None
        for rep_item in images1[rel].get("repeats", []):
            if rep_item.get("exists"):
                if not rep_item.get("error"):
                    try:
                        r1 = get_result(run1_id, rel, rep_item["repeat"])
                        break
                    except Exception:
                        pass

        for rep_item in images2[rel].get("repeats", []):
            if rep_item.get("exists"):
                if not rep_item.get("error"):
                    try:
                        r2 = get_result(run2_id, rel, rep_item["repeat"])
                        break
                    except Exception:
                        pass

        s1 = r1.get("overall_status") if r1 else None
        s2 = r2.get("overall_status") if r2 else None
        objs1 = [o for o in (r1 or {}).get("objects", []) or [] if o.get("name") or o.get("labelName")]
        objs2 = [o for o in (r2 or {}).get("objects", []) or [] if o.get("name") or o.get("labelName")]

        def norm_label(o):
            raw = o.get("name") or o.get("labelName") or ""
            return str(raw).strip().replace(" ", "").replace("\u3000", "")

        labels1 = sorted((norm_label(o) for o in objs1))
        labels2 = sorted((norm_label(o) for o in objs2))
        status_changed = s1 != s2
        obj_count_changed = len(objs1) != len(objs2)
        labels_changed = labels1 != labels2
        changed = status_changed or obj_count_changed or labels_changed
        if changed:
            changed_count += 1
        change_types = []
        if status_changed:
            change_types.append("状态变化")
        if obj_count_changed:
            change_types.append("目标数变化")
        if labels_changed:
            change_types.append("标签变化")
        items.append({'image':rel, 
         'v1_status':s1, 
         'v2_status':s2,  'v1_object_count':len(objs1), 
         'v2_object_count':len(objs2),  'v1_labels':labels1, 
         'v2_labels':labels2,  'changed':changed, 
         'change_types':change_types})

    return {'run1':{'id':run1_id, 
      'prompt_name':(run1.get)("prompt_name"),  'prompt_version':(run1.get)("prompt_version"), 
      'dataset':(run1.get)("dataset")}, 
     'run2':{'id':run2_id, 
      'prompt_name':(run2.get)("prompt_name"),  'prompt_version':(run2.get)("prompt_version"), 
      'dataset':(run2.get)("dataset")}, 
     'total_common':len(common), 
     'changed':changed_count,  'unchanged':(len(common)) - changed_count, 
     'only_in_run1':only1, 
     'only_in_run2':only2,  'items':items}
