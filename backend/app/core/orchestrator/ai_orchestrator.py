"""AI Orchestrator for Forge 1 - Core orchestration engine."""

import logging
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task types for model routing."""

    GENERAL = "general"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    REVIEW = "review"


class TaskContext(BaseModel):
    """Context for task execution."""

    task_type: TaskType = Field(default=TaskType.GENERAL)
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    # Retrieval-augmented generation controls
    use_rag: bool = Field(default=False, description="Whether to use RAG prior to LLM call")
    rag_top_k: int = Field(default=5, description="How many documents to retrieve when using RAG")


class TaskResult(BaseModel):
    """Result of task execution."""

    model_config = {"protected_namespaces": ()}

    success: bool
    output: str
    model_used: str
    execution_time: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class LLMAdapter(Protocol):
    """Protocol for LLM adapters."""

    @property
    def model_name(self) -> str:
        """Return the model name."""
        ...

    @property
    def capabilities(self) -> list[TaskType]:
        """Return supported task types."""
        ...

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        """Generate response from prompt."""
        ...


class AdapterRegistry:
    """Registry for LLM adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, LLMAdapter] = {}
        self._capability_map: dict[TaskType, list[str]] = {}

    def register(self, adapter: LLMAdapter) -> None:
        """Register an LLM adapter."""
        self._adapters[adapter.model_name] = adapter

        # Update capability map
        for capability in adapter.capabilities:
            if capability not in self._capability_map:
                self._capability_map[capability] = []
            self._capability_map[capability].append(adapter.model_name)

        logger.info(f"Registered adapter: {adapter.model_name}")

    def get_adapters_for_task(self, task_type: TaskType) -> list[LLMAdapter]:
        """Get adapters capable of handling a specific task type."""
        model_names = self._capability_map.get(task_type, [])
        return [self._adapters[name] for name in model_names if name in self._adapters]

    def get_adapter(self, model_name: str) -> LLMAdapter | None:
        """Get adapter by model name."""
        return self._adapters.get(model_name)

    def list_adapters(self) -> list[str]:
        """List all registered adapter names."""
        return list(self._adapters.keys())


class ModelRouter:
    """Routes tasks to appropriate models based on capabilities and availability."""

    def __init__(self, registry: AdapterRegistry):
        self.registry = registry

    def select_model(self, task_type: TaskType, context: TaskContext) -> LLMAdapter | None:
        """Select the best model for a given task."""
        available_adapters = self.registry.get_adapters_for_task(task_type)

        if not available_adapters:
            logger.warning(f"No adapters available for task type: {task_type}")
            return None

        # Simple selection logic - can be enhanced with cost, performance metrics
        # For now, return the first available adapter
        selected = available_adapters[0]
        logger.info(f"Selected model {selected.model_name} for task type {task_type}")
        return selected


