from fastapi import Depends
import redis.asyncio as redis
from datetime import datetime, timezone

from src.app.core.redis import get_redis

import logging
logger = logging.getLogger(__name__)

REFRESH_PREFIX = "refresh:"       # allowlist  — present = valid
ACCESS_BLOCK_PREFIX = "blocked:"  # blocklist  — present = revoked

class TokenStore:
    """
    A token store that manages refresh token allowlist and access token blocklist using Redis.
    - Refresh tokens are stored in an allowlist: if the token's jti is present in Redis, it's valid; otherwise, it's revoked.
    - Access tokens are stored in a blocklist: if the token's jti is present in Redis, it's revoked; otherwise, it's valid.
    """

    def __init__(self, redis: redis.Redis):
        self.redis = redis

    # helpers 
    @staticmethod
    def _ttl(expires_at: datetime) -> int:
        """Calculate the TTL (time to live) in seconds for a token based on its expiration time."""

        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        return max(ttl, 0)

    # refresh token allowlist
    async def store_refresh_token(
        self,
        user_id: str,
        jti: str,
        expires_at: datetime
    ) -> None:
        """Store the refresh token's jti in Redis with an expiration time equal to the token's remaining lifetime."""

        ttl = self._ttl(expires_at)
        if ttl > 0:
            await self.redis.setex(f"{REFRESH_PREFIX}{user_id}:{jti}", ttl, "1")
            logger.info("Stored refresh token jti=%s user=%s ttl=%ss", jti, user_id, ttl)

    async def is_refresh_token_valid(
        self,
        user_id: str,
        jti: str
    ) -> bool:
        """
        Check if the refresh token's jti exists in Redis. 
        Return True if it exists (valid), or False if it does not exist (revoked).
        """

        exists = await self.redis.exists(f"{REFRESH_PREFIX}{user_id}:{jti}")
        return exists == 1

    async def revoke_refresh_token(
        self,
        user_id: str,
        jti: str
    ) -> None:
        """Revoke a specific refresh token by deleting its jti from Redis."""

        await self.redis.delete(f"{REFRESH_PREFIX}{user_id}:{jti}")
        logger.info("Revoked refresh token jti=%s user=%s", jti, user_id)

    async def revoke_all_refresh_tokens(
        self,
        user_id: str
    ) -> None:
        """Logout from all devices. Revoke all refresh tokens for the user by deleting all keys with the user's prefix from Redis."""
        async for key in self.redis.scan_iter(f"{REFRESH_PREFIX}{user_id}:*"):
            await self.redis.delete(key)
        logger.info("Revoked all refresh tokens for user=%s", user_id)

    # access token blocklist
    async def blocklist_access_token(
        self,
        jti: str,
        expires_at: datetime
    ) -> None:
        """Blocklist an access token by storing its jti in Redis with an expiration time equal to the token's remaining lifetime."""
        ttl = self._ttl(expires_at)
        if ttl > 0:
            await self.redis.setex(f"{ACCESS_BLOCK_PREFIX}{jti}", ttl, "1")
            logger.info("Blocklisted access token jti=%s ttl=%ss", jti, ttl)

    async def is_access_token_blocked(
        self,
        jti: str
    ) -> bool:
        """
        Check if the access token's jti exists in Redis. 
        Return True if it exists (revoked), or False if it does not exist (valid).
        """
        exists = await self.redis.exists(f"{ACCESS_BLOCK_PREFIX}{jti}")
        return exists == 1
    
async def get_token_store(
    redis_client: redis.Redis = Depends(get_redis)
) -> TokenStore:
    return TokenStore(redis_client)