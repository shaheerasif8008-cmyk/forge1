from __future__ import annotations

from .prom_metrics import observe_request, set_success_ratio, OPEN_SPANS as _OPEN_SPANS  # noqa: F401


def incr_open_spans(tenant_id: str) -> None:
    try:
        _OPEN_SPANS.labels(tenant=tenant_id or "-").inc()
    except Exception:
        pass


def decr_open_spans(tenant_id: str) -> None:
    try:
        _OPEN_SPANS.labels(tenant=tenant_id or "-").dec()
    except Exception:
        pass


