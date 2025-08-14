from __future__ import annotations

from shared.testing.runner import RunnerHooks, load_suite_from_name, run_suite
from shared.testing.schemas import CaseResult, TestCase


class DummyHooks:
    def __init__(self) -> None:
        self.pre_count = 0
        self.post_count = 0

    def pre_case(self, case: TestCase) -> None:  # noqa: D401 - simple counter
        self.pre_count += 1

    def post_case(self, case: TestCase, result: CaseResult) -> None:  # noqa: D401 - simple counter
        self.post_count += 1


def dummy_execute(case: TestCase, hooks: RunnerHooks | None) -> CaseResult:
    # Produce outputs that satisfy golden suite expectations
    text = ""
    if case.id == "gb-1":
        text = "hello world summary"
    elif case.id == "gb-2":
        text = "classification: positive"
    elif case.id == "gb-3":
        text = "foobar"
    else:
        text = "ok"

    return CaseResult(
        case_id=case.id,
        passed=True,
        output=text,
        latency_ms=100,
        cost_usd=0.0005,
    )


def test_run_suite_aggregates_metrics() -> None:
    suite = load_suite_from_name("golden_basic.yaml")
    hooks = DummyHooks()
    report = run_suite(suite, dummy_execute, hooks)

    assert report.metrics.total_cases == len(suite.cases)
    assert report.metrics.passed_cases == len(suite.cases)
    assert report.metrics.failed_cases == 0
    assert report.metrics.avg_latency_ms is not None and report.metrics.avg_latency_ms > 0
    assert report.metrics.total_cost_usd is not None and report.metrics.total_cost_usd > 0
    assert hooks.pre_count == len(suite.cases)
    assert hooks.post_count == len(suite.cases)
