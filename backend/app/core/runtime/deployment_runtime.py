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
import logging

from ..orchestrator.ai_orchestrator import AIOrchestrator, TaskResult
from ..rag.rag_engine import RAGEngine
from ..tools.tool_registry import ToolRegistry
from ..logging_config import get_trace_id
from ..telemetry.metrics_service import MetricsService, TaskMetrics
from ...interconnect import get_interconnect
from ...shadow.dispatcher import should_shadow, tee_and_record
from ...shadow.differ import semantic_diff_score


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
        self.logger = logging.getLogger(__name__)

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
        self.logger.info("DeploymentRuntime orchestrator built")
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
            # propagate trace id to context for each iteration
            trace_id = get_trace_id()
            if trace_id:
                run_ctx.setdefault("trace_id", trace_id)
            self.logger.info("DeploymentRuntime iteration start")
            res = await self.orchestrator.run_task(prompt, context=run_ctx)
            # Shadow canary tee (best-effort, optional)
            try:
                tenant_id = str(run_ctx.get("tenant_id", ""))
                employee_id = str(run_ctx.get("employee_id", ""))
                if tenant_id and employee_id:
                    for session in get_session():
                        db = session
                        do_shadow, cfg = should_shadow(db, tenant_id=tenant_id, employee_id=employee_id)
                        if do_shadow and cfg and cfg.shadow_employee_id:
                            shadow_rt = DeploymentRuntime(employee_config=self.config)
                            shadow_rt.build_orchestrator()
                            shadow_res = await shadow_rt.orchestrator.run_task(prompt, context=run_ctx)  # type: ignore[union-attr]
                            score = semantic_diff_score(res.output or "", shadow_res.output or "")
                            tee_and_record(
                                db,
                                tenant_id=tenant_id,
                                employee_id=employee_id,
                                shadow_employee_id=str(cfg.shadow_employee_id),
                                input_text=prompt,
                                primary_output=res.output,
                                shadow_output=shadow_res.output,
                                score=score,
                            )
                        # end session scope
                        break
            except Exception:
                pass
            # Publish task lifecycle events (best-effort)
            try:
                import asyncio as _asyncio
                tenant_id = str(run_ctx.get("tenant_id", "")) or None
                employee_id = str(run_ctx.get("employee_id", "")) or None
                async def _emit():
                    ic = await get_interconnect()
                    await ic.publish(
                        stream="events.tasks",
                        type="task.completed" if res.success else "task.failed",
                        source="runtime.deployment",
                        subject=employee_id or "",
                        tenant_id=tenant_id,
                        employee_id=employee_id,
                        trace_id=trace_id,
                        actor="runtime",
                        data={
                            "output_len": len(res.output or ""),
                            "model": res.model_used,
                            "execution_ms": int(res.execution_time * 1000),
                            "error": res.error,
                        },
                    )
                _asyncio.create_task(_emit())
            except Exception:
                pass
            results.append(res)
            # Basic loop example: break if failed or nothing to continue
            if not res.success:
                break
            # In a richer runtime, update `prompt` or `run_ctx` here.
        self.logger.info("DeploymentRuntime completed")
        return results
