"""Prometheus metrics for Forge1 backend.

Exposes helpers used by middleware and services to record request timings
and success ratios. Safe to import even if prometheus_client is unavailable
at runtime (functions will no-op).
"""

from __future__ import annotations

from typing import Any

try:
    from prometheus_client import Counter, Gauge, Histogram
except Exception:  # pragma: no cover - allow running without dependency
    Counter = Gauge = Histogram = None  # type: ignore[assignment]


REQUEST_COUNT: Any | None = None
REQUEST_LATENCY: Any | None = None
EMPLOYEE_SUCCESS_RATIO: Any | None = None
OPEN_SPANS: Any | None = None
TOOL_CALLS_TOTAL: Any | None = None
TOKENS_USED_TOTAL: Any | None = None


def _init_metrics() -> None:
    global REQUEST_COUNT, REQUEST_LATENCY, EMPLOYEE_SUCCESS_RATIO, OPEN_SPANS, TOOL_CALLS_TOTAL, TOKENS_USED_TOTAL
    if Counter is None:  # dependency not installed
        REQUEST_COUNT = None
        REQUEST_LATENCY = None
        EMPLOYEE_SUCCESS_RATIO = None
        OPEN_SPANS = None
        TOOL_CALLS_TOTAL = None
        TOKENS_USED_TOTAL = None
        return
    if REQUEST_COUNT is not None:
        return
    REQUEST_COUNT = Counter(
        "forge1_request_total",
        "Total HTTP requests",
        labelnames=("route", "method", "status"),
    )
    REQUEST_LATENCY = Histogram(
        "forge1_request_duration_seconds",
        "HTTP request duration in seconds",
        labelnames=("route", "method", "status"),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    EMPLOYEE_SUCCESS_RATIO = Gauge(
        "forge1_employee_success_ratio",
        "Success ratio by tenant and employee",
        labelnames=("tenant", "employee"),
    )
    OPEN_SPANS = Gauge(
        "forge1_open_spans",
        "Number of open spans per tenant",
        labelnames=("tenant",),
    )
    TOOL_CALLS_TOTAL = Counter(
        "forge1_tool_calls_total",
        "Total tool calls",
        labelnames=("tenant", "employee"),
    )
    TOKENS_USED_TOTAL = Counter(
        "forge1_tokens_used_total",
        "Total tokens used (approximate)",
        labelnames=("tenant", "employee"),
    )


def observe_request(*, route: str, method: str, status_code: int, duration_seconds: float) -> None:
    """Record a single HTTP request observation."""
    _init_metrics()
    if REQUEST_COUNT is None:
        return
    labels = (route or "-", (method or "-").upper(), str(int(status_code)))
    try:
        REQUEST_COUNT.labels(*labels).inc()
        REQUEST_LATENCY.labels(*labels).observe(max(0.0, float(duration_seconds)))
    except Exception:
        pass


def set_success_ratio(tenant_id: str | None, employee_id: str | None, value: float) -> None:
    """Set the success ratio gauge for a tenant/employee pair."""
    _init_metrics()
    if EMPLOYEE_SUCCESS_RATIO is None:
        return
    try:
        EMPLOYEE_SUCCESS_RATIO.labels(tenant=(tenant_id or "-"), employee=(employee_id or "-")).set(float(value))
    except Exception:
        pass


def incr_tool_call(tenant_id: str | None, employee_id: str | None) -> None:
    _init_metrics()
    if TOOL_CALLS_TOTAL is None:
        return
    try:
        TOOL_CALLS_TOTAL.labels(tenant=(tenant_id or "-"), employee=(employee_id or "-")).inc()
    except Exception:
        pass


def add_tokens_used(tenant_id: str | None, employee_id: str | None, tokens: int) -> None:
    _init_metrics()
    if TOKENS_USED_TOTAL is None:
        return
    try:
        TOKENS_USED_TOTAL.labels(tenant=(tenant_id or "-"), employee=(employee_id or "-")).inc(max(0, int(tokens)))
    except Exception:
        pass
