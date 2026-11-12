@app.post("/api/runs/{run_id}/reparse")
def api_reparse_run(run_id: str):
    try:
        return runner.reparse_results(run_id)
    except Exception as e:
        _err(e, 404)
