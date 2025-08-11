from __future__ import annotations

from app.core.orchestrator.ai_orchestrator import AIOrchestrator


def test_configure_from_employee_minimal():
    cfg = {
        "role": {"name": "Assistant", "description": "Helps"},
        "tools": ["api_caller"],
        "rag": {"enabled": True, "top_k": 3, "provider": "hybrid"},
        "memory": {
            "short_term": {"provider": "redis", "ttl": 3600},
            "long_term": {"provider": "pgvector", "dimensions": 1536},
        },
    }

    orch = AIOrchestrator(employee_config=cfg)
    assert orch.workflow and isinstance(orch.workflow, list)
    # rag_engine should be initialized (no-op retriever)
    assert orch.rag_engine is not None
    # memory short term may be initialized when provider is redis
    # (we don't require a live Redis; object creation is enough)
    assert hasattr(orch, "short_term_memory")
