"""Short-term memory module using Redis for session storage."""

import logging
from typing import Any, cast

import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SessionData(BaseModel):
    """Session data model for validation."""

    data: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=lambda: __import__("time").time())
    last_accessed: float = Field(default_factory=lambda: __import__("time").time())


class ShortTermMemory:
    """Redis-based short-term memory for session management."""

    def __init__(self, redis_url: str | None = None):
        """Initialize Redis connection.

        Args:
            redis_url: Redis connection URL. If None, uses REDIS_URL env var.
        """
        self.redis_url = redis_url
        self._client: redis.Redis | None = None
        self._connection_error = False

    async def _get_client(self) -> redis.Redis:
        """Get Redis client, creating connection if needed.

        Returns:
            Redis client instance

        Raises:
            RuntimeError: If Redis connection cannot be established
        """
        if self._client is None or self._connection_error:
            try:
                if self.redis_url is None:
                    import os

                    self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

                client_any: Any = redis.from_url(  # type: ignore[no-untyped-call]
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                client: redis.Redis = cast(redis.Redis, client_any)
                self._client = client

                # Test connection
                await client.ping()
                self._connection_error = False
                logger.info("Redis connection established successfully")

            except Exception as e:
                self._connection_error = True
                error_msg = f"Failed to connect to Redis: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        if self._client is None:
            raise RuntimeError("Redis client is not initialized")
        return self._client

    async def save_session(self, key: str, value: dict[str, Any], expiry: int = 3600) -> bool:
        """Save session data to Redis with expiry.

        Args:
            key: Session identifier
            value: Session data dictionary
            expiry: Expiry time in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If key is empty or expiry is negative
            RuntimeError: If Redis operation fails
        """
        if not key or not key.strip():
            raise ValueError("Session key cannot be empty")

        if expiry < 0:
            raise ValueError("Expiry time cannot be negative")

        try:
            client = await self._get_client()

            # Create session data with metadata
            session_data = SessionData(data=value)
            serialized_data = session_data.model_dump_json()

            # Save to Redis with expiry
            result = await client.setex(key, expiry, serialized_data)

            if result:
                logger.debug(f"Session saved successfully")
                return True
            else:
                logger.warning("Failed to save session")
                return False

        except redis.RedisError as e:
            error_msg = f"Redis error saving session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error saving session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def get_session(self, key: str) -> dict[str, Any] | None:
        """Retrieve session data from Redis.

        Args:
            key: Session identifier

        Returns:
            Session data dictionary or None if not found/expired

        Raises:
            ValueError: If key is empty
            RuntimeError: If Redis operation fails
        """
        if not key or not key.strip():
            raise ValueError("Session key cannot be empty")

        try:
            client = await self._get_client()

            # Get session data from Redis
            serialized_data = await client.get(key)

            if serialized_data is None:
                logger.debug("Session not found or expired")
                return None

            # Deserialize and validate session data
            try:
                session_data = SessionData.model_validate_json(serialized_data)

                # Update last accessed time
                session_data.last_accessed = __import__("time").time()
                updated_data = session_data.model_dump_json()

                # Refresh expiry (get current TTL and reset)
                ttl = await client.ttl(key)
                if ttl > 0:
                    await client.setex(key, ttl, updated_data)

                logger.debug(f"Session retrieved successfully: {key}")
                return session_data.data

            except Exception as e:  # noqa: BLE001
                logger.warning(f"Invalid session data format: {e}")
                # Clean up corrupted data
                await self.delete_session(key)
                return None

        except redis.RedisError as e:
            error_msg = f"Redis error retrieving session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error retrieving session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def delete_session(self, key: str) -> bool:
        """Delete session data from Redis.

        Args:
            key: Session identifier

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If key is empty
            RuntimeError: If Redis operation fails
        """
        if not key or not key.strip():
            raise ValueError("Session key cannot be empty")

        try:
            client = await self._get_client()

            # Delete session from Redis
            result = await client.delete(key)

            if result > 0:
                logger.debug("Session deleted successfully")
                return True
            else:
                logger.debug("Session not found for deletion")
                return False

        except redis.RedisError as e:
            error_msg = f"Redis error deleting session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error deleting session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def session_exists(self, key: str) -> bool:
        """Check if session exists in Redis.

        Args:
            key: Session identifier

        Returns:
            True if session exists, False otherwise

        Raises:
            ValueError: If key is empty
            RuntimeError: If Redis operation fails
        """
        if not key or not key.strip():
            raise ValueError("Session key cannot be empty")

        try:
            client = await self._get_client()
            exists_count: int = await client.exists(key)
            return bool(exists_count > 0)

        except redis.RedisError as e:
            error_msg = f"Redis error checking session existence: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error checking session existence: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def get_session_ttl(self, key: str) -> int | None:
        """Get remaining time-to-live for a session.

        Args:
            key: Session identifier

        Returns:
            TTL in seconds, -1 if no expiry, None if not found

        Raises:
            ValueError: If key is empty
            RuntimeError: If Redis operation fails
        """
        if not key or not key.strip():
            raise ValueError("Session key cannot be empty")

        try:
            client = await self._get_client()
            ttl_val: int = await client.ttl(key)

            if ttl_val == -2:  # Key doesn't exist
                return None
            elif ttl_val == -1:  # Key exists but no expiry
                return -1
            else:
                return ttl_val

        except redis.RedisError as e:
            error_msg = f"Redis error getting TTL for session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error getting TTL for session: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            try:
                # AsyncRedis has .close() coroutine; plain client uses .close() sync
                close_fn = getattr(self._client, "close", None)
                if callable(close_fn):
                    res = close_fn()
                    if hasattr(res, "__await__"):
                        await res  # type: ignore[func-returns-value]
                logger.info("Redis connection closed")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._client = None

    async def health_check(self) -> dict[str, Any]:
        """Check Redis connection health.

        Returns:
            Health status dictionary
        """
        try:
            client = await self._get_client()

            # Get Redis info
            info = await client.info()

            return {
                "status": "healthy",
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }

        except Exception as e:  # noqa: BLE001
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_error": self._connection_error,
            }


# Factory function for easy instantiation
def create_short_term_memory(redis_url: str | None = None) -> ShortTermMemory:
    """Create a ShortTermMemory instance.

    Args:
        redis_url: Redis connection URL. If None, uses REDIS_URL env var.

    Returns:
        Configured ShortTermMemory instance
    """
    return ShortTermMemory(redis_url=redis_url)
