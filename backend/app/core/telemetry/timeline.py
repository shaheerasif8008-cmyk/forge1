from __future__ import annotations

from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...db.models import TaskExecution, TaskReview, Escalation, Employee


def normalize_events(
    *,
    tenant_id: str,
    employee_id: str,
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Collect recent events for an employee, normalize, and order by time desc.

    Event types: message (user/assistant), supervisor_review, retry, escalation.
    Tool/rag events are included when derivable; otherwise omitted gracefully.
    """
    events: list[dict[str, Any]] = []

    # Verify employee scoping
    emp = db.get(Employee, employee_id)
    if emp is None or emp.tenant_id != tenant_id:
        return []

    # Task executions -> messages
    try:
        rows = (
            db.query(TaskExecution)
            .filter(TaskExecution.tenant_id == tenant_id, TaskExecution.employee_id == employee_id)
            .order_by(desc(TaskExecution.id))
            .limit(limit * 2)
            .offset(offset)
            .all()
        )
        for t in rows:
            # user message (prompt)
            events.append(
                {
                    "type": "message",
                    "role": "user",
                    "employee_id": employee_id,
                    "tenant_id": tenant_id,
                    "text": t.prompt,
                    "ts": (t.created_at.isoformat() if t.created_at else None),
                }
            )
            # assistant reply (response)
            events.append(
                {
                    "type": "message",
                    "role": "assistant",
                    "employee_id": employee_id,
                    "tenant_id": tenant_id,
                    "text": t.response or "",
                    "model_used": t.model_used,
                    "tokens": t.tokens_used,
                    "latency_ms": t.execution_time,
                    "success": t.success,
                    "error": t.error_message,
                    "ts": (t.created_at.isoformat() if t.created_at else None),
                }
            )
    except Exception:
        pass

    # Task reviews
    try:
        revs = (
            db.query(TaskReview)
            .order_by(desc(TaskReview.id))
            .limit(limit)
            .offset(offset)
            .all()
        )
        for r in revs:
            events.append(
                {
                    "type": "supervisor_review" if r.status != "retry_planned" else "retry",
                    "employee_id": employee_id,
                    "tenant_id": tenant_id,
                    "score": r.score,
                    "status": r.status,
                    "fix_plan": r.fix_plan,
                    "ts": (r.created_at.isoformat() if r.created_at else None),
                }
            )
    except Exception:
        pass

    # Escalations
    try:
        escs = (
            db.query(Escalation)
            .filter(Escalation.tenant_id == tenant_id, Escalation.employee_id == employee_id)
            .order_by(desc(Escalation.id))
            .limit(limit)
            .offset(offset)
            .all()
        )
        for e in escs:
            events.append(
                {
                    "type": "escalation",
                    "employee_id": employee_id,
                    "tenant_id": tenant_id,
                    "status": e.status,
                    "reason": e.reason,
                    "ts": (e.created_at.isoformat() if e.created_at else None),
                }
            )
    except Exception:
        pass

    # Include AI insights for admin context (best-effort)
    try:
        from ...db.models import AiInsight
        AiInsight.__table__.create(bind=db.get_bind(), checkfirst=True)
        insights = (
            db.query(AiInsight)
            .order_by(desc(AiInsight.id))
            .limit(max(1, limit // 5))
            .offset(offset // 5)
            .all()
        )
        for ins in insights:
            events.append(
                {
                    "type": "ai_insight",
                    "actor": ins.actor,
                    "title": ins.title,
                    "ts": (ins.created_at.isoformat() if ins.created_at else None),
                }
            )
    except Exception:
        pass

    # Order desc by ts; fallback to insertion order
    events.sort(key=lambda ev: ev.get("ts") or "", reverse=True)
    # Paginate again on the merged view to ensure final cap
    return events[offset : offset + limit]


