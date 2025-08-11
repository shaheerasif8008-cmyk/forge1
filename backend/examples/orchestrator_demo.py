#!/usr/bin/env python3
"""Demo script for AI Orchestrator."""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.orchestrator.ai_orchestrator import (
    TaskContext,
    TaskType,
    create_orchestrator,
)


class DemoLLMAdapter:
    """Demo LLM adapter for testing."""

    def __init__(self, model_name: str, capabilities: list[TaskType]):
        self._model_name = model_name
        self._capabilities = capabilities

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def capabilities(self) -> list[TaskType]:
        return self._capabilities

    async def generate(self, prompt: str, context: dict) -> str:
        """Generate a demo response."""
        await asyncio.sleep(0.1)  # Simulate API call
        return f"Demo response from {self._model_name}: {prompt[:50]}..."


async def main():
    """Main demo function."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting AI Orchestrator Demo")

    # Create orchestrator
    orchestrator = create_orchestrator()

    # Create demo adapters
    gpt5_adapter = DemoLLMAdapter("gpt-5", [TaskType.GENERAL, TaskType.CODE_GENERATION])
    claude_adapter = DemoLLMAdapter("claude-4.1", [TaskType.ANALYSIS, TaskType.REVIEW])
    gemini_adapter = DemoLLMAdapter("gemini-pro", [TaskType.CREATIVE, TaskType.GENERAL])

    # Register adapters
    orchestrator.register_adapter(gpt5_adapter)
    orchestrator.register_adapter(claude_adapter)
    orchestrator.register_adapter(gemini_adapter)

    logger.info(f"📋 Registered models: {orchestrator.get_available_models()}")

    # Health check
    health = await orchestrator.health_check()
    logger.info(f"🏥 Health status: {health}")

    # Demo tasks
    tasks = [
        ("Write a Python function to calculate fibonacci numbers", TaskType.CODE_GENERATION),
        ("Analyze the performance of this algorithm", TaskType.ANALYSIS),
        ("Create a creative story about AI", TaskType.CREATIVE),
        ("Review this code for best practices", TaskType.REVIEW),
        ("Explain machine learning concepts", TaskType.GENERAL),
    ]

    for task, task_type in tasks:
        logger.info(f"\n🔍 Executing task: {task}")
        logger.info(f"📝 Task type: {task_type.value}")

        context = TaskContext(
            task_type=task_type, user_id="demo_user", metadata={"priority": "high"}
        )

        result = await orchestrator.run_task(task, context.dict())

        if result.success:
            logger.info("✅ Task completed successfully!")
            logger.info(f"🤖 Model used: {result.model_used}")
            logger.info(f"⏱️  Execution time: {result.execution_time:.3f}s")
            logger.info(f"📤 Output: {result.output}")
        else:
            logger.error(f"❌ Task failed: {result.error}")

    logger.info("\n🎉 Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
