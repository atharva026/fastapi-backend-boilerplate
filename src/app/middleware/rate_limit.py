import time
from dataclasses import dataclass
from typing import Literal

from starlette.types import ASGIApp, Receive, Scope, Send, Message
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette import status

from src.app.core.rate_limiter import (
    RedisRateLimiter,
    RateLimitResult,
    AUTH_RATE_LIMIT,
    PUBLIC_RATE_LIMIT,
    PRIVATE_RATE_LIMIT,
    EMAIL_RATE_LIMIT,
    get_client_ip_from_request,
)

IpKeyPrefix = Literal["auth", "public", "private"]
SKIP_RATE_LIMIT_PATHS = frozenset({
    "/", 
    "/health"
})

# Data

@dataclass
class RateLimitInfo:
    """Carries rate limit context from the check site to the response headers."""
    limit: int
    remaining: int
    reset_at: int # Unix timestamp (seconds) when the window resets
    retry_after: int | None = None

# Builders

def _build_rate_limit_info(result: RateLimitResult, window_seconds: int) -> RateLimitInfo:
    now = int(time.time())
    reset_at = now + (result.retry_after or 0) if not result.allowed else now + window_seconds
    return RateLimitInfo(
        limit=result.limit,
        remaining=result.remaining,
        reset_at=reset_at,
        retry_after=result.retry_after if not result.allowed else None,
    )

def _rate_limit_headers(info: RateLimitInfo) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(info.limit),
        "X-RateLimit-Remaining": str(max(info.remaining, 0)),
        "X-RateLimit-Reset": str(info.reset_at),
    }
    if info.retry_after is not None:
        headers["Retry-After"] = str(info.retry_after)
    return headers

def _too_many_requests(info: RateLimitInfo) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": {
                "code": "TOO_MANY_REQUESTS",
                "message": "Too many requests. Please try again in a few seconds.",
                "reset": info.retry_after,
            },
        },
        headers=_rate_limit_headers(info),
    )

def _unauthorized(code: str, message: str, info: RateLimitInfo | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "error": {"code": code, "message": message}},
        headers=_rate_limit_headers(info) if info else {},
    )

# Core rate-limit primitive

async def _check_ip_limit(
    limiter: RedisRateLimiter | None,
    ip: str,
    limit: int,
    window_seconds: int,
    prefix: IpKeyPrefix
) -> RateLimitResult | None:
    if limiter is None:
        return None
    key = f"rl:ip:{prefix}:{ip}"   # e.g. rl:ip:auth:1.2.3.4 / rl:ip:public:1.2.3.4
    return await limiter.allow_request(key, limit=limit, window_seconds=window_seconds)

async def _enforce_ip_limit(
    limiter: RedisRateLimiter | None,
    ip: str,
    limit: int,
    window_seconds: int,
    prefix: IpKeyPrefix
) -> tuple[bool, RateLimitInfo | None]:
    """
    Run an IP-based rate limit check and return (denied, info).

    Returns:
        (True,  info)  — request was denied; caller should send _too_many_requests(info)
        (False, info)  — request allowed with a live limiter; inject headers
        (False, None)  — no limiter configured; pass through without headers
    """
    result = await _check_ip_limit(limiter, ip, limit, window_seconds, prefix)
    if result is None:
        return False, None
    info = _build_rate_limit_info(result, window_seconds)
    return not result.allowed, info

# ASGI send wrapper

def _inject_headers_into_send(send: Send, extra_headers: dict[str, str]) -> Send:
    """Inject rate-limit headers into http.response.start without buffering the body."""
    async def send_with_headers(message: Message) -> None:
        if message["type"] == "http.response.start":
            existing_headers = list(message.get("headers", []))

            for name, value in extra_headers.items():
                existing_headers.append(
                    (name.encode("latin-1"), value.encode("latin-1"))
                )
            message = {**message, "headers": existing_headers}

        await send(message)
    return send_with_headers

def _patched_send(send: Send, info: RateLimitInfo | None) -> Send:
    """Return a header-injecting send when we have rate-limit info, raw send otherwise."""
    if info is None:
        return send
    return _inject_headers_into_send(send, _rate_limit_headers(info))

# Middleware

