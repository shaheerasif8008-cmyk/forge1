#!/usr/bin/env python3
"""Demo script for short-term memory module."""

import asyncio
import logging
from datetime import datetime

from app.core.memory.short_term import create_short_term_memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_basic_operations():
    """Demonstrate basic memory operations."""
    logger.info("🚀 Starting basic memory operations demo...")

    # Create memory instance
    memory = create_short_term_memory()

    try:
        # Test health check
        health = await memory.health_check()
        logger.info(f"📊 Memory health: {health}")

        # Save a session
        session_data = {
            "user_id": "user_123",
            "username": "john_doe",
            "role": "admin",
            "last_login": datetime.now().isoformat(),
            "preferences": {"theme": "dark", "language": "en", "notifications": True},
        }

        logger.info("💾 Saving session data...")
        success = await memory.save_session("session_user_123", session_data, expiry=1800)
        if success:
            logger.info("✅ Session saved successfully")
        else:
            logger.error("❌ Failed to save session")
            return

        # Check if session exists
        exists = await memory.session_exists("session_user_123")
        logger.info(f"🔍 Session exists: {exists}")

        # Get session TTL
        ttl = await memory.get_session_ttl("session_user_123")
        logger.info(f"⏰ Session TTL: {ttl} seconds")

        # Retrieve session data
        logger.info("📖 Retrieving session data...")
        retrieved_data = await memory.get_session("session_user_123")
        if retrieved_data:
            logger.info(f"✅ Session retrieved: {retrieved_data}")
        else:
            logger.error("❌ Failed to retrieve session")
            return

        # Update session data
        logger.info("🔄 Updating session data...")
        updated_data = retrieved_data.copy()
        updated_data["last_activity"] = datetime.now().isoformat()
        updated_data["preferences"]["theme"] = "light"

        success = await memory.save_session("session_user_123", updated_data, expiry=1800)
        if success:
            logger.info("✅ Session updated successfully")
        else:
            logger.error("❌ Failed to update session")

        # Retrieve updated data
        final_data = await memory.get_session("session_user_123")
        logger.info(f"📖 Final session data: {final_data}")

        # Clean up
        logger.info("🧹 Cleaning up...")
        deleted = await memory.delete_session("session_user_123")
        if deleted:
            logger.info("✅ Session deleted successfully")
        else:
            logger.warning("⚠️ Session deletion failed")

        # Verify deletion
        exists_after = await memory.session_exists("session_user_123")
        logger.info(f"🔍 Session exists after deletion: {exists_after}")

    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Demo failed: {e}")
    finally:
        await memory.close()


async def demo_multiple_sessions():
    """Demonstrate managing multiple sessions."""
    logger.info("🚀 Starting multiple sessions demo...")

    memory = create_short_term_memory()

    try:
        # Create multiple sessions
        sessions = {
            "session_admin_1": {
                "user_id": "admin_001",
                "role": "admin",
                "permissions": ["read", "write", "delete"],
                "created_at": datetime.now().isoformat(),
            },
            "session_user_1": {
                "user_id": "user_001",
                "role": "user",
                "permissions": ["read"],
                "created_at": datetime.now().isoformat(),
            },
            "session_guest_1": {
                "user_id": "guest_001",
                "role": "guest",
                "permissions": ["read"],
                "created_at": datetime.now().isoformat(),
            },
        }

        # Save all sessions with different expiry times
        expiry_times = [3600, 1800, 900]  # 1 hour, 30 min, 15 min
        for i, (key, data) in enumerate(sessions.items()):
            expiry = expiry_times[i % len(expiry_times)]
            success = await memory.save_session(key, data, expiry)
            if success:
                logger.info(f"✅ Saved {key} with {expiry}s expiry")
            else:
                logger.error(f"❌ Failed to save {key}")

        # List all sessions and their TTLs
        logger.info("📋 Session status:")
        for key in sessions.keys():
            ttl = await memory.get_session_ttl(key)
            if ttl is not None:
                logger.info(f"  {key}: TTL {ttl}s")
            else:
                logger.info(f"  {key}: Not found")

        # Simulate session access (refreshes TTL)
        logger.info("🔄 Accessing sessions to refresh TTL...")
        for key in sessions.keys():
            data = await memory.get_session(key)
            if data:
                logger.info(f"  ✅ Accessed {key}")
            else:
                logger.warning(f"  ⚠️ Could not access {key}")

        # Clean up all sessions
        logger.info("🧹 Cleaning up all sessions...")
        for key in sessions.keys():
            deleted = await memory.delete_session(key)
            if deleted:
                logger.info(f"  ✅ Deleted {key}")
            else:
                logger.warning(f"  ⚠️ Could not delete {key}")

    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Multiple sessions demo failed: {e}")
    finally:
        await memory.close()


async def demo_error_handling():
    """Demonstrate error handling scenarios."""
    logger.info("🚀 Starting error handling demo...")

    memory = create_short_term_memory()

    try:
        # Test invalid key
        logger.info("🧪 Testing invalid key handling...")
        try:
            await memory.save_session("", {"data": "value"})
        except ValueError as e:
            logger.info(f"✅ Caught expected error: {e}")

        try:
            await memory.get_session("   ")
        except ValueError as e:
            logger.info(f"✅ Caught expected error: {e}")

        # Test invalid expiry
        logger.info("🧪 Testing invalid expiry handling...")
        try:
            await memory.save_session("test_key", {"data": "value"}, -1)
        except ValueError as e:
            logger.info(f"✅ Caught expected error: {e}")

        # Test with non-existent Redis (should handle gracefully)
        logger.info("🧪 Testing connection failure handling...")
        bad_memory = create_short_term_memory("redis://invalid:6379/0")

        try:
            await bad_memory.save_session("test", {"data": "value"})
        except RuntimeError as e:
            logger.info(f"✅ Caught expected connection error: {e}")

        await bad_memory.close()

    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Error handling demo failed: {e}")
    finally:
        await memory.close()


async def main():
    """Main demo function."""
    logger.info("🎯 Forge1 Short-Term Memory Demo")
    logger.info("=" * 50)

    # Check if Redis is available
    memory = create_short_term_memory()
    try:
        health = await memory.health_check()
        if health["status"] == "healthy":
            logger.info("✅ Redis connection available")
        else:
            logger.warning("⚠️ Redis connection issues detected")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"⚠️ Redis not available: {e}")
        logger.info("📝 Running demos with mocked Redis operations...")
    finally:
        await memory.close()

    # Run demos
    await demo_basic_operations()
    logger.info("")

    await demo_multiple_sessions()
    logger.info("")

    await demo_error_handling()
    logger.info("")

    logger.info("🎉 Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
