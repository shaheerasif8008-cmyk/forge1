from __future__ import annotations

from app.core.quality.guards import check_and_reserve_tokens


def test_tenant_and_employee_budget_enforced(monkeypatch) -> None:
    # Use in-memory fallback by ensuring Redis import fails
    monkeypatch.setattr("app.core.quality.guards.Redis", None)

    tenant = "t1"
    emp = None  # use global cap path

    # Emulate employee cap via env default first
    monkeypatch.setenv("EMPLOYEE_DAILY_TOKENS_CAP", "100")
    # Reserve up to cap
    assert check_and_reserve_tokens(tenant, emp, 60)
    # Stay within cap
    assert check_and_reserve_tokens(tenant, emp, 30)
    # Next push exceeds 100
    assert not check_and_reserve_tokens(tenant, emp, 20)


