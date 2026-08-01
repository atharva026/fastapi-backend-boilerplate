import redis.asyncio as aioredis
from src.app.core.config import config
from src.app.core.logging import get_logger

logger = get_logger(__name__)

# Global variable to hold the Redis connection pool
_redis_pool: aioredis.ConnectionPool | None = None

async def redis_on_startup() -> None:
    """Initialize the Redis connection pool on application startup."""
    global _redis_pool
    _redis_pool = aioredis.ConnectionPool(
        host=config.REDIS_CONFIG.redis_host,
        port=config.REDIS_CONFIG.redis_port,
        db=config.REDIS_CONFIG.redis_db,
        max_connections=20,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
        decode_responses=True,
    )

    # Verify connection eagerly — fail loud at startup
    async with aioredis.Redis(connection_pool=_redis_pool) as client:
        await client.ping()

    auth_part = "no-auth"

    if config.REDIS_CONFIG.redis_username and config.REDIS_CONFIG.redis_password:
        auth_part = f"{config.REDIS_CONFIG.redis_username}:****"
    elif config.REDIS_CONFIG.redis_password:
        auth_part = "****"

    logger.info(
        "Redis connection pool initialized at redis://%s@%s:%d/%d",
        auth_part,
        config.REDIS_CONFIG.redis_host,
        config.REDIS_CONFIG.redis_port,
        config.REDIS_CONFIG.redis_db,
    )

async def redis_on_shutdown() -> None:
    """Close the Redis connection pool on application shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis connection pool closed")

async def get_redis() -> aioredis.Redis:
    """Get a Redis client instance from the connection pool. Raises an error if the pool is not initialized."""
    if _redis_pool is None:
        raise RuntimeError("Redis pool not initialized")
    return aioredis.Redis(connection_pool=_redis_pool)
