from __future__ import annotations

import time
from collections.abc import Callable
from importlib.resources import files as resources_files
from typing import Any, Protocol, runtime_checkable

import yaml

from ..utils import to_text
from .schemas import CaseResult, Expected, SuiteReport, SuiteReportMetrics, TestCase, TestSuite
from .suites import __name__ as suites_pkg_name


@runtime_checkable
class RunnerHooks(Protocol):
    """Optional lifecycle hooks for the runner."""

    def pre_case(self, case: TestCase) -> None:  # pragma: no cover - default no-op
        ...

    def post_case(self, case: TestCase, result: CaseResult) -> None:  # pragma: no cover
        ...


def _apply_expectations(
    expected: Expected, output: Any, latency_ms: int | None, cost_usd: float | None
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    text_output = to_text(output).lower()

    for needle in expected.contains:
        if needle.lower() not in text_output:
            ok = False
            messages.append(f"missing required text: {needle}")

    for needle in expected.not_contains:
        if needle.lower() in text_output:
            ok = False
            messages.append(f"forbidden text present: {needle}")

    if expected.max_latency_ms is not None and latency_ms is not None:
        if latency_ms > expected.max_latency_ms:
            ok = False
            messages.append(f"latency {latency_ms}ms exceeds max {expected.max_latency_ms}ms")

    if expected.max_cost_usd is not None and cost_usd is not None:
        if cost_usd > expected.max_cost_usd:
            ok = False
            messages.append(f"cost ${cost_usd:.6f} exceeds max ${expected.max_cost_usd:.6f}")

    return ok, messages


def load_suite_from_path(path: str | bytes) -> TestSuite:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TestSuite.model_validate(data)


def load_suite_from_name(resource_name: str) -> TestSuite:
    """Load a suite YAML by filename from packaged `shared.testing.suites` resources."""
    resource_path = resources_files(suites_pkg_name) / resource_name
    with resource_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TestSuite.model_validate(data)


Executor = Callable[[TestCase, RunnerHooks | None], CaseResult]


def run_suite(
    suite: TestSuite, execute_case: Executor, hooks: RunnerHooks | None = None
) -> SuiteReport:
    started = SuiteReport.now_utc()
    case_results: list[CaseResult] = []

    total_latency: int = 0
    latency_count: int = 0
    total_cost: float = 0.0
    cost_seen: bool = False
    passed = 0

    for case in suite.cases:
        if hooks and hasattr(hooks, "pre_case"):
            hooks.pre_case(case)

        t0 = time.perf_counter()
        result = execute_case(case, hooks)
        t1 = time.perf_counter()

        # If executor omitted latency, compute wall time as fallback
        if result.latency_ms is None:
            result.latency_ms = int((t1 - t0) * 1000)

        # Apply built-in expectations
        ok, messages = _apply_expectations(
            case.expected, result.output, result.latency_ms, result.cost_usd
        )
        result.passed = result.passed and ok
        if messages:
            result.details.setdefault("expectation_messages", messages)

        if hooks and hasattr(hooks, "post_case"):
            hooks.post_case(case, result)

        case_results.append(result)

        if result.passed:
            passed += 1

        if result.latency_ms is not None:
            latency_count += 1
            total_latency += int(result.latency_ms)

        if result.cost_usd is not None:
            cost_seen = True
            total_cost += float(result.cost_usd)

    ended = SuiteReport.now_utc()
    duration_ms = int((ended - started).total_seconds() * 1000)

    avg_latency_ms: float | None
    if latency_count > 0:
        avg_latency_ms = total_latency / latency_count
    else:
        avg_latency_ms = None

    total_cost_usd: float | None = total_cost if cost_seen else None

    metrics = SuiteReportMetrics(
        total_cases=len(suite.cases),
        passed_cases=passed,
        failed_cases=len(suite.cases) - passed,
        avg_latency_ms=avg_latency_ms,
        total_cost_usd=total_cost_usd,
    )

    return SuiteReport(
        suite_id=suite.id,
        suite_name=suite.name,
        started_at=started,
        ended_at=ended,
        duration_ms=duration_ms,
        metrics=metrics,
        results=case_results,
    )
