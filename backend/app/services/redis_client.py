from typing import Optional

from redis import asyncio as aioredis


_redis: Optional[aioredis.Redis] = None


async def create_redis_client(url: str) -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(url, decode_responses=True)
        # Warmup ping to validate connection early
        await _redis.ping()
    return _redis


async def get_redis_client() -> aioredis.Redis:
    assert _redis is not None, "Redis client has not been initialized"
    return _redis


async def close_redis_client() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


