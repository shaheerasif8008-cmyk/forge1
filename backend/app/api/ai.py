"""AI API endpoints for task execution and model management."""

import time
from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..api.auth import get_current_user
from ..core.logging_config import get_trace_id, set_request_context
from ..core.config import settings
from ..core.orchestrator.ai_orchestrator import TaskType, create_orchestrator
from ..core.quality.feedback_loop import score_task, should_retry, next_fix_plan
from ..db.models import Escalation, TaskReview
from ..core.rag.rag_engine import RAGEngine
from ..core.security.rate_limit import increment_and_check
from ..db.session import get_session
from ..core.telemetry.metrics_service import MetricsService, TaskMetrics
from ..interconnect import get_interconnect

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


class TaskRequest(BaseModel):
    """Request model for AI task execution."""

    task: str = Field(..., description="The task description or prompt")
    task_type: TaskType = Field(default=TaskType.GENERAL, description="Type of task")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    model_name: str | None = Field(default=None, description="Specific model to use")


class TaskResponse(BaseModel):
    """Response model for AI task execution."""

    success: bool
    output: str
    model_used: str
    execution_time: float
    metadata: dict[str, Any]
    error: str | None = None


class ModelInfo(BaseModel):
    """Model information response."""

    name: str
    capabilities: list[str]
    available: bool


@router.post("/execute", response_model=TaskResponse)
async def execute_task(
    request: TaskRequest,
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
    db=Depends(get_session),  # noqa: B008
) -> TaskResponse:
    """Execute an AI task."""
    try:
        # Ensure trace id is present in context for downstream propagation
        trace_id = get_trace_id()
        if trace_id:
            request.context.setdefault("trace_id", trace_id)  # type: ignore[attr-defined]
        # Basic per-tenant rate limiting
        key = f"rl:{current_user['tenant_id']}:{current_user['user_id']}:ai:execute"
        try:
            allowed = increment_and_check(settings.redis_url, key, limit=60, window_seconds=60)
        except Exception:
            allowed = True  # fail-open
        if not allowed:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        # Emit task.requested (best-effort)
        try:
            import asyncio as _asyncio
            async def _emit():
                ic = await get_interconnect()
                await ic.publish(
                    stream="events.tasks",
                    type="task.requested",
                    source="api.ai",
                    tenant_id=current_user["tenant_id"],
                    data={"task": request.task[:120], "task_type": request.task_type.value},
                )
            _asyncio.create_task(_emit())
        except Exception:
            pass

        # Provide a tenant-scoped minimal RAG engine using LongTermMemory as vector source
        class _VectorStore:
            def add(self, documents):
                return None

            def similarity_search(self, query: str, top_k: int = 5):
                # Fallback to DB cosine distance via LongTermMemory helpers if needed
                from ..core.memory.long_term import query_memory

                results = query_memory(
                    db, query, top_k=top_k, tenant_id=str(current_user["tenant_id"]) or None
                )
                for r in results:
                    r.setdefault("metadata", {})
                return results

        rag_engine = RAGEngine(vector_store=_VectorStore())
        orchestrator = create_orchestrator()

        # Add user context
        context = request.context.copy()
        context.update(
            {
                "user_id": current_user["user_id"],
                "tenant_id": current_user["tenant_id"],
                "session_id": f"session_{int(time.time())}",
            }
        )

        # Cost/size guardrails
        task_text = request.task.strip()
        if len(task_text) > 5000:
            task_text = task_text[:5000]
        context.setdefault("max_tokens", 2000)

        # Execute task with auto-retry & escalation
        max_retries = max(0, int(getattr(settings, "feedback_max_retries", 1)))
        attempts = 0
        result = await orchestrator.run_task(task=task_text, context=context)
        attempts += 1
        s = score_task(result)
        while attempts <= max_retries and (not result.success or should_retry(s, result.error)):
            plan = next_fix_plan(s, result.error, context)
            # Merge plan params into context for next attempt
            context.update(plan.get("params", {}))
            result = await orchestrator.run_task(task=task_text, context=context)
            attempts += 1
            s = score_task(result)

        # Persist review for this API-run (no task_execution linkage here)
        try:
            for session in get_session():
                db = session
                db.add(TaskReview(task_execution_id=None, score=int(s * 100), status="scored", fix_plan=next_fix_plan(s, result.error, context)))
                db.commit()
                break
        except Exception:
            pass

        # Escalate if continuing to fail
        if not result.success and not should_retry(s, result.error):
            try:
                for session in get_session():
                    db = session
                    esc = Escalation(
                        tenant_id=current_user.get("tenant_id"),
                        employee_id=None,
                        user_id=int(current_user.get("user_id")) if str(current_user.get("user_id", "")).isdigit() else None,
                        reason=str(result.error)[:500] if result.error else "low_score_failure",
                        status="open",
                    )
                    db.add(esc)
                    db.commit()
                    # TODO: enqueue notification/event (stub)
                    break
            except Exception:
                pass

        # Persist daily rollup for the ad-hoc AI execute (no employee)
        try:
            for session in get_session():
                db = session
                MetricsService().rollup_task(
                    db,
                    TaskMetrics(
                        tenant_id=current_user["tenant_id"],
                        employee_id=None,
                        duration_ms=int(result.execution_time * 1000),
                        tokens_used=int(result.metadata.get("tokens_used", 0)),
                        success=bool(result.success),
                    ),
                )
                break
        except Exception:
            pass

        return TaskResponse(
            success=result.success,
            output=result.output,
            model_used=result.model_used,
            execution_time=result.execution_time,
            metadata=result.metadata,
            error=result.error,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("AI execute_task failed", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}",
        ) from e


@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
) -> list[ModelInfo]:
    """List available AI models and their capabilities."""
    try:
        orchestrator = create_orchestrator()
        models = orchestrator.get_available_models()

        model_infos = []
        for model_name in models:
            capabilities = orchestrator.get_model_capabilities(model_name)
            model_infos.append(
                ModelInfo(
                    name=model_name,
                    capabilities=[cap.value for cap in (capabilities or [])],
                    available=True,
                )
            )

        return model_infos

    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        ) from e


@router.get("/capabilities", response_model=list[str])
async def list_capabilities(
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
) -> list[str]:
    """List available task capabilities."""
    return [cap.value for cap in TaskType]


@router.get("/health")
async def ai_health_check(
    current_user: dict[str, str] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """Check AI orchestrator health."""
    try:
        orchestrator = create_orchestrator()
        health = await orchestrator.health_check()
        return health
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI health check failed: {str(e)}",
        ) from e
