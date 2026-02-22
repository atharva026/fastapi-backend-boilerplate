from fastapi import Request
from urllib.parse import urlparse
from src.app.core.config import config

ALLOWED_DOMAINS = {
    "prod": {
        "fastapi.com",
        "admin.fastapi.com",
    },
    "staging": {
        "staging.fastapi.com",
        "staging.admin.fastapi.com",
    },
}

def extract_hostname(origin: str) -> str | None:
    try:
        parsed = urlparse(origin)
        return parsed.hostname
    except Exception:
        return None
    
def get_cookie_options(request: Request) -> dict:
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    domain = None

    if origin and config.ENVIRONMENT in ALLOWED_DOMAINS:
        hostname = extract_hostname(origin)

        if hostname in ALLOWED_DOMAINS[config.ENVIRONMENT]:
            domain = hostname

    if config.ENVIRONMENT in ["prod", "staging"]:
        samesite = "strict"
        secure = True
    else:
        # Development
        samesite = "lax"  #"none"
        secure = True

    return {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "domain": domain
    }

