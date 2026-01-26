from fastapi import Request
from src.app.core.config import config

def get_cookie_options(request: Request) -> dict:
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    domain = None

    if config.ENV in ["production", "development"]:
        if "staging.admin.fastapi.com" in origin:
            domain = "staging.admin.fastapi.com"
        elif "staging.fastapi.com" in origin:
            domain = "staging.fastapi.com"
        elif "admin.fastapi.com" in origin:
            domain = "admin.fastapi.com"
        elif "fastapi.com" in origin:
            domain = "fastapi.com"
        # otherwise: leave domain=None (browser will default)

    # if config.ENV in ["production", "staging"]:
    #     samesite = "none"
    #     secure = True
    # else:
    #     # Development
    samesite = "none"
    secure = True

    return {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "domain": domain
    }

