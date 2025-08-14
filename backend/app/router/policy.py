from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass
class RouterPolicy:
    max_cost_per_task_cents: Optional[int] = None
    max_latency_ms: Optional[int] = None
    allowed_models: list[str] = field(default_factory=list)
    fallback_chain: list[str] = field(default_factory=list)

    def is_allowed(self, model_name: str) -> bool:
        return (not self.allowed_models) or (model_name in self.allowed_models)

    @staticmethod
    def from_dict(d: dict | None) -> "RouterPolicy":
        d = d or {}
        return RouterPolicy(
            max_cost_per_task_cents=d.get("max_cost_per_task_cents"),
            max_latency_ms=d.get("max_latency_ms"),
            allowed_models=list(d.get("allowed_models", []) or []),
            fallback_chain=list(d.get("fallback_chain", []) or []),
        )


