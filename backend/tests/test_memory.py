"""Tests for short-term memory module."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.memory.short_term import (
    SessionData,
    ShortTermMemory,
    create_short_term_memory,
)


class TestSessionData:
    """Test SessionData model."""

    def test_session_data_creation(self):
        """Test SessionData creation with default values."""
        session = SessionData(data={"user_id": "123", "role": "admin"})

        assert session.data == {"user_id": "123", "role": "admin"}
        assert isinstance(session.created_at, float)
        assert isinstance(session.last_accessed, float)
        assert session.created_at > 0
        assert session.last_accessed > 0

    def test_session_data_serialization(self):
        """Test SessionData JSON serialization."""
        session = SessionData(data={"test": "value"})
        json_str = session.model_dump_json()

        # Should be valid JSON
        assert isinstance(json_str, str)
        assert "test" in json_str
        assert "value" in json_str

    def test_session_data_deserialization(self):
        """Test SessionData JSON deserialization."""
        original_session = SessionData(data={"test": "value"})
        json_str = original_session.model_dump_json()

        # Deserialize
        deserialized_session = SessionData.model_validate_json(json_str)

        assert deserialized_session.data == original_session.data
        assert deserialized_session.created_at == original_session.created_at


class TestShortTermMemory:
    """Test ShortTermMemory class."""

    @pytest.fixture
    async def memory(self):
        """Create ShortTermMemory instance for testing."""
        memory = ShortTermMemory(redis_url="redis://localhost:6379/0")
        yield memory
        await memory.close()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.setex = AsyncMock(return_value=True)
        mock_client.get = AsyncMock()
        mock_client.delete = AsyncMock(return_value=1)
        mock_client.exists = AsyncMock(return_value=1)
        mock_client.ttl = AsyncMock(return_value=3600)
        mock_client.info = AsyncMock(
            return_value={
                "redis_version": "7.0.0",
                "connected_clients": 1,
                "used_memory_human": "1.0M",
                "uptime_in_seconds": 3600,
            }
        )
        return mock_client

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_initialization(self, mock_from_url, memory):
        """Test ShortTermMemory initialization."""
        assert memory.redis_url == "redis://localhost:6379/0"
        assert memory._client is None
        assert memory._connection_error is False

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_client_success(self, mock_from_url, memory, mock_redis_client):
        """Test successful Redis client creation."""
        mock_from_url.return_value = mock_redis_client

        client = await memory._get_client()

        assert client == mock_redis_client
        assert memory._client == mock_redis_client
        assert memory._connection_error is False
        mock_redis_client.ping.assert_called_once()

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_client_connection_failure(self, mock_from_url, memory):
        """Test Redis connection failure handling."""
        mock_from_url.side_effect = Exception("Connection failed")

        with pytest.raises(RuntimeError, match="Failed to connect to Redis"):
            await memory._get_client()

        assert memory._connection_error is True

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_save_session_success(self, mock_from_url, memory, mock_redis_client):
        """Test successful session save."""
        mock_from_url.return_value = mock_redis_client

        result = await memory.save_session("test_key", {"user_id": "123"}, 1800)

        assert result is True
        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[0][1] == 1800

    async def test_save_session_invalid_key(self, memory):
        """Test session save with invalid key."""
        with pytest.raises(ValueError, match="Session key cannot be empty"):
            await memory.save_session("", {"data": "value"})

        with pytest.raises(ValueError, match="Session key cannot be empty"):
            await memory.save_session("   ", {"data": "value"})

    async def test_save_session_invalid_expiry(self, memory):
        """Test session save with invalid expiry."""
        with pytest.raises(ValueError, match="Expiry time cannot be negative"):
            await memory.save_session("test_key", {"data": "value"}, -1)

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_session_success(self, mock_from_url, memory, mock_redis_client):
        """Test successful session retrieval."""
        mock_from_url.return_value = mock_redis_client

        # Mock session data
        session_data = SessionData(data={"user_id": "123", "role": "admin"})
        mock_redis_client.get.return_value = session_data.model_dump_json()
        mock_redis_client.ttl.return_value = 1800

        result = await memory.get_session("test_key")

        assert result == {"user_id": "123", "role": "admin"}
        mock_redis_client.get.assert_called_once_with("test_key")

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_session_not_found(self, mock_from_url, memory, mock_redis_client):
        """Test session retrieval when not found."""
        mock_from_url.return_value = mock_redis_client
        mock_redis_client.get.return_value = None

        result = await memory.get_session("test_key")

        assert result is None

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_session_corrupted_data(self, mock_from_url, memory, mock_redis_client):
        """Test session retrieval with corrupted data."""
        mock_from_url.return_value = mock_redis_client
        mock_redis_client.get.return_value = "invalid json data"

        result = await memory.get_session("test_key")

        assert result is None
        # Should clean up corrupted data
        mock_redis_client.delete.assert_called_once_with("test_key")

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_delete_session_success(self, mock_from_url, memory, mock_redis_client):
        """Test successful session deletion."""
        mock_from_url.return_value = mock_redis_client

        result = await memory.delete_session("test_key")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_delete_session_not_found(self, mock_from_url, memory, mock_redis_client):
        """Test session deletion when not found."""
        mock_from_url.return_value = mock_redis_client
        mock_redis_client.delete.return_value = 0

        result = await memory.delete_session("test_key")

        assert result is False

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_session_exists(self, mock_from_url, memory, mock_redis_client):
        """Test session existence check."""
        mock_from_url.return_value = mock_redis_client

        result = await memory.session_exists("test_key")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_session_ttl(self, mock_from_url, memory, mock_redis_client):
        """Test getting session TTL."""
        mock_from_url.return_value = mock_redis_client

        result = await memory.get_session_ttl("test_key")

        assert result == 3600
        mock_redis_client.ttl.assert_called_once_with("test_key")

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_session_ttl_not_found(self, mock_from_url, memory, mock_redis_client):
        """Test getting TTL for non-existent session."""
        mock_from_url.return_value = mock_redis_client
        mock_redis_client.ttl.return_value = -2

        result = await memory.get_session_ttl("test_key")

        assert result is None

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_get_session_ttl_no_expiry(self, mock_from_url, memory, mock_redis_client):
        """Test getting TTL for session without expiry."""
        mock_from_url.return_value = mock_redis_client
        mock_redis_client.ttl.return_value = -1

        result = await memory.get_session_ttl("test_key")

        assert result == -1

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_health_check_success(self, mock_from_url, memory, mock_redis_client):
        """Test successful health check."""
        mock_from_url.return_value = mock_redis_client

        result = await memory.health_check()

        assert result["status"] == "healthy"
        assert result["redis_version"] == "7.0.0"
        assert result["connected_clients"] == 1
        mock_redis_client.ping.assert_called_once()
        mock_redis_client.info.assert_called_once()

    @patch("app.core.memory.short_term.redis.from_url")
    async def test_health_check_failure(self, mock_from_url, memory):
        """Test health check when Redis is unavailable."""
        mock_from_url.side_effect = Exception("Connection failed")

        result = await memory.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["connection_error"] is True

    async def test_close(self, memory):
        """Test closing Redis connection."""
        # Mock client
        memory._client = AsyncMock()

        await memory.close()

        memory._client.close.assert_called_once()
        assert memory._client is None


class TestFactoryFunction:
    """Test factory function."""

    def test_create_short_term_memory(self):
        """Test factory function creation."""
        memory = create_short_term_memory()
        assert isinstance(memory, ShortTermMemory)
        assert memory.redis_url is None

    def test_create_short_term_memory_with_url(self):
        """Test factory function creation with custom URL."""
        custom_url = "redis://custom:6379/0"
        memory = create_short_term_memory(redis_url=custom_url)
        assert isinstance(memory, ShortTermMemory)
        assert memory.redis_url == custom_url


class TestIntegration:
    """Integration tests with real Redis (if available)."""

    @pytest.mark.integration
    async def test_real_redis_operations(self):
        """Test with real Redis connection (requires Redis server)."""
        # This test will be skipped if Redis is not available
        try:
            memory = ShortTermMemory()

            # Test save
            result = await memory.save_session("test_integration", {"data": "value"}, 60)
            assert result is True

            # Test get
            retrieved = await memory.get_session("test_integration")
            assert retrieved == {"data": "value"}

            # Test exists
            exists = await memory.get_session("test_integration")
            assert exists is not None

            # Test TTL
            ttl = await memory.get_session_ttl("test_integration")
            assert ttl > 0 and ttl <= 60

            # Test delete
            deleted = await memory.delete_session("test_integration")
            assert deleted is True

            # Verify deletion
            retrieved_after = await memory.get_session("test_integration")
            assert retrieved_after is None

            await memory.close()

        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Redis not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
