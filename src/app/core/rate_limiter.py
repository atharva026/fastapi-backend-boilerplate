import uuid
from time import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Request
import redis.asyncio as aioredis

from src.app.core.logging import get_logger
logger = get_logger(__name__)

@dataclass(frozen=True)
class RateLimitConfig:
    limit: int
    window_seconds: int

@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    retry_after: Optional[int] = None

# Default configurations
AUTH_RATE_LIMIT = RateLimitConfig(
    limit=10,
    window_seconds=60,
)

PUBLIC_RATE_LIMIT = RateLimitConfig(
    limit=60,
    window_seconds=60,
)

PRIVATE_RATE_LIMIT = RateLimitConfig(
    limit=30,
    window_seconds=60,
)

EMAIL_RATE_LIMIT = RateLimitConfig(
    limit=2,
    window_seconds=60,
)

class RedisRateLimiter:
    """
    Sliding-window rate limiter implemented with Redis sorted sets (ZSET).
    Uses a Lua script to perform the following atomically:
      - Remove entries older than the sliding window
      - Count current entries
      - If under limit, add the current timestamp as a new member and return allowed
      - If over limit, return not allowed and the reset time (ms)
    This implementation is accurate (sliding window) and safe for high concurrency because
    operations are performed inside a single Redis script call.
    """

    LUA_SCRIPT = r"""
    local key = KEYS[1]
    local window = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local member = ARGV[3]
    local expire = tonumber(ARGV[4])
    -- Redis server time (milliseconds)
    local t = redis.call('TIME')
    local now = t[1] * 1000 + math.floor(t[2] / 1000)
    -- remove old entries
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local current = redis.call('ZCARD', key)
    if current < limit then
        -- allow: add the current request
        redis.call('ZADD', key, now, member)
        redis.call('EXPIRE', key, expire)
        return {1, limit - current - 1}
    else
        -- denied. find the oldest member score to calculate reset
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        local reset = 0
        if oldest[2] then
            reset = window - (now - tonumber(oldest[2]))
            if reset < 0 then reset = 0 end
        end
        return {0, reset}
    end
    """

    def __init__(self, redis: aioredis.Redis, fail_open: bool = True):
        self.redis = redis
        self.fail_open = fail_open
        self.last_log_time = 0
        self._script_sha = None

    async def _load_script(self) -> None:
        self._script_sha = await self.redis.script_load(self.LUA_SCRIPT)

    async def _execute_script(
        self,
        key: str,
        window_ms: int,
        limit: int,
        member: str,
        expire: int,
    ):
        if self._script_sha is None:
            await self._load_script()

        try:
            return await self.redis.evalsha(
                self._script_sha,
                1,
                key,
                window_ms,
                limit,
                member,
                expire,
            )

        except aioredis.ResponseError as exc:
            # Redis restarted and lost cached scripts.
            if "NOSCRIPT" not in str(exc):
                raise

            logger.warning("Redis Lua script cache was cleared. Reloading...")

            await self._load_script()

            return await self.redis.evalsha(
                self._script_sha,
                1,
                key,
                window_ms,
                limit,
                member,
                expire,
            )

    async def allow_request(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> RateLimitResult:
        """
        Attempt to consume a single slot for the given key.
        Returns (allowed: bool, value: int)
          - if allowed == True: value is remaining tokens
          - if allowed == False: value is reset time in seconds
        """
        # sliding window uses milliseconds
        window_ms = window_seconds * 1000
        member = f"{window_seconds}-{uuid.uuid4()}"
        expire = window_seconds * 2

        try:
            result = await self._execute_script(
                key,
                window_ms,
                limit,
                member,
                expire,
            )

            allowed = bool(result[0])
            value = int(result[1])

            if allowed:
                return RateLimitResult(
                    allowed=True,
                    remaining=value,
                    limit=limit
                )

            retry_after = (value + 999) // 1000

            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                retry_after=retry_after,
            )

        except Exception as exc:
            now = time.time()
            if now - self.last_log_time >= 60:
                logger.error("Rate limiter error for key %s: %s", key, exc)
                self.last_log_time = now

            # Fail-open vs fail-closed: default to fail-open for availability

            if self.fail_open:
                return RateLimitResult(
                    allowed=True,
                    remaining=-1,
                )

            # If fail-closed, treat as blocked
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=window_seconds,
            )


def get_client_ip_from_request(request: Request) -> str:
    """
    Extract the real client IP from the request.
    - Check X-Forwarded-For (the left-most entry is the original client)
    - Check X-Real-IP
    - Fall back to request.client.host
    Important: In production ensure your reverse proxy/load-balancer sets these headers and that
    FastAPI/Uvicorn is configured to trust the proxy (or use ProxyHeaders middleware if needed).
    """
    # Prefer X-Forwarded-For (may contain comma separated list)
    xff = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
    if xff:
        # left-most IP is the original client
        return xff.split(",")[0].strip()

    # Next, X-Real-IP
    xr = request.headers.get("X-Real-IP") or request.headers.get("x-real-ip")
    if xr:
        return xr.strip()

    # Fallback to ASGI client
    if request.client:
        return request.client.host

    return "127.0.0.1"

__all__ = [
    "RedisRateLimiter",
    "RateLimitConfig",
    "RateLimitResult",
    "AUTH_RATE_LIMIT",
    "PUBLIC_RATE_LIMIT",
    "PRIVATE_RATE_LIMIT",
    "get_client_ip_from_request",
]