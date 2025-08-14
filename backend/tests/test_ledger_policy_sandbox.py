from __future__ import annotations

import os
import time

from sqlalchemy.orm import Session

from app.db.session import get_session
from app.db.models import LedgerEntry, LedgerJournal, PolicyAudit
from app.ledger.sdk import post as ledger_post
from app.policy.engine import evaluate as policy_evaluate, PolicyDecision
from app.exec.sandbox_manager import run_tool_sandboxed, SandboxTimeout


def _db() -> Session:
    for s in get_session():
        return s
    raise RuntimeError("no session")


def test_ledger_invariants_and_idempotency() -> None:
    db = _db()
    # Balanced journal
    jid = ledger_post(
        db,
        tenant_id="t-ledger",
        journal_name="test_balance",
        external_id="ext-1",
        lines=[
            {"account_name": "cash", "side": "debit", "commodity": "usd_cents", "amount": 123},
            {"account_name": "revenue", "side": "credit", "commodity": "usd_cents", "amount": 123},
        ],
    )
    # Idempotent on same external_id
    jid2 = ledger_post(
        db,
        tenant_id="t-ledger",
        journal_name="test_balance",
        external_id="ext-1",
        lines=[
            {"account_name": "cash", "side": "debit", "commodity": "usd_cents", "amount": 123},
            {"account_name": "revenue", "side": "credit", "commodity": "usd_cents", "amount": 123},
        ],
    )
    assert jid == jid2
    # Invariant: per commodity sum is zero
    rows = db.query(LedgerEntry).filter(LedgerEntry.journal_id == jid).all()
    net = 0
    for r in rows:
        amt = r.amount if r.side == "debit" else -r.amount
        net += amt
    assert net == 0


def test_policy_matrix_and_audit() -> None:
    # Create a simple rule file dynamically
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "app", "policy", "rules")
    os.makedirs(rules_dir, exist_ok=True)
    rule_path = os.path.join(rules_dir, "test.cel")
    with open(rule_path, "w", encoding="utf-8") as f:
        f.write('{"subject":"tool:api_caller","action":"execute","match":"example.com","allow":false,"reason":"domain deny"}\n')
    try:
        dec = policy_evaluate("tool:api_caller", "execute", {"tenant_id": "t1", "url": "https://example.com"})
        assert dec.allow is False
        # Ensure an audit row exists
        db = _db()
        rows = db.query(PolicyAudit).order_by(PolicyAudit.id.desc()).all()
        assert rows and rows[0].decision in {"allow", "deny"}
    finally:
        os.remove(rule_path)


def test_sandbox_kills_infinite_loop() -> None:
    # Spawn a sandbox that loops forever and ensure timeout enforced
    import textwrap, tempfile

    code = textwrap.dedent(
        """
        import time
        while True:
            time.sleep(1)
        """
    )
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as tf:
        tf.write(code)
        tf.flush()
        path = tf.name
    try:
        # Run via sandbox using a trivial wrapper module
        try:
            run_tool_sandboxed("runpy", "run_path", {"path_name": path}, timeout_secs=1)
            assert False, "expected timeout"
        except SandboxTimeout:
            pass
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


