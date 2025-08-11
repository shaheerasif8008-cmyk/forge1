from __future__ import annotations

import pytest

from app.core.runtime.deployment_runtime import DeploymentRuntime


def _minimal_config() -> dict:
    return {
        "role": {"name": "Research Assistant", "description": "Helps with research."},
        "tools": ["api_caller", {"name": "doc_summarizer"}],
        "rag": {"enabled": False, "top_k": 5, "provider": "hybrid"},
        "memory": {
            "short_term": {"provider": "redis", "ttl": 3600},
            "long_term": {"provider": "pgvector", "dimensions": 1536},
        },
    }


def test_runtime_validates_and_loads_tools():
    cfg = _minimal_config()
    rt = DeploymentRuntime(cfg)
    orch = rt.build_orchestrator()
    assert orch is not None


def test_runtime_raises_on_missing_tool():
    cfg = _minimal_config()
    # introduce a missing tool
    cfg["tools"].append("non_existent_tool")
    with pytest.raises(ValueError):
        DeploymentRuntime(cfg)


@pytest.mark.asyncio
async def test_runtime_runs_basic_loop():
    cfg = _minimal_config()
    rt = DeploymentRuntime(cfg)
    results = await rt.start("Say hello", iterations=1)
    assert len(results) == 1
    assert results[0].model_used in {
        "none",
        "test-model",
        "openai-gpt-5",
        "claude-4-1-sonnet-20241022",
        "gemini-gemini-1.5-pro",
    }
