"""Simple Redis-backed fixed-window rate limiter.

Design:
- Keyed by a caller-provided string (e.g., tenant:user:path)
- Uses Redis INCR and EXPIRE to count requests in the current window
- Returns True if under limit; False otherwise

If Redis is unavailable, the functions raise RuntimeError so callers can decide fallback behavior.
"""

from __future__ import annotations

from typing import Final

from redis import Redis


def sliding_window_allow(redis_url: str, key: str, limit: int, window_seconds: int) -> bool:
    """Sliding window rate limit using Redis sorted set.

    Stores timestamps (ms) in ZSET at `key`. Removes entries older than window, counts remaining,
    and allows if count < limit. Uses a single pipeline for atomicity.
    """
    if limit <= 0:
        return False
    if window_seconds <= 0:
        window_seconds = 1

    now_ms: int
    try:
        import time

        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        cutoff = now_ms - window_ms
        client: Final[Redis] = Redis.from_url(redis_url, decode_responses=True)
        with client.pipeline() as pipe:
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            removed, count = pipe.execute()
        allowed = int(count) < limit
        if allowed:
            with client.pipeline() as pipe:
                pipe.zadd(key, {str(now_ms): now_ms})
                pipe.expire(key, window_seconds)
                pipe.execute()
        client.close()
        return allowed
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Sliding window rate limiting failed: {exc}") from exc


def increment_and_check(redis_url: str, key: str, limit: int, window_seconds: int) -> bool:
    """Increment the request counter and check if within the limit.

    Args:
        redis_url: Redis connection URL
        key: Unique rate limit key (e.g., rl:tenant:user:path)
        limit: Maximum number of requests allowed in the window
        window_seconds: Window size in seconds

    Returns:
        True if the request is allowed (under limit), False if rate limit exceeded

    Raises:
        RuntimeError: If Redis is not reachable or an operation fails
    """
    if limit <= 0:
        return False
    if window_seconds <= 0:
        window_seconds = 1

    try:
        client: Final[Redis] = Redis.from_url(redis_url, decode_responses=True)
        with client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = pipe.execute()
        client.close()
        try:
            current = int(count)
        except (TypeError, ValueError):
            current = limit + 1
        return current <= limit
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Rate limiting failed: {exc}") from exc


