from __future__ import annotations

from typing import Any

import pytest

from app.core.employee_builder.employee_builder import EmployeeBuilder
from app.core.orchestrator.ai_orchestrator import TaskType
from app.core.runtime.deployment_runtime import DeploymentRuntime
from app.core.tools.tool_registry import ToolRegistry


class DummyTool:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._name

    def run(self, **kwargs: Any) -> Any:  # type: ignore[override]
        return {"ok": True}


@pytest.mark.asyncio
async def test_end_to_end_builder_to_runtime(monkeypatch):
    # Build employee from template (inferred from role)
    eb = EmployeeBuilder(
        role_name="Research Assistant",
        description="Conducts research and summarizes findings",
        tools=["web_scraper", "data_analyzer", "doc_summarizer", "keyword_extractor"],
    )
    cfg = eb.build_config()

    # Prepare a registry that registers dummy tools for the required names
    reg = ToolRegistry()

    def fake_load_builtins():
        for n in ["web_scraper", "data_analyzer", "doc_summarizer", "keyword_extractor"]:
            reg.register(DummyTool(n), override=True)

        # emulate LoadResult
        class LR:
            modules_loaded = 0
            tools_registered = 4

        return LR()

    monkeypatch.setattr(reg, "load_builtins", fake_load_builtins)

    rt = DeploymentRuntime(cfg, registry=reg)
    orch = rt.build_orchestrator()
    assert orch is not None

    # Register a dummy LLM adapter so no external API is needed
    class DummyAdapter:
        def __init__(self) -> None:
            self._name = "dummy-llm"

        @property
        def model_name(self) -> str:  # type: ignore[override]
            return self._name

        @property
        def capabilities(self) -> list[TaskType]:  # type: ignore[override]
            return [TaskType.GENERAL]

        async def generate(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
            return {"text": f"OK: {prompt[:30]}", "tokens": 5}

    orch.register_adapter(DummyAdapter())

    results = await rt.start("Introduce your capabilities", iterations=1)
    assert len(results) == 1
    assert results[0].success
