def build_example(
    *,
    summary: str,
    code: str,
    message: str,
):
    return {
        "summary": summary,
        "value": {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    }
