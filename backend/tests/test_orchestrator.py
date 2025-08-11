"""Tests for AI Orchestrator."""

from unittest.mock import AsyncMock

import pytest

from app.core.orchestrator.ai_orchestrator import (
    AdapterRegistry,
    ModelRouter,
    TaskContext,
    TaskResult,
    TaskType,
    create_orchestrator,
)


class MockLLMAdapter:
    """Mock LLM adapter for testing."""

    def __init__(self, model_name: str, capabilities: list[TaskType]):
        self._model_name = model_name
        self._capabilities = capabilities
        self.generate = AsyncMock(return_value={"text": "Mock response", "tokens": 10})

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def capabilities(self) -> list[TaskType]:
        return self._capabilities


@pytest.fixture
def mock_adapter():
    """Create a mock LLM adapter."""
    return MockLLMAdapter("test-model", [TaskType.GENERAL, TaskType.ANALYSIS])


@pytest.fixture
def registry():
    """Create an adapter registry."""
    return AdapterRegistry()


@pytest.fixture
def orchestrator():
    """Create an AI orchestrator instance."""
    return create_orchestrator()


class TestAdapterRegistry:
    """Test adapter registry functionality."""

    def test_register_adapter(self, registry, mock_adapter):
        """Test registering an adapter."""
        registry.register(mock_adapter)
        assert "test-model" in registry.list_adapters()
        assert registry.get_adapter("test-model") == mock_adapter

    def test_get_adapters_for_task(self, registry, mock_adapter):
        registry.register(mock_adapter)
        adapters = registry.get_adapters_for_task(TaskType.GENERAL)
        assert len(adapters) == 1
        assert adapters[0] == mock_adapter

    def test_get_adapters_for_unsupported_task(self, registry, mock_adapter):
        """Test getting adapters for unsupported task type."""
        registry.register(mock_adapter)
        adapters = registry.get_adapters_for_task(TaskType.CODE_GENERATION)
        assert len(adapters) == 0


class TestModelRouter:
    """Test model routing functionality."""

    def test_select_model(self, registry, mock_adapter):
        """Test model selection for a task."""
        registry.register(mock_adapter)
        router = ModelRouter(registry)

        context = TaskContext(task_type=TaskType.GENERAL)
        selected = router.select_model(TaskType.GENERAL, context)

        assert selected == mock_adapter

    def test_select_model_no_available(self, registry):
        """Test model selection when no adapters available."""
        router = ModelRouter(registry)

        context = TaskContext(task_type=TaskType.GENERAL)
        selected = router.select_model(TaskType.GENERAL, context)

        assert selected is None


class TestAIOrchestrator:
    """Test AI orchestrator functionality."""

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.registry is not None
        assert orchestrator.router is not None
        assert len(orchestrator.get_available_models()) == 0

    def test_register_adapter(self, orchestrator, mock_adapter):
        """Test registering an adapter with the orchestrator."""
        orchestrator.register_adapter(mock_adapter)
        assert "test-model" in orchestrator.get_available_models()

    def test_get_model_capabilities(self, orchestrator, mock_adapter):
        """Test getting model capabilities."""
        orchestrator.register_adapter(mock_adapter)
        capabilities = orchestrator.get_model_capabilities("test-model")
        assert capabilities == [TaskType.GENERAL, TaskType.ANALYSIS]

    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator):
        """Test orchestrator health check."""
        health = await orchestrator.health_check()
        assert health["status"] == "healthy"
        assert health["registered_models"] == 0
        assert "orchestrator_version" in health

    @pytest.mark.asyncio
    async def test_run_task_no_adapters(self, orchestrator):
        """Test running a task with no adapters available."""
        result = await orchestrator.run_task("test task")

        assert not result.success
        assert result.model_used == "none"
        assert "No suitable model available" in result.error

    @pytest.mark.asyncio
    async def test_run_task_with_adapter(self, orchestrator, mock_adapter):
        """Test running a task with an available adapter."""
        orchestrator.register_adapter(mock_adapter)

        result = await orchestrator.run_task("test task", {"task_type": TaskType.GENERAL})

        assert result.success
        assert result.model_used == "test-model"
        assert result.output == "Mock response"
        assert result.execution_time > 0


class TestTaskContext:
    """Test task context functionality."""

    def test_default_values(self):
        """Test default context values."""
        context = TaskContext()
        assert context.task_type == TaskType.GENERAL
        assert context.user_id is None
        assert context.session_id is None
        assert context.metadata == {}
        assert context.constraints == {}

    def test_custom_values(self):
        """Test custom context values."""
        context = TaskContext(
            task_type=TaskType.CODE_GENERATION, user_id="user123", metadata={"priority": "high"}
        )
        assert context.task_type == TaskType.CODE_GENERATION
        assert context.user_id == "user123"
        assert context.metadata["priority"] == "high"


class TestTaskResult:
    """Test task result functionality."""

    def test_success_result(self):
        """Test successful task result."""
        result = TaskResult(
            success=True, output="Task completed", model_used="gpt-5", execution_time=1.5
        )
        assert result.success
        assert result.output == "Task completed"
        assert result.model_used == "gpt-5"
        assert result.execution_time == 1.5
        assert result.error is None

    def test_error_result(self):
        """Test error task result."""
        result = TaskResult(
            success=False, output="", model_used="none", execution_time=0.1, error="Task failed"
        )
        assert not result.success
        assert result.error == "Task failed"
