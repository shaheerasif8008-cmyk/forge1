from __future__ import annotations

import pytest

from app.core.orchestrator.ai_orchestrator import AIOrchestrator, LLMAdapter, TaskType


class FailingAdapter:
    model_name = "fail-adapter"
    capabilities = [TaskType.GENERAL]

    async def generate(self, prompt: str, context):  # type: ignore[no-untyped-def]
        raise RuntimeError("upstream down")


def test_circuit_breaker_opens(monkeypatch) -> None:
    monkeypatch.setenv("CIRCUIT_BREAKER_THRESHOLD", "2")
    orch = AIOrchestrator()
    orch.register_adapter(FailingAdapter())

    async def _run():
        with pytest.raises(RuntimeError):
            await orch.run_task("test", {})

    import anyio

    # First call should fail and return TaskResult via orchestrator; our helper expects raises,
    # so call orchestrator directly and assert error state
    async def _run_direct():
        return await orch.run_task("test", {})

    res1 = anyio.run(_run_direct)
    assert not res1.success
    res2 = anyio.run(_run_direct)
    assert not res2.success
    # Third call should be blocked by breaker (open)
    res3 = anyio.run(_run_direct)
    assert not res3.success and "circuit open" in (res3.error or "")


