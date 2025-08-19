"""AI Orchestrator for Forge 1 - Core orchestration engine.

Structured logging is used throughout. A request-scoped trace ID set in
`app.core.logging_config` will be automatically included in log entries.
"""

import logging
from enum import Enum
from typing import Any, Protocol
import os
import time

from pydantic import BaseModel, Field
from ..logging_config import get_trace_id
from ..llm.model_router import ModelRouter as CostAwareRouter, RouterInputs, TenantPolicy
from ..telemetry.metrics_service import MetricsService, TaskMetrics
from ..telemetry.error_inspector import capture_error_snapshot
from ...router.runtime import ThompsonRouter
from ...router.policy import RouterPolicy
from ...ledger.sdk import post as ledger_post
from ...db.session import SessionLocal
from ..quality.feedback_loop import score_task, should_retry, next_fix_plan
from ...db.session import get_session
from ...db.models import TaskReview
from ..logging_config import get_trace_id
from ...interconnect import get_interconnect
from ..telemetry.tracing import span as trace_span, mark_ok as trace_ok, mark_error as trace_error
from ...db.models import ConsensusLog
from ...db.session import SessionLocal as _SL

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
    # Optional prompt prefix/variants for self-tuning
    prompt_prefix: str | None = None
    prompt_variants: list[str] | None = None
    tool_strategy: dict[str, Any] | None = None
    # Multi-role support for employee orchestrator
    roles: list[str] | None = None


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
        self._cb_states: dict[str, dict[str, Any]] = {}

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

    def run_with_circuit_breaker(self, model_name: str, call: callable) -> Any:  # type: ignore[override]
        from ..config import settings

        state = self._cb_states.setdefault(
            model_name,
            {
                "state": "CLOSED",
                "failures": 0,
                "last_trip": 0.0,
                "threshold": int(getattr(settings, "circuit_breaker_threshold", 3)),
                "cooldown": int(getattr(settings, "circuit_breaker_cooldown_secs", 60)),
            },
        )
        now = time.time()
        if state["state"] == "OPEN" and now - state["last_trip"] > state["cooldown"]:
            state["state"] = "HALF_OPEN"
        if state["state"] == "OPEN":
            raise RuntimeError("LLM circuit open; please retry later")
        try:
            result = call()
            state["failures"] = 0
            if state["state"] == "HALF_OPEN":
                state["state"] = "CLOSED"
            return result
        except Exception:
            state["failures"] += 1
            if state["state"] == "HALF_OPEN" or state["failures"] >= state["threshold"]:
                state["state"] = "OPEN"
                state["last_trip"] = now
            raise

    def list_adapters(self) -> list[str]:
        """List all registered adapter names."""
        return list(self._adapters.keys())


