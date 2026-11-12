def api_file_truth(task: str, rel: str):
    """标注页面显示用：直接返回数据集中的原图"""
    try:
        p = truth.image_path(task, rel)
        if not os.path.exists(p):
            _err(FileNotFoundError(rel), 404)
        return FileResponse(p)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, 404)
