from __future__ import annotations

from app.core.master_ai import run_suite


def test_master_ai_runs_golden_suite() -> None:
    report = run_suite("golden_basic", {})
    assert report.suite_id == "golden-basic"
    assert report.failed == 0
    assert report.passed == report.total_cases
    assert report.tokens_in >= 0 and report.tokens_out >= 0