class ModelRouter:
    """Routes tasks to appropriate models based on capabilities and availability."""

    def __init__(self, registry: AdapterRegistry):
        self.registry = registry

    def select_model(self, task_type: TaskType, context: 'TaskContext') -> LLMAdapter | None:
        """Select the best model for a given task."""
        available_adapters = self.registry.get_adapters_for_task(task_type)

        if not available_adapters:
            logger.warning(f"No adapters available for task type: {task_type}")
            return None

        # Simple selection logic - can be enhanced with cost, performance metrics
        # For now, return the first available adapter
        selected = available_adapters[0]
        logger.info(
            f"Selected model {selected.model_name} for task type {task_type}",
        )
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
        # Keep legacy simple router for fallback; prefer cost-aware router
        self.router = ModelRouter(self.registry)
        self.cost_router = CostAwareRouter(self.registry)
        self.logger = logging.getLogger(__name__)
        self.rag_engine = rag_engine
        # Circuit breaker states per adapter
        self._cb_states: dict[str, dict[str, Any]] = {}

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
            # Prefer OpenRouter universal adapter when OPENROUTER_API_KEY is present
            try:
                from .adapter_openrouter import OpenRouterAdapter
                openrouter = OpenRouterAdapter()
                self.register_adapter(openrouter)
                self.logger.info("OpenRouter adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.warning(f"OpenRouter unavailable: {e}")

            # Register provider-specific adapters only if directly requested/keys available
            try:
                from .adapter_openai import create_openai_adapter
                openai_adapter = create_openai_adapter()
                self.register_adapter(openai_adapter)
                self.logger.info("OpenAI adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.info(f"OpenAI adapter not enabled: {e}")

            try:
                from .adapter_claude import create_claude_adapter
                claude_adapter = create_claude_adapter()
                self.register_adapter(claude_adapter)
                self.logger.info("Claude adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.info(f"Claude adapter not enabled: {e}")

            try:
                from .adapter_gemini import create_gemini_adapter
                gemini_adapter = create_gemini_adapter()
                self.register_adapter(gemini_adapter)
                self.logger.info("Gemini adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.info(f"Gemini adapter not enabled: {e}")

            # Register Forge Local model adapter when env present
            try:
                from .adapter_local import ForgeLocalAdapter
                local = ForgeLocalAdapter()
                self.register_adapter(local)
                self.logger.info("Forge Local adapter registered successfully")
            except (ImportError, ValueError, RuntimeError) as e:
                self.logger.info(f"Forge Local adapter not enabled: {e}")

        except (ImportError, ValueError, RuntimeError) as e:
            self.logger.error(f"Error setting up default adapters: {e}")

        registered_count = len(self.registry.list_adapters())
        self.logger.info(
            f"AI Orchestrator initialized with {registered_count} adapters",
        )

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
        trace_id = get_trace_id() or str(context.get("trace_id")) if context else None

        try:
            self.logger.info(
                f"Starting task execution",
            )

            # Route to appropriate model
            # Router: prefer cost/latency aware router with flags; allow admin flag override
            use_router = bool((self.employee_config or {}).get("router", {}).get("enabled", False))
            selected_model = None
            selected_model_name = None
            tenant_id = str((context or {}).get("tenant_id", ""))
            employee_id = str((context or {}).get("employee_id", "") or "") or None
            if use_router and tenant_id:
                tp = TenantPolicy(
                    max_cents_per_day=None,
                    max_tokens_per_run=int((context or {}).get("max_tokens", 0) or 0) or None,
                )
                ri = RouterInputs(
                    requested_model=str((context or {}).get("model_name", "") or None),
                    task_type=task_context.task_type,
                    tenant_id=tenant_id,
                    employee_id=employee_id,
                    tenant_policy=tp,
                    latency_slo_ms=int((context or {}).get("latency_slo_ms", 0) or 0) or None,
                    prompt=task,
                    user_id=str((context or {}).get("user_id", "") or None),
                    function_name=str((context or {}).get("function_name", "") or None),
                    tools=list((context or {}).get("tool_calls", []) or []),
                    estimated_tokens=None,
                )
                decision = await self.cost_router.select(ri)
                if decision is not None:
                    selected_model = self.registry.get_adapter(decision.model_name)
                    selected_model_name = decision.model_name
            if not selected_model:
                selected_model = self.router.select_model(task_context.task_type, task_context)
                selected_model_name = selected_model.model_name if selected_model else None
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
                    self.logger.debug("RAG: starting retrieval")
                    retrieved_docs = self.rag_engine.query(
                        task, top_k=max(1, task_context.rag_top_k)
                    )
                    if retrieved_docs:
                        used_rag = True
                        self.logger.info(
                            f"RAG: retrieved {len(retrieved_docs)} documents",
                        )
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

            # Self-tuning: apply optional prompt prefix or try variants selection
            prompt_candidates: list[str] = []
            prefix = str((context or {}).get("prompt_prefix", "") or "")
            if prefix:
                prompt_candidates.append(prefix + "\n\n" + augmented_prompt)
            variants = list((context or {}).get("prompt_variants", []) or [])
            for v in variants:
                prompt_candidates.append(str(v) + "\n\n" + augmented_prompt)
            if not prompt_candidates:
                prompt_candidates = [augmented_prompt]

            # Execute task with selected/first candidate; trim context and enforce token budgets
            execution_context: dict[str, Any] = dict(context or {})
            # Hard caps and defaults
            max_tokens = int(execution_context.get("max_tokens", 2000))
            if max_tokens > 32000:
                max_tokens = 32000
            execution_context["max_tokens"] = max_tokens
            # Preflight estimate (very rough): scale with prompt length
            estimated_tokens = max(1, min(32000, len(augmented_prompt) // 4))
            execution_context["estimated_tokens"] = estimated_tokens
            if trace_id and "trace_id" not in execution_context:
                execution_context["trace_id"] = trace_id
            if used_rag:
                execution_context["rag_used"] = True
                execution_context["retrieved_docs"] = retrieved_docs
            # Strict tenant/employee budget enforcement (pre-flight using estimate)
            try:
                from ..quality.guards import check_and_reserve_tokens as _reserve_tokens
                tenant_id_for_budget = str((context or {}).get("tenant_id", "") or "") or None
                employee_id_for_budget = str((context or {}).get("employee_id", "") or "") or None
                reserve_tokens = int(min(max_tokens, estimated_tokens))
                if reserve_tokens > 0 and not _reserve_tokens(tenant_id_for_budget, employee_id_for_budget, reserve_tokens):
                    return TaskResult(
                        success=False,
                        output="",
                        model_used=selected_model_name or selected_model.model_name,
                        execution_time=time.time() - start_time,
                        error="Budget exceeded",
                    )
            except Exception:
                pass
            # Simple circuit breaker inline to avoid nested loops issues
            name = selected_model.model_name
            threshold = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
            cooldown = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_SECS", "60"))
            state = self._cb_states.setdefault(
                name,
                {"state": "CLOSED", "failures": 0, "last_trip": 0.0, "threshold": threshold, "cooldown": cooldown},
            )
            now = time.time()
            if state["state"] == "OPEN" and (now - state["last_trip"]) > state["cooldown"]:
                state["state"] = "HALF_OPEN"
            if state["state"] == "OPEN":
                raise RuntimeError("LLM circuit open; please retry later")
            try:
                # Prompt cache
                with trace_span(
                    name=f"llm:{selected_model.model_name}",
                    span_type="llm",
                    trace_id=trace_id,
                    parent_span_id=None,
                    tenant_id=str((context or {}).get("tenant_id", "") or None),
                    employee_id=str((context or {}).get("employee_id", "") or None),
                    input={"prompt": "***redacted***"},
                ) as _span_ctx:
                    cached = await self.cost_router.maybe_get_cached(
                        model=selected_model.model_name,
                        function_name=str((context or {}).get("function_name", "") or None),
                        user_id=str((context or {}).get("user_id", "") or None),
                        prompt=prompt_candidates[0],
                        tools=list((context or {}).get("tool_calls", []) or []),
                    )
                    if cached is not None:
                        response = cached
                    else:
                        # Resilience ensemble for critical tasks
                        ensemble = list((context or {}).get("ensemble_models", []) or [])
                        results: list[tuple[str, dict[str, Any]]] = []
                        primary_resp = await selected_model.generate(prompt_candidates[0], execution_context)
                        results.append((selected_model.model_name, primary_resp))
                        for mname in ensemble[:2]:
                            alt = self.registry.get_adapter(str(mname))
                            if not alt:
                                continue
                            try:
                                alt_resp = await alt.generate(prompt_candidates[0], execution_context)
                                results.append((alt.model_name, alt_resp))
                            except Exception:
                                results.append((alt.model_name, {"text": "", "tokens": 0, "error": True}))
                        if len(results) == 1:
                            response = primary_resp
                        else:
                            from hashlib import sha256
                            def _norm(t: str) -> str:
                                return (t or "").strip().lower()
                            buckets: dict[str, list[int]] = {}
                            for idx, (_mn, resp) in enumerate(results):
                                txt = _norm(str(resp.get("text", "")))
                                h = sha256(txt.encode("utf-8")).hexdigest() if txt else ""
                                buckets.setdefault(h, []).append(idx)
                            best_hash, voters = max(buckets.items(), key=lambda kv: len(kv[1])) if buckets else ("", [0])
                            chosen_idx = voters[0] if voters else 0
                            response = results[chosen_idx][1]
                            # Persist consensus log (best-effort)
                            try:
                                with _SL() as _db:
                                    _db.add(
                                        ConsensusLog(
                                            tenant_id=str((context or {}).get("tenant_id", "") or None),
                                            employee_id=str((context or {}).get("employee_id", "") or None),
                                            task_type=str(task_context.task_type),
                                            models=[{"model": mn, "ok": not bool(r.get("error")), "latency_ms": None} for mn, r in results],
                                            agreed=(len(voters) >= 2),
                                            selected_model=results[chosen_idx][0],
                                            consensus_k=len(voters),
                                        )
                                    )
                                    _db.commit()
                            except Exception:
                                pass
                        await self.cost_router.store_cache(
                            model=selected_model.model_name,
                            function_name=str((context or {}).get("function_name", "") or None),
                            user_id=str((context or {}).get("user_id", "") or None),
                            prompt=prompt_candidates[0],
                            tools=list((context or {}).get("tool_calls", []) or []),
                            response=response,
                        )
                    try:
                        trace_ok(_span_ctx, output={"tokens": response.get("tokens", 0)})
                    except Exception:
                        pass
                await self.cost_router.record_provider_success(selected_model.model_name)
                state["failures"] = 0
                if state["state"] == "HALF_OPEN":
                    state["state"] = "CLOSED"
            except Exception as _e:
                # Dead-letter queue routing for failed generation (best-effort)
                try:
                    import asyncio as _asyncio
                    async def _emit_dlq():
                        ic = await get_interconnect()
                        await ic.publish(
                            stream="events.tasks",
                            type="task.generate_failed",
                            source="orchestrator",
                            data={"error": str(_e)},
                            trace_id=get_trace_id(),
                        )
                    _asyncio.create_task(_emit_dlq())
                except Exception:
                    pass
                await self.cost_router.record_provider_failure(selected_model.model_name)
                state["failures"] += 1
                if state["state"] == "HALF_OPEN" or state["failures"] >= state["threshold"]:
                    state["state"] = "OPEN"
                    state["last_trip"] = now
                try:
                    trace_error(_span_ctx, str(_e))  # type: ignore[name-defined]
                except Exception:
                    pass
                raise

            # Extract text from response dict
            output = response.get("text", "")
            tokens = response.get("tokens", 0)
            # Approximate cost in cents from router pricing map
            try:
                from ..llm.model_router import _provider_of, _cost_cents_for_tokens
                provider = _provider_of(selected_model.model_name)
                cost_cents = int(_cost_cents_for_tokens(provider, int(tokens or 0)))
            except Exception:
                cost_cents = int((tokens or 0) * 0.02)

            execution_time = time.time() - start_time
            self.logger.info(
                f"Task completed in {execution_time:.2f}s using {selected_model.model_name}",
            )

            result = TaskResult(
                success=True,
                output=output,
                model_used=selected_model_name or selected_model.model_name,
                execution_time=execution_time,
                metadata={
                    "task_type": task_context.task_type.value,
                    "tokens_used": tokens,
                    "estimated_tokens": estimated_tokens,
                    "rag_used": used_rag,
                    "retrieved_docs_count": len(retrieved_docs),
                    "cost_cents": cost_cents,
                },
            )
            # Ledger: record token and cost usage (nominal cost using token proxy)
            try:
                with SessionLocal() as db:
                    token_amt = int(tokens or 0)
                    cost_cents = int(cost_cents)
                    if token_amt > 0:
                        ledger_post(
                            db,
                            tenant_id=str((context or {}).get("tenant_id") or None),
                            journal_name="model_usage",
                            external_id=None,
                            lines=[
                                {"account_name": "llm_token_expense", "side": "debit", "commodity": "tokens", "amount": token_amt},
                                {"account_name": "llm_token_pool", "side": "credit", "commodity": "tokens", "amount": token_amt},
                            ],
                        )
                    if cost_cents > 0:
                        ledger_post(
                            db,
                            tenant_id=str((context or {}).get("tenant_id") or None),
                            journal_name="model_cost",
                            external_id=None,
                            lines=[
                                {"account_name": "llm_cost_expense", "side": "debit", "commodity": "usd_cents", "amount": cost_cents},
                                {"account_name": "cash", "side": "credit", "commodity": "usd_cents", "amount": cost_cents},
                            ],
                        )
            except Exception:
                pass
            # Record router outcome
            try:
                if use_router and selected_model_name:
                    tenant_id = str((context or {}).get("tenant_id", "")) or "default"
                    router = ThompsonRouter(tenant_id, str(task_context.task_type))
                    router.record_outcome(
                        model_name=selected_model_name,
                        success=True,
                        latency_ms=execution_time * 1000.0,
                        cost_cents=float(cost_cents),
                    )
            except Exception:
                pass
            # Persist routing telemetry
            try:
                from ...db.session import SessionLocal as _SL
                from ...db.models import ModelRouteLog
                with _SL() as _db:
                    tenant_id = str((context or {}).get("tenant_id", "")) or None
                    employee_id = str((context or {}).get("employee_id", "")) or None
                    _db.add(
                        ModelRouteLog(
                            tenant_id=tenant_id,
                            employee_id=employee_id,
                            task_type=task_context.task_type.value,
                            model_name=selected_model.model_name,
                            success=True,
                            latency_ms=int(execution_time * 1000),
                        )
                        )
                    _db.commit()
            except Exception:
                pass
            # Emit task.completed
            try:
                import asyncio as _asyncio
                async def _emit():
                    ic = await get_interconnect()
                    await ic.publish(
                        stream="events.tasks",
                        type="task.completed",
                        source="orchestrator",
                        data={"tokens": tokens, "model": selected_model.model_name},
                        trace_id=get_trace_id(),
                    )
                _asyncio.create_task(_emit())
            except Exception:
                pass
            # Feedback loop: score and persist review
            try:
                s = score_task(result)
                plan = next_fix_plan(s, None, context or {})
                for session in get_session():
                    db = session
                    review = TaskReview(
                        task_execution_id=None,  # can be backfilled if needed with proper linkage
                        score=int(s * 100),
                        status="scored",
                        fix_plan=plan,
                    )
                    db.add(review)
                    db.commit()
                    break
            except Exception:
                pass
            # Metrics: per-tenant/employee task counters and success ratio exposure
            try:
                tenant_id = str((context or {}).get("tenant_id", ""))
                employee_id = str((context or {}).get("employee_id", "")) or None
                ms = MetricsService()
                ms.incr_task(
                    TaskMetrics(
                        tenant_id=tenant_id or "unknown",
                        employee_id=employee_id,
                        duration_ms=int(execution_time * 1000),
                        tokens_used=int(tokens or 0),
                        success=True,
                    )
                )
                # Success ratio will be computed for gauges elsewhere from rollups; no direct set here
            except Exception:
                pass
            return result

        except (RuntimeError, ValueError, TypeError) as e:
            execution_time = time.time() - start_time
            self.logger.error("Task execution failed", exc_info=e)

            # record metrics for failure
            try:
                tenant_id = str((context or {}).get("tenant_id", ""))
                employee_id = str((context or {}).get("employee_id", "")) or None
                ms = MetricsService()
                ms.incr_task(
                    TaskMetrics(
                        tenant_id=tenant_id or "unknown",
                        employee_id=employee_id,
                        duration_ms=int(execution_time * 1000),
                        tokens_used=int((context or {}).get("tokens_used", 0)),
                        success=False,
                    )
                )
            except Exception:
                pass

            # Feedback loop: score, decide retry/escalation, persist
            try:
                s = score_task({
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "metadata": {"tokens_used": (context or {}).get("tokens_used", 0)},
                })
                plan = next_fix_plan(s, str(e), context or {})
                status_label = "retry_planned" if should_retry(s, str(e)) else "escalated"
                for session in get_session():
                    db = session
                    review = TaskReview(
                        task_execution_id=None,
                        score=int(s * 100),
                        status=status_label,
                        fix_plan=plan,
                    )
                    db.add(review)
                    db.commit()
                    break
            except Exception:
                pass

            result = TaskResult(
                success=False,
                output="",
                model_used="none",
                execution_time=execution_time,
                error=str(e),
            )
            # Record router negative outcome
            try:
                if (self.employee_config or {}).get("router", {}).get("enabled", False) and selected_model_name:
                    tenant_id = str((context or {}).get("tenant_id", "")) or "default"
                    router = ThompsonRouter(tenant_id, str((context or {}).get("task_type", "general")))
                    router.record_outcome(
                        model_name=selected_model_name,
                        success=False,
                        latency_ms=execution_time * 1000.0,
                        cost_cents=float((context or {}).get("tokens_used", 0)) * 0.0002,
                    )
            except Exception:
                pass
            # Persist failed routing decision
            try:
                from ...db.session import SessionLocal as _SL
                from ...db.models import ModelRouteLog
                with _SL() as _db:
                    tenant_id = str((context or {}).get("tenant_id", "")) or None
                    employee_id = str((context or {}).get("employee_id", "")) or None
                    _db.add(
                        ModelRouteLog(
                            tenant_id=tenant_id,
                            employee_id=employee_id,
                            task_type=str((context or {}).get("task_type", "general")),
                            model_name="none",
                            success=False,
                            latency_ms=int(execution_time * 1000),
                        )
                    )
                    _db.commit()
            except Exception:
                pass
            # Emit task.failed and persist Error Inspector snapshot
            try:
                import asyncio as _asyncio
                async def _emit3():
                    ic = await get_interconnect()
                    await ic.publish(
                        stream="events.tasks",
                        type="task.failed",
                        source="orchestrator",
                        data={"error": str(e)},
                        trace_id=get_trace_id(),
                    )
                _asyncio.create_task(_emit3())
            except Exception:
                pass

            # Persist snapshot (best-effort)
            try:
                for session in get_session():
                    db = session
                    capture_error_snapshot(
                        db,
                        tenant_id=str((context or {}).get("tenant_id", "")) or None,
                        employee_id=str((context or {}).get("employee_id", "")) or None,
                        trace_id=get_trace_id(),
                        task_type=str((context or {}).get("task_type", "general")),
                        prompt=str(task or ""),
                        error_message=str(e),
                        tool_stack=list((context or {}).get("tool_calls", []) or []),
                        llm_trace={},
                        tokens_used=int((context or {}).get("tokens_used", 0)),
                    )
                    break
            except Exception:
                pass
            return result

    def register_adapter(self, adapter: LLMAdapter) -> None:
        """Register a new LLM adapter."""
        self.registry.register(adapter)

    # Removed helper; handled inline

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
