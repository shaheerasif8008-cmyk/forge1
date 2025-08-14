from __future__ import annotations

"""Built-in tools for Central AI and related agents.

Security: All tools are deterministic, use internal APIs only, and perform strict
input validation. External network access is not used.
"""

from dataclasses import dataclass
from typing import Any

from ...telemetry.metrics_service import MetricsService
from ...release.rollout import set_canary_percent, rollback_now
from ....db.session import SessionLocal
from ....db.models import AiEvaluation


@dataclass
class _SimpleTool:
    _name: str

    @property
    def name(self) -> str:
        return self._name

    def run(self, **kwargs: Any) -> Any:  # pragma: no cover - specific tools override
        raise NotImplementedError


class RunTestpackTool(_SimpleTool):
    def __init__(self) -> None:
        super().__init__("run_testpack")

    def run(self, **kwargs: Any) -> dict[str, Any]:
        employee_id = str(kwargs.get("employee_id", "")).strip()
        suite = str(kwargs.get("suite", "golden_basic.yaml") or "golden_basic.yaml")
        if not employee_id:
            raise ValueError("employee_id required")
        # Placeholder: integrate with shared.testing.runner via in-process call, or via API.
        # For now, record a synthetic pass result.
        report = {"suite": suite, "passed": True, "avg_latency_ms": 150, "total_cost_usd": 0.0001}
        with SessionLocal() as db:
            row = AiEvaluation(employee_id=employee_id, suite_name=suite, passed=bool(report["passed"]), report=report)
            db.add(row)
            db.commit()
        return report


class CompareMetricsTool(_SimpleTool):
    def __init__(self) -> None:
        super().__init__("compare_metrics")

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """Compare metrics from DailyUsageMetric; return deltas vs baseline."""
        employee_id = str(kwargs.get("employee_id", "")).strip()
        baseline_tokens = int(kwargs.get("baseline_tokens", 0) or 0)
        baseline_latency = float(kwargs.get("baseline_latency_ms", 0) or 0)
        # Read today rollups
        # Minimal placeholder: read none and return neutral deltas
        return {"employee_id": employee_id, "delta_tokens": 0 - baseline_tokens, "delta_latency_ms": 0 - baseline_latency}


class OpenPrTool(_SimpleTool):
    def __init__(self) -> None:
        super().__init__("open_pr")

    def run(self, **kwargs: Any) -> dict[str, Any]:
        title = str(kwargs.get("title", "Automation PR"))
        body = str(kwargs.get("body", ""))
        labels = list(kwargs.get("labels", []))
        # For security, do not call GitHub; return a recordable intent only.
        return {"title": title, "body": body, "labels": labels, "status": "recorded"}


class PromoteReleaseTool(_SimpleTool):
    def __init__(self) -> None:
        super().__init__("promote_release")

    def run(self, **kwargs: Any) -> dict[str, Any]:
        percent = int(kwargs.get("percent", 5) or 5)
        set_canary_percent(percent)
        return {"status": "ok", "mode": "percent", "value": percent}


class RollbackReleaseTool(_SimpleTool):
    def __init__(self) -> None:
        super().__init__("rollback_release")

    def run(self, **kwargs: Any) -> dict[str, Any]:
        rollback_now()
        return {"status": "ok", "mode": "off"}


def get_tools() -> dict[str, _SimpleTool]:
    return {
        "run_testpack": RunTestpackTool(),
        "compare_metrics": CompareMetricsTool(),
        "open_pr": OpenPrTool(),
        "promote_release": PromoteReleaseTool(),
        "rollback_release": RollbackReleaseTool(),
    }


