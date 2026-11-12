def api_file_annotated(run_id: str, rel: str, repeat: int = 1):
    try:
        p = runner.result_file(run_id, rel, repeat, "annotated")
        if not p:
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, 404)
