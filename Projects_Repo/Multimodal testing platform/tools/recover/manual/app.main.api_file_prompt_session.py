def api_file_prompt_session(session_id: str, name: str):
    """提示词生成会话的附件图片"""
    try:
        p = prompt_ai.attachment_file(session_id, name)
        if not os.path.isfile(p):
            _err(FileNotFoundError(name), 404)
        return FileResponse(p)
    except HTTPException:
        raise
    except Exception as e:
        _err(e, 404)
