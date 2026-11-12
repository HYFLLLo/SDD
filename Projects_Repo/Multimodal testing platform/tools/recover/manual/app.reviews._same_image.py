def _same_image(source_run_id, target_run_id, rel):
    from . import runner
    try:
        source = runner.image_file(source_run_id, rel)
        target = runner.image_file(target_run_id, rel)
        if os.path.getsize(source) != os.path.getsize(target):
            return False
        def digest(path):
            value = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1048576), b""):
                    value.update(chunk)
            return value.digest()
        return digest(source) == digest(target)
    except Exception:
        return False
