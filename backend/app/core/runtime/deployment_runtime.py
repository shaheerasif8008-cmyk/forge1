"""Deployment runtime for executing an employee agent.

This module provides `DeploymentRuntime`, which:
- Accepts an employee config dictionary
- Loads tools via the ToolRegistry
- Initializes the AIOrchestrator with RAG and memory settings from the config
- Starts a simple agent loop by invoking the orchestrator

The runtime is intentionally lightweight to keep responsibilities separate.
It validates configuration early and raises user-friendly errors when required
fields or tools are missing.
"""

from __future__ import annotations

from typing import Any

from ..orchestrator.ai_orchestrator import AIOrchestrator, TaskResult
from ..rag.rag_engine import RAGEngine
from ..tools.tool_registry import ToolRegistry


class DeploymentRuntime:
    """Run-time wrapper that prepares the orchestrator and tools for an employee.

    Args:
        employee_config: Validated config dict describing the employee
        registry: Optional tool registry; if not provided, a new one is created
        rag_engine: Optional RAG engine; if not provided and RAG is enabled, a basic RAGEngine
                    with no retriever/vector_store is used (acts as no-op retrieval)
    """

    def __init__(
        self,
        employee_config: dict[str, Any],
        *,
        registry: ToolRegistry | None = None,
        rag_engine: Any | None = None,
    ) -> None:
        self.config = employee_config
        self.registry = registry or ToolRegistry()
        self.rag_engine = rag_engine
        self.orchestrator: AIOrchestrator | None = None

        self._validate_config(self.config)
        # Load built-in tools and ensure required ones are available
        self.registry.load_builtins()
        self._loaded_tools: dict[str, Any] = self._load_required_tools(self.config.get("tools", []))

    @staticmethod
    def _validate_config(cfg: dict[str, Any]) -> None:
        if not isinstance(cfg, dict):
            raise ValueError("employee_config must be a dictionary")
        role = cfg.get("role")
        if not isinstance(role, dict):
            raise ValueError("config.role must be a mapping with name/description")
        if not str(role.get("name", "")).strip():
            raise ValueError("config.role.name is required")
        if not str(role.get("description", "")).strip():
            raise ValueError("config.role.description is required")

        tools = cfg.get("tools")
        if not isinstance(tools, list) or not tools:
            raise ValueError("config.tools must be a non-empty list")

        rag = cfg.get("rag")
        if not isinstance(rag, dict):
            raise ValueError("config.rag must be provided (dict)")
        mem = cfg.get("memory")
        if not isinstance(mem, dict):
            raise ValueError("config.memory must be provided (dict)")

    def _load_required_tools(self, tools_spec: list[dict[str, Any] | str]) -> dict[str, Any]:
        loaded: dict[str, Any] = {}
        for entry in tools_spec:
            if isinstance(entry, str):
                tool_name = entry
            elif isinstance(entry, dict):
                tool_name = str(entry.get("name", ""))
            else:
                tool_name = ""
            if not tool_name:
                raise ValueError("Tool entry missing name")

            tool = self.registry.get(tool_name)
            if tool is None:
                raise ValueError(f"Required tool '{tool_name}' is not available")
            loaded[tool_name] = tool
        return loaded

    def build_orchestrator(self) -> AIOrchestrator:
        # Initialize a basic rag engine if requested but not provided
        rag_cfg: dict[str, Any] = self.config.get("rag", {})
        rag_enabled = bool(rag_cfg.get("enabled", False))
        rag = self.rag_engine
        if rag is None and rag_enabled:
            # Provide a no-op retriever to satisfy RAGEngine requirements
            class _NoopRetriever:
                def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
                    return []

            rag = RAGEngine(vector_store=None, retriever=_NoopRetriever(), reranker=None)

        self.orchestrator = AIOrchestrator(rag_engine=rag)
        return self.orchestrator

    async def start(
        self,
        seed_task: str,
        *,
        iterations: int = 1,
        context: dict[str, Any] | None = None,
    ) -> list[TaskResult]:
        """Start a simple agent loop for the employee.

        Args:
            seed_task: The initial task to run
            iterations: Number of iterations to run (default: 1)
            context: Optional context to pass to the orchestrator

        Returns:
            List of TaskResult objects, one per iteration.
        """
        if self.orchestrator is None:
            self.build_orchestrator()
        assert self.orchestrator is not None

        role = self.config["role"]
        rag_cfg = self.config.get("rag", {})

        run_ctx: dict[str, Any] = {
            "task_type": self.config.get("task_type", "general"),
            "use_rag": bool(rag_cfg.get("enabled", False)),
            "rag_top_k": int(rag_cfg.get("top_k", 5)),
            "tools": list(self._loaded_tools.keys()),
            "role": {"name": role.get("name"), "description": role.get("description")},
        }
        if context:
            run_ctx.update(context)

        results: list[TaskResult] = []
        prompt = seed_task
        for _i in range(max(1, iterations)):
            res = await self.orchestrator.run_task(prompt, context=run_ctx)
            results.append(res)
            # Basic loop example: break if failed or nothing to continue
            if not res.success:
                break
            # In a richer runtime, update `prompt` or `run_ctx` here.
        return results