class AIOrchestrator:
    """Main AI orchestration engine for Forge 1."""

    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        rag_engine: Any | None = None,
        employee_config: dict[str, Any] | None = None,
    ):
        self.registry = registry or AdapterRegistry()
        self.router = ModelRouter(self.registry)
        self.logger = logging.getLogger(__name__)
        self.rag_engine = rag_engine

        # Optional employee-driven configuration
        self.employee_config: dict[str, Any] | None = None
        self.workflow: list[dict[str, Any]] = []
        self.short_term_memory: Any | None = None
        self.long_term_memory: Any | None = None

        # Initialize with default adapters (will be populated by adapter modules)
        self._setup_default_adapters()

        # Apply employee configuration last to preserve backward compatibility
        if employee_config is not None:
            self.configure_from_employee(employee_config)

    def _setup_default_adapters(self) -> None:
        """Setup default adapters automatically."""
        try:
            # Import and register OpenAI adapter if API key is available
            try:
                from .adapter_openai import create_openai_adapter

                # Create and register adapter
                openai_adapter = create_openai_adapter()
                self.register_adapter(openai_adapter)
                self.logger.info("OpenAI adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.warning(f"Could not register OpenAI adapter: {e}")

            # Import and register Claude adapter if API key is available
            try:
                from .adapter_claude import create_claude_adapter

                claude_adapter = create_claude_adapter()
                self.register_adapter(claude_adapter)
                self.logger.info("Claude adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.warning(f"Could not register Claude adapter: {e}")

            # Import and register Gemini adapter if API key is available
            try:
                from .adapter_gemini import create_gemini_adapter

                gemini_adapter = create_gemini_adapter()
                self.register_adapter(gemini_adapter)
                self.logger.info("Gemini adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.warning(f"Could not register Gemini adapter: {e}")

        except (ImportError, ValueError, RuntimeError) as e:
            self.logger.error(f"Error setting up default adapters: {e}")

        registered_count = len(self.registry.list_adapters())
        self.logger.info(f"AI Orchestrator initialized with {registered_count} adapters")

    # New employee-driven configuration flow
    def configure_from_employee(self, employee_config: dict[str, Any]) -> None:
        """Configure orchestrator components from an EmployeeBuilder config.

        This loads multi-agent workflow, RAG, and memory settings dynamically
        while remaining optional for backward compatibility.
        """
        self.employee_config = employee_config

        # 1) Workflow setup - accept provided or create a simple default
        workflow = employee_config.get("workflow")
        if isinstance(workflow, list) and workflow:
            # Expect a list of agent role specs
            self.workflow = [dict(agent) for agent in workflow]
        else:
            role = employee_config.get("role", {})
            self.workflow = [
                {
                    "name": str(role.get("name", "Agent")),
                    "description": str(role.get("description", "Primary agent")),
                    "type": "single",
                }
            ]

        # 2) RAG setup - create a simple engine when requested, unless already provided
        try:
            rag_cfg = employee_config.get("rag", {})
            use_rag = bool(rag_cfg.get("enabled", False))
            if self.rag_engine is None and use_rag:
                from ..rag.rag_engine import RAGEngine

                class _NoopRetriever:
                    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
                        return []

                self.rag_engine = RAGEngine(
                    vector_store=None, retriever=_NoopRetriever(), reranker=None
                )
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Failed to initialize RAG engine from config: {e}")

        # 3) Memory setup - create short-term memory client if provider is redis
        try:
            memory_cfg = employee_config.get("memory", {})
            st_cfg = memory_cfg.get("short_term", {}) if isinstance(memory_cfg, dict) else {}
            lt_cfg = memory_cfg.get("long_term", {}) if isinstance(memory_cfg, dict) else {}

            provider = str(st_cfg.get("provider", "")).lower()
            if provider == "redis":
                from ..memory.short_term import create_short_term_memory

                self.short_term_memory = create_short_term_memory()
            self.long_term_memory = lt_cfg or None
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Failed to initialize memory from config: {e}")

    async def run_task(self, task: str, context: dict[str, Any] | None = None) -> TaskResult:
        """Execute a task using the appropriate AI model."""
        import time

        start_time = time.time()
        task_context = TaskContext(**(context or {}))

        try:
            self.logger.info(f"Starting task execution: {task[:100]}...")

            # Route to appropriate model
            selected_model = self.router.select_model(task_context.task_type, task_context)
            if not selected_model:
                return TaskResult(
                    success=False,
                    output="",
                    model_used="none",
                    execution_time=time.time() - start_time,
                    error="No suitable model available for task type",
                )

            # Optionally perform retrieval-augmented generation
            augmented_prompt = task
            used_rag = False
            retrieved_docs: list[dict[str, Any]] = []
            if task_context.use_rag and self.rag_engine is not None:
                try:
                    retrieved_docs = self.rag_engine.query(
                        task, top_k=max(1, task_context.rag_top_k)
                    )
                    if retrieved_docs:
                        used_rag = True
                        # Compose a brief context block
                        snippets: list[str] = []
                        for doc in retrieved_docs:
                            content = str(doc.get("content", ""))
                            if content:
                                snippets.append(content)
                        knowledge_block = "\n\n".join(snippets[: task_context.rag_top_k])
                        augmented_prompt = (
                            "Use the following context to answer the user's request.\n\n"
                            f"Context:\n{knowledge_block}\n\nUser request: {task}"
                        )
                except Exception as e:  # noqa: BLE001
                    # Log and continue without RAG
                    self.logger.warning(f"RAG retrieval failed: {e}")

            # Execute task with possibly augmented prompt; merge RAG artifacts into context
            execution_context: dict[str, Any] = dict(context or {})
            if used_rag:
                execution_context["rag_used"] = True
                execution_context["retrieved_docs"] = retrieved_docs
            response = await selected_model.generate(augmented_prompt, execution_context)

            # Extract text from response dict
            output = response.get("text", "")
            tokens = response.get("tokens", 0)

            execution_time = time.time() - start_time
            self.logger.info(
                f"Task completed in {execution_time:.2f}s using {selected_model.model_name} (tokens: {tokens})"
            )

            return TaskResult(
                success=True,
                output=output,
                model_used=selected_model.model_name,
                execution_time=execution_time,
                metadata={
                    "task_type": task_context.task_type.value,
                    "tokens_used": tokens,
                    "rag_used": used_rag,
                    "retrieved_docs_count": len(retrieved_docs),
                },
            )

        except (RuntimeError, ValueError, TypeError) as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Task execution failed: {str(e)}")

            return TaskResult(
                success=False,
                output="",
                model_used="none",
                execution_time=execution_time,
                error=str(e),
            )

    def register_adapter(self, adapter: LLMAdapter) -> None:
        """Register a new LLM adapter."""
        self.registry.register(adapter)

    def get_available_models(self) -> list[str]:
        """Get list of available model names."""
        return self.registry.list_adapters()

    def get_model_capabilities(self, model_name: str) -> list[TaskType] | None:
        """Get capabilities of a specific model."""
        adapter = self.registry.get_adapter(model_name)
        return adapter.capabilities if adapter else None

    async def health_check(self) -> dict[str, Any]:
        """Health check for the orchestrator."""
        return {
            "status": "healthy",
            "registered_models": len(self.registry.list_adapters()),
            "available_task_types": list(self.router.registry._capability_map.keys()),
            "orchestrator_version": "1.0.0",
        }


# Factory function for easy instantiation
def create_orchestrator() -> AIOrchestrator:
    """Create a new AI orchestrator instance."""
    return AIOrchestrator()
