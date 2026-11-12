def api_file_dataset(dataset: str, rel: str):
    try:
        p = datasets.image_path(dataset, rel)
        if not os.path.exists(p):
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, 404)
