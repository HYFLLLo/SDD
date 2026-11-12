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
