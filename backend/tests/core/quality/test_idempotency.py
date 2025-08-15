from __future__ import annotations

from app.core.quality.guards import idempotency_check_and_store, idempotency_store_response


def test_idempotency_flow(monkeypatch) -> None:
    # Force no Redis
    monkeypatch.setattr("app.core.quality.guards.Redis", None)
    is_dup, resp_key = idempotency_check_and_store(tenant_id="t1", key="k1", request_fingerprint="fp1")
    assert not is_dup
    # Second call with same fp becomes duplicate
    is_dup2, resp_key2 = idempotency_check_and_store(tenant_id="t1", key="k1", request_fingerprint="fp1")
    assert is_dup2
    assert resp_key2 is None
    # Store response should not crash
    idempotency_store_response(tenant_id="t1", key="k1", response_payload={"ok": True})


