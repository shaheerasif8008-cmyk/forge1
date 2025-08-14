from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Expected(BaseModel):
    """Simple expectation rules for a test case output.

    - contains: All strings must be present in the textual output
    - not_contains: None of these strings may be present
    - max_latency_ms: Optional threshold for latency
    - max_cost_usd: Optional threshold for cost accounting
    """

    contains: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)
    max_latency_ms: int | None = None
    max_cost_usd: float | None = None


class TestCase(BaseModel):
    """A single test case within a suite."""

    id: str
    input: Any
    expected: Expected = Field(default_factory=Expected)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int | None = None


class TestSuite(BaseModel):
    """A collection of test cases with metadata."""

    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    cases: list[TestCase] = Field(default_factory=list)


class CaseResult(BaseModel):
    """Execution result for a single test case."""

    case_id: str
    passed: bool
    output: Any = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SuiteReportMetrics(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    avg_latency_ms: float | None = None
    total_cost_usd: float | None = None


class SuiteReport(BaseModel):
    suite_id: str
    suite_name: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    metrics: SuiteReportMetrics
    results: list[CaseResult]

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(UTC)
