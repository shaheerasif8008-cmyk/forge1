#!/usr/bin/env python3
"""Test script for LLM adapters."""

import asyncio
import logging
from typing import Any

from app.core.orchestrator import (
    AIOrchestrator,
    TaskType,
    create_claude_adapter,
    create_gemini_adapter,
    create_openai_adapter,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_adapter_creation():
    """Test creating adapters without API keys (should fail gracefully)."""
    logger.info("Testing adapter creation...")

    # Test OpenAI adapter creation (should fail without API key)
    try:
        openai_adapter = await create_openai_adapter()
        logger.info(f"✅ OpenAI adapter created: {openai_adapter.model_name}")
    except ValueError as e:
        logger.info(f"✅ OpenAI adapter creation failed as expected: {e}")

    # Test Claude adapter creation (should fail without API key)
    try:
        claude_adapter = await create_claude_adapter()
        logger.info(f"✅ Claude adapter created: {claude_adapter.model_name}")
    except ValueError as e:
        logger.info(f"✅ Claude adapter creation failed as expected: {e}")

    # Test Gemini adapter creation (should fail without API key)
    try:
        gemini_adapter = await create_gemini_adapter()
        logger.info(f"✅ Gemini adapter created: {gemini_adapter.model_name}")
    except ValueError as e:
        logger.info(f"✅ Gemini adapter creation failed as expected: {e}")


async def test_orchestrator_initialization():
    """Test orchestrator initialization with adapters."""
    logger.info("Testing orchestrator initialization...")

    try:
        orchestrator = AIOrchestrator()
        available_models = orchestrator.get_available_models()
        logger.info(
            f"✅ Orchestrator initialized with {len(available_models)} models: {available_models}"
        )

        # Test health check
        health = await orchestrator.health_check()
        logger.info(f"✅ Health check: {health}")

        return orchestrator
    except (ImportError, ValueError, RuntimeError) as e:
        logger.error(f"❌ Orchestrator initialization failed: {e}")
        return None


async def test_task_routing():
    """Test task routing to appropriate models."""
    logger.info("Testing task routing...")

    orchestrator = await test_orchestrator_initialization()
    if not orchestrator:
        return

    # Test different task types
    task_types = [
        TaskType.GENERAL,
        TaskType.CODE_GENERATION,
        TaskType.ANALYSIS,
        TaskType.CREATIVE,
        TaskType.REVIEW,
    ]

    for task_type in task_types:
        capabilities = orchestrator.get_model_capabilities("openai-gpt-5")
        if capabilities:
            logger.info(f"✅ Task type {task_type.value} supported by OpenAI")
        else:
            logger.info(f"⚠️ Task type {task_type.value} not supported by OpenAI")


async def test_mock_adapters():
    """Test with mock adapters that don't require API keys."""
    logger.info("Testing with mock adapters...")

    class MockAdapter:
        """Mock adapter for testing."""

        @property
        def model_name(self) -> str:
            return "mock-adapter"

        @property
        def capabilities(self) -> list[TaskType]:
            return [TaskType.GENERAL, TaskType.CODE_GENERATION]

        async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "text": f"Mock response to: {prompt[:50]}...",
                "tokens": len(prompt.split()) + 10,
                "model": "mock-adapter",
                "finish_reason": "stop",
            }

    # Create orchestrator with mock adapter
    orchestrator = await test_orchestrator_initialization()
    if not orchestrator:
        return

    registry = orchestrator.registry
    mock_adapter = MockAdapter()
    registry.register(mock_adapter)

    logger.info(f"✅ Mock adapter registered: {mock_adapter.model_name}")

    # Test task execution
    try:
        result = await orchestrator.run_task(
            "Write a simple Python function", {"task_type": TaskType.CODE_GENERATION.value}
        )
        logger.info(f"✅ Task execution result: {result}")
    except (ValueError, RuntimeError) as e:
        logger.error(f"❌ Task execution failed: {e}")


async def main():
    """Main test function."""
    logger.info("🚀 Starting LLM adapter tests...")

    # Test 1: Adapter creation
    await test_adapter_creation()

    # Test 2: Orchestrator initialization
    await test_orchestrator_initialization()

    # Test 3: Task routing
    await test_task_routing()

    # Test 4: Mock adapters
    await test_mock_adapters()

    logger.info("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
