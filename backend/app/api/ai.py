"""AI API endpoints for task execution and model management."""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..api.auth import get_current_user
from ..core.rag.rag_engine import RAGEngine
from ..db.session import get_session
from ..core.orchestrator.ai_orchestrator import TaskType, create_orchestrator
from ..core.security.rate_limit import increment_and_check
from ..core.config import settings

router = APIRouter(prefix="/ai", tags=["ai"])


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
        # Basic per-tenant rate limiting
        key = f"rl:{current_user['tenant_id']}:{current_user['user_id']}:ai:execute"
        try:
            allowed = increment_and_check(settings.redis_url, key, limit=60, window_seconds=60)
        except Exception:
            allowed = True  # fail-open
        if not allowed:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

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

        # Execute task
        result = await orchestrator.run_task(task=request.task, context=context)

        return TaskResponse(
            success=result.success,
            output=result.output,
            model_used=result.model_used,
            execution_time=result.execution_time,
            metadata=result.metadata,
            error=result.error,
        )

    except Exception as e:  # noqa: BLE001
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
