from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from ..db.models import PolicyAudit
from ..db.session import SessionLocal


@dataclass
class PolicyDecision:
    allow: bool
    reason: str


def _load_rules() -> list[str]:
    rules_dir = os.path.join(os.path.dirname(__file__), "rules")
    files = []
    try:
        for fn in os.listdir(rules_dir):
            if fn.endswith(".cel"):
                files.append(os.path.join(rules_dir, fn))
    except FileNotFoundError:
        return []
    contents: list[str] = []
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                contents.append(f.read())
        except Exception:
            continue
    return contents


def evaluate(subject: str, action: str, context: dict[str, Any]) -> PolicyDecision:
    """Evaluate CEL-like rules.

    Rules are JSONL with fields: subject, action, allow, match (substring in URL, tool, domain), reason.
    - Multiple rules may match; DENY takes precedence over ALLOW.
    - If no rules match, default allow.
    """
    rules_src = _load_rules()
    tenant_id = str(context.get("tenant_id") or "")
    allow_reason: str | None = None
    deny_reason: str | None = None

    for src in rules_src:
        for line in src.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rule = json.loads(line)
            except Exception:
                continue
            if rule.get("subject") and rule["subject"] != subject:
                continue
            if rule.get("action") and rule["action"] != action:
                continue
            match = rule.get("match")
            hay = json.dumps(context)
            if match and match not in hay:
                continue
            if bool(rule.get("allow", True)):
                allow_reason = str(rule.get("reason", "allow"))
            else:
                deny_reason = str(rule.get("reason", "deny"))
    decision = PolicyDecision(allow=(deny_reason is None), reason=(deny_reason or allow_reason or "default allow"))

    # Audit (best-effort; tables managed via Alembic)
    try:
        with SessionLocal() as db:
            db.add(
                PolicyAudit(
                    tenant_id=tenant_id or None,
                    subject=subject,
                    action=action,
                    decision="allow" if decision.allow else "deny",
                    reason=decision.reason,
                    meta=context,
                )
            )
            db.commit()
    except Exception:
        pass
    return decision


