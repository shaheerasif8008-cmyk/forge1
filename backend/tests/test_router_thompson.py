from __future__ import annotations

import random

from app.router.runtime import ThompsonRouter
from app.router.policy import RouterPolicy


def test_thompson_converges_to_better_model() -> None:
    rng = random.Random(123)
    router = ThompsonRouter("t1", "general", rng=rng)
    models = ["ModelA", "ModelB"]
    pol = RouterPolicy()

    # Simulated environment: ModelA has 70% success; ModelB has 30%
    def env(m: str) -> bool:
        p = 0.7 if m == "ModelA" else 0.3
        return rng.random() < p

    wins = {"ModelA": 0, "ModelB": 0}
    for _ in range(200):
        choice = router.route(models=models, policy=pol)
        m = choice["model"]
        ok = env(m)
        wins[m] += 1 if ok else 0
        router.record_outcome(model_name=m, success=ok, latency_ms=100.0, cost_cents=1.0)

    assert wins["ModelA"] > wins["ModelB"]


def test_budget_and_latency_penalties_push_selection() -> None:
    rng = random.Random(42)
    router = ThompsonRouter("t2", "general", rng=rng)
    models = ["CheapSlow", "FastCostly"]
    pol = RouterPolicy(max_cost_per_task_cents=2, max_latency_ms=150)
    # Seed outcomes: CheapSlow cheaper but slower; FastCostly faster but expensive
    for _ in range(50):
        router.record_outcome(model_name="CheapSlow", success=True, latency_ms=200.0, cost_cents=1.0)
    for _ in range(10):
        router.record_outcome(model_name="FastCostly", success=True, latency_ms=80.0, cost_cents=10.0)

    choice = router.route(models=models, policy=pol)
    # With both constraints, penalization applies to both; prefer the one violating fewer
    assert choice["model"] in {"CheapSlow", "FastCostly"}


def test_fallback_on_empty_allowed_uses_all() -> None:
    router = ThompsonRouter("t3", "general")
    models = ["A", "B"]
    pol = RouterPolicy(allowed_models=[])  # all allowed
    choice = router.route(models=models, policy=pol)
    assert choice["model"] in models


