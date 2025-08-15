"""AI Supervisor ("AI CEO") policy checks and approvals.

This module provides lightweight, synchronous policy checks that can be
invoked before high-impact actions (e.g., sending emails, writing to CRMs,
deleting files, initiating payments).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ...db.models import SupervisorPolicy, ActionApproval
from ...db.session import SessionLocal
from sqlalchemy.exc import SQLAlchemyError

Decision = Literal["allow", "deny", "needs_human"]


@dataclass
class ActionContext:
    tenant_id: str
    employee_id: str | None = None
    user_id: int | None = None
    action: str = ""
    cost_cents: int = 0
    pii_detected: bool = False
    metadata: dict[str, Any] | None = None


def _load_policy(tenant_id: str) -> SupervisorPolicy | None:
    try:
        with SessionLocal() as db:
            # Ensure table presence in dev/test; do not error if missing
            try:
                SupervisorPolicy.__table__.create(bind=db.get_bind(), checkfirst=True)
            except Exception:
                pass
            return db.get(SupervisorPolicy, tenant_id)
    except SQLAlchemyError:
        return None


def review_action(action: str, context: dict[str, Any]) -> dict[str, str]:
    """Review a prospective action and return a policy decision.

    Returns dict with keys: {decision: "allow|deny|needs_human", reason: str}
    """
    tenant_id = str(context.get("tenant_id", ""))
    if not tenant_id:
        return {"decision": "deny", "reason": "missing_tenant"}

    policy = _load_policy(tenant_id)
    if policy is None:
        # Default conservative policy: allow unless obviously risky
        default = {
            "deny_actions": {"payment", "file_delete"},
            "require_human_for": {"crm_write", "email_send"},
            "pii_strict": False,
            "budget_per_request_cents": None,
        }
        deny_actions = default["deny_actions"]
        require_human_for = default["require_human_for"]
        pii_strict = default["pii_strict"]
        budget_per_request_cents = None
    else:
        deny_actions = set(policy.deny_actions or [])
        require_human_for = set(policy.require_human_for or [])
        pii_strict = bool(policy.pii_strict)
        budget_per_request_cents = policy.budget_per_request_cents

    # Budget check
    cost_cents = int(context.get("cost_cents", 0) or 0)
    if budget_per_request_cents is not None and cost_cents > budget_per_request_cents:
        return {"decision": "deny", "reason": "budget_overrun"}

    # PII strict mode
    if pii_strict and bool(context.get("pii_detected", False)):
        return {"decision": "needs_human", "reason": "pii_detected"}

    # Action name rules
    action_name = str(action)
    if action_name in deny_actions:
        return {"decision": "deny", "reason": "action_denied"}
    if action_name in require_human_for:
        # Create an approval ticket
        try:
            with SessionLocal() as db:
                ActionApproval.__table__.create(bind=db.get_bind(), checkfirst=True)
                db.add(ActionApproval(tenant_id=tenant_id, employee_id=str(context.get("employee_id") or ""), action=action_name, payload=context, status="pending"))
                db.commit()
        except Exception:
            pass
        return {"decision": "needs_human", "reason": "human_approval_required"}

    # Ghost mode: do not execute, but log as allowed
    if policy and bool(policy.ghost_mode):
        return {"decision": "needs_human", "reason": "ghost_mode"}
    return {"decision": "allow", "reason": "ok"}


# Convenience check for tool hooks
HIGH_IMPACT_ACTIONS = {"email_send", "crm_write", "file_delete", "payment"}


def should_hook_tool(action: str) -> bool:
    return action in HIGH_IMPACT_ACTIONS


