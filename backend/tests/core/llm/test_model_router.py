from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.llm.model_router import ModelRouter, RouterInputs, TenantPolicy


class _TaskType:
    def __init__(self, value: str) -> None:
        self.value = value


class _Adapter:
    def __init__(self, name: str, caps: list[_TaskType]) -> None:
        self._name = name
        self._caps = caps

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[_TaskType]:
        return self._caps


class _Registry:
    def __init__(self, adapters: list[_Adapter]) -> None:
        self._adapters = {a.model_name: a for a in adapters}

    def get_adapters_for_task(self, task_type: Any) -> list[_Adapter]:
        return [a for a in self._adapters.values() if any(c.value == task_type.value for c in a.capabilities)]

    def get_adapter(self, model_name: str) -> _Adapter | None:
        return self._adapters.get(model_name)


@pytest.mark.asyncio
async def test_router_prefers_lower_cost_when_all_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    # Provide fake env keys
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    # Set costs so openrouter cheaper than openai
    monkeypatch.setenv("OPENAI_1K_TOKEN_COST_CENTS", "50")
    monkeypatch.setenv("OPENROUTER_1K_TOKEN_COST_CENTS", "5")

    caps = [_TaskType("general")]
    registry = _Registry([_Adapter("openrouter-gpt-4o", caps), _Adapter("openai-gpt-5", caps)])
    router = ModelRouter(registry)
    ri = RouterInputs(
        requested_model=None,
        task_type=_TaskType("general"),
        tenant_id="t1",
        employee_id=None,
        tenant_policy=TenantPolicy(max_cents_per_day=None, max_tokens_per_run=None),
        latency_slo_ms=800,
        prompt="hello",
        user_id=None,
        function_name=None,
        tools=None,
        estimated_tokens=100,
    )
    d = await router.select(ri)
    assert d is not None
    assert d.provider == "openrouter"


