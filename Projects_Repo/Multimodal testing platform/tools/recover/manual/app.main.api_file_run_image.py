def api_file_run_image(run_id: str, rel: str):
    try:
        p = runner.image_file(run_id, rel)
        if not os.path.isfile(p):
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, 404)
