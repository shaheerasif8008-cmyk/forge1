from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Global Prometheus collectors (default registry)

REQUESTS_TOTAL = Counter(
    "forge1_requests_total",
    "Total HTTP requests",
    ["route", "method", "status"],
)

REQUEST_LATENCY_SECONDS = Histogram(
    "forge1_request_latency_seconds",
    "HTTP request latency",
    ["route", "method"],
    buckets=(0.05, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0),
)

TASK_SUCCESS_RATIO = Gauge(
    "forge1_task_success_ratio",
    "Task success ratio (0-1) per tenant/employee",
    ["tenant", "employee"],
)

# Optional tracing: count open spans
OPEN_SPANS = Gauge(
    "forge1_open_spans",
    "Number of open tracing spans per tenant",
    ["tenant"],
)


def observe_request(route: str, method: str, status_code: int, duration_seconds: float) -> None:
    REQUESTS_TOTAL.labels(route=route, method=method, status=str(status_code)).inc()
    REQUEST_LATENCY_SECONDS.labels(route=route, method=method).observe(max(0.0, duration_seconds))


def set_success_ratio(tenant_id: str, employee_id: str | None, ratio: float) -> None:
    TASK_SUCCESS_RATIO.labels(tenant=tenant_id, employee=str(employee_id or "")).set(max(0.0, min(1.0, ratio)))


def incr_open_spans(tenant_id: str) -> None:
    OPEN_SPANS.labels(tenant=tenant_id).inc()


def decr_open_spans(tenant_id: str) -> None:
    OPEN_SPANS.labels(tenant=tenant_id).dec()


