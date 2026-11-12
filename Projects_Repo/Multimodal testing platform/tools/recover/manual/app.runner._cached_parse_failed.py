def _cached_parse_failed(run_id):
    base = os.path.join(_run_dir(run_id), "results")
    return _parse_failed_cache.get(run_id, fingerprint(base), lambda: _scan_parse_failed(run_id))
