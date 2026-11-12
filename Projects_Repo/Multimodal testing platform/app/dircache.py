"""目录指纹缓存：数据没变时复用上次的计算结果。

指纹 = (匹配文件数, 最新 mtime_ns)。文件内容修改、新增、删除都会改变指纹，
因此写路径上无需手动失效。指纹只做 stat，比逐个读 JSON 便宜几个数量级，
专门解决工作台等聚合接口反复全量扫描目录的卡顿。
"""
import json, os, threading

def fingerprint(root, suffix=".json", exclude_names=(), recursive=False):
    """目录内容指纹：(匹配文件数, 最新 mtime_ns)。目录不存在返回 (0, 0)。

    suffix 为 None 时统计所有文件；exclude_names 按文件名排除。
    """
    count = 0
    latest = 0
    if not os.path.isdir(root):
        return (0, 0)
    excluded = set(exclude_names or ())
    if recursive:
        for (dirpath, _, files) in os.walk(root):
            for fn in files:
                if suffix and not fn.endswith(suffix):
                    continue
                if fn in excluded:
                    continue
                try:
                    m = os.stat(os.path.join(dirpath, fn)).st_mtime_ns
                except OSError:
                    continue
                count += 1
                if m > latest:
                    latest = m

    else:
        for fn in os.listdir(root):
            if suffix and not fn.endswith(suffix):
                continue
            if fn in excluded:
                continue
            try:
                m = os.stat(os.path.join(root, fn)).st_mtime_ns
            except OSError:
                continue
            count += 1
            if m > latest:
                latest = m

    return (
     count, latest)


def subfile_fingerprint(root, subname):
    r"""一级子目录中同名文件的指纹，如 runs/*\/run.json、judgments/*\/job.json。"""
    count = 0
    latest = 0
    if not os.path.isdir(root):
        return (0, 0)
    for entry in os.listdir(root):
        p = os.path.join(root, entry, subname)
        try:
            m = os.stat(p).st_mtime_ns
        except OSError:
            continue

        count += 1
        if m > latest:
            latest = m
    return (count, latest)


class FingerprintCache:
    """按 key 缓存计算结果；指纹一致直接复用，变化才重算。

    返回值经 JSON 深拷贝，调用方修改不会污染缓存。
    compute 在锁外执行，极端并发下可能重复计算，但结果幂等可自愈。
    """

    def __init__(self):
        self._items = {}
        self._lock = threading.Lock()

    def get(self, key, fp, compute):
        with self._lock:
            item = self._items.get(key)
            if item:
                if item[0] == fp:
                    return json.loads(json.dumps((item[1]), ensure_ascii=False))
        data = compute()
        with self._lock:
            self._items[key] = (
             fp, data)
        return json.loads(json.dumps(data, ensure_ascii=False))

    def invalidate(self, key=None):
        with self._lock:
            if key is None:
                self._items.clear()
            else:
                self._items.pop(key, None)
