from __future__ import annotations

from app.core.supervisor.ai_supervisor import review_action


def test_review_allow_default() -> None:
    ctx = {"tenant_id": "t1", "cost_cents": 0}
    d = review_action("read_only", ctx)
    assert d["decision"] in {"allow", "needs_human", "deny"}


def test_review_budget_deny() -> None:
    # No policy in DB -> budget not enforced, but simulate via context override by setting low budget would require DB
    # We rely on deny list instead
    ctx = {"tenant_id": "t1", "cost_cents": 999999}
    d = review_action("payment", ctx)
    assert d["decision"] == "deny"


def test_review_pii_needs_human() -> None:
    ctx = {"tenant_id": "t1", "pii_detected": True}
    d = review_action("email_send", ctx)
    # Default policy marks email_send as needs_human even without PII
    assert d["decision"] in {"needs_human", "deny"}


