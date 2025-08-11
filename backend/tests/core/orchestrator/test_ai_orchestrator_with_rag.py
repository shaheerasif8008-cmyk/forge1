from __future__ import annotations

from typing import Any

import pytest

from app.core.orchestrator.ai_orchestrator import (
    AIOrchestrator,
    LLMAdapter,
    TaskResult,
    TaskType,
)


class DummyAdapter(LLMAdapter):
    def __init__(self) -> None:
        self._name = "dummy-llm"

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[TaskType]:
        return [TaskType.GENERAL]

    async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
        # Echo back that we saw RAG
        rag_note = " [RAG]" if context.get("rag_used") else ""
        return {"text": f"RESULT:{rag_note} {prompt[:40]}", "tokens": 10}


class DummyRAG:
    def __init__(self, with_results: bool = True) -> None:
        self._with_results = with_results

    def query(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self._with_results:
            return []
        return [
            {
                "id": "d1",
                "content": "A first context snippet.",
                "metadata": {"src": "X"},
                "score": 0.9,
            },
            {
                "id": "d2",
                "content": "A second context snippet.",
                "metadata": {"src": "Y"},
                "score": 0.8,
            },
        ][:top_k]


@pytest.mark.asyncio
async def test_orchestrator_uses_rag_when_enabled():
    orch = AIOrchestrator(rag_engine=DummyRAG())
    orch.register_adapter(DummyAdapter())

    res: TaskResult = await orch.run_task("Explain topic Z", {"use_rag": True, "rag_top_k": 2})

    assert res.success
    assert res.metadata.get("rag_used") is True
    assert res.metadata.get("retrieved_docs_count") == 2
    assert "RESULT:" in res.output


@pytest.mark.asyncio
async def test_orchestrator_skips_rag_when_disabled():
    orch = AIOrchestrator(rag_engine=DummyRAG())
    orch.register_adapter(DummyAdapter())

    res: TaskResult = await orch.run_task("Explain topic Z", {"use_rag": False})

    assert res.success
    assert res.metadata.get("rag_used") is False
    assert res.metadata.get("retrieved_docs_count") == 0


@pytest.mark.asyncio
async def test_orchestrator_handles_rag_errors_gracefully():
    class ErrorRAG:
        def query(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
            raise RuntimeError("RAG failed")

    orch = AIOrchestrator(rag_engine=ErrorRAG())
    orch.register_adapter(DummyAdapter())

    res: TaskResult = await orch.run_task("Explain topic Z", {"use_rag": True})
    assert res.success
    assert res.metadata.get("rag_used") is False
    assert res.metadata.get("retrieved_docs_count") == 0
