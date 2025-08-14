from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.core.master_ai import run_suite as master_run_suite
from shared.testing.runner import RunnerHooks


router = APIRouter(prefix="/suites", tags=["suites"])


@router.get("/")
def list_suites() -> list[str]:
    return [
        "golden_basic",
        "adversarial",
        "cost_latency",
    ]


class DefaultHooks:
    def pre_case(self, case: Any) -> None:
        return None

    def post_case(self, case: Any, result: Any) -> None:
        return None


def default_execute_case(case: Any, hooks: RunnerHooks | None) -> dict[str, Any]:
    # Minimal default executor for sandbox: echo input
    text = str(case.input)
    return {
        "case_id": case.id,
        "passed": True,
        "output": text,
        "latency_ms": 50,
        "cost_usd": 0.0,
        "error": None,
        "details": {},
    }


@router.post("/run")
def run_suite_endpoint(
    suite: str = Query("golden_basic"),
) -> dict[str, Any]:
    report = master_run_suite(suite, {})
    return report.model_dump()