class RateLimitMiddleware:
    """
    Pure ASGI rate-limiting middleware.

    Always injects X-RateLimit-* headers on allowed requests.
    Adds Retry-After on 429. Adds limit headers on 401 (post-IP-check).

    Decision table & Redis key namespacing:
    ┌──────────────────────────┬─────────────────────┬────────────────────────────────────────┐
    │ Endpoint / State         │ Redis key           | Limit applied                          │
    ├──────────────────────────┼─────────────────────┼────────────────────────────────────────┤
    │ Auth endpoint            │ rl:ip:auth:{ip}     | IP  — AUTH_RATE_LIMIT   (5/min)        │
    │ Public endpoint          │ rl:ip:public:{ip}   | IP  — PUBLIC_RATE_LIMIT (60/min)       │
    │ Private + auth_failed    │ rl:ip:private:{ip}  | IP  — PRIVATE_RATE_LIMIT → then 401    │
    │ Private + authenticated  │ rl:user:{user_id}   | User — PRIVATE_RATE_LIMIT (30/min)     │
    └──────────────────────────┴─────────────────────┴────────────────────────────────────────┘
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope) #, receive, send) # no receive/send

        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        limiter: RedisRateLimiter | None = getattr(request.app.state, "rate_limiter", None)
        ip = get_client_ip_from_request(request)

        response = await self._route(scope, limiter, ip, send)

        if response is not None:
            await response(scope, receive, send)
        else:
            patched_send = scope["state"].pop("rate_limit_send_patch", send)
            await self.app(scope, receive, patched_send)

    async def _route(
        self,
        scope: Scope,
        limiter: RedisRateLimiter | None,
        ip: str,
        send: Send,
    ) -> Response | None:
        """
        Determine the correct rate-limit action for this request.
        Returns a Response to short-circuit (429 / 401), or None to continue
        """
        state = scope.get("state", {})
        is_public: bool = state.get("is_public", False)
        is_auth_ep: bool = state.get("is_auth_endpoint", False)
        is_email_ep: bool = state.get("is_email_endpoint", False)
        auth_failed: bool = state.get("auth_failed", False)
        user_id: str | None = state.get("user_id", None)

        if scope["path"] in SKIP_RATE_LIMIT_PATHS:   # early exit, zero Redis calls
            return None
        
        # Email endpoints
        if is_public and is_email_ep:
            return await self._handle_ip_limited(
                scope, send, limiter, ip,
                EMAIL_RATE_LIMIT.limit, 
                EMAIL_RATE_LIMIT.window_seconds,
                prefix="email",
            )
    
        if is_public and is_auth_ep:
            return await self._handle_ip_limited(
                scope,
                send,
                limiter, 
                ip, 
                AUTH_RATE_LIMIT.limit, 
                AUTH_RATE_LIMIT.window_seconds,
                prefix="auth",
            )

        if is_public:
            return await self._handle_ip_limited(
                scope,
                send,
                limiter, 
                ip, 
                PUBLIC_RATE_LIMIT.limit, 
                PUBLIC_RATE_LIMIT.window_seconds,
                prefix="public",
            )

        if auth_failed:
            return await self._handle_auth_failed(
                scope, 
                limiter, 
                ip, 
                prefix="private"
            ) # auth_failed always returns a Response — no send needed

        if user_id:
            return await self._handle_user_limited(
                scope, send, limiter, user_id 
            )

        return None

    async def _handle_ip_limited(
        self,
        scope: Scope,
        send: Send,
        limiter: RedisRateLimiter | None,
        ip: str,
        limit: int,
        window_seconds: int,
        prefix: IpKeyPrefix,
    ) -> Response | None:
        """Apply an IP-based limit; inject headers on success, 429 on denial."""
        denied, info = await _enforce_ip_limit(limiter, ip, limit, window_seconds, prefix)
        if denied:
            return _too_many_requests(info)

        # Store a real callable, wrapping the live send
        scope["state"]["rate_limit_send_patch"] = _patched_send(send, info)

        return None

    async def _handle_auth_failed(
        self,
        scope: Scope,
        limiter: RedisRateLimiter | None,
        ip: str,
        prefix: IpKeyPrefix,
    ) -> Response:
        """
        Fallback IP limit for unauthenticated private requests, then 401.
        Uses the private bucket — auth-failed probes shouldn't consume auth slots.
        """
        denied, info = await _enforce_ip_limit(
            limiter,
            ip, 
            PRIVATE_RATE_LIMIT.limit, 
            PRIVATE_RATE_LIMIT.window_seconds,
            prefix
        )
        if denied:
            return _too_many_requests(info)

        state = scope.get("state", {})
        code: str = state.get("auth_error", "NOT_AUTHENTICATED")
        message: str = state.get("auth_error_message", "Not authenticated")
  
        return _unauthorized(code, message, info) # always returns a Response — no send patching needed

    async def _handle_user_limited(
        self,
        scope: Scope,
        send: Send,
        limiter: RedisRateLimiter | None,
        user_id: str,
    ) -> Response | None:
        """Apply a per-user limit; inject headers on success, 429 on denial."""
        if limiter is None:
            return None
        result = await limiter.allow_request(
            f"rl:user:{user_id}",
            PRIVATE_RATE_LIMIT.limit,
            PRIVATE_RATE_LIMIT.window_seconds
        )
        info = _build_rate_limit_info(result, PRIVATE_RATE_LIMIT.window_seconds)
        if not result.allowed:
            return _too_many_requests(info)
        
        # Store a real callable, not the info object
        scope["state"]["rate_limit_send_patch"] = _patched_send(send, info)

        return None
