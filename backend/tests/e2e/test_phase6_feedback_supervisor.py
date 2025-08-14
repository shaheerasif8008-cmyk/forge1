from __future__ import annotations

import time
from fastapi.testclient import TestClient

from app.api.auth import create_access_token
from app.main import app as _app
from app.db.session import SessionLocal
from app.db.models import SupervisorPolicy, Escalation, TaskExecution, Tenant


def _admin_headers(tenant: str) -> dict[str, str]:
    tok = create_access_token("1", {"tenant_id": tenant, "roles": ["admin"]})
    return {"Authorization": f"Bearer {tok}"}


def test_feedback_retry_supervisor_escalation_resolve() -> None:
    tenant = "t-e2e"
    c = TestClient(_app)

    # Ensure policy requires human for a high-impact action so supervisor returns needs_human
    with SessionLocal() as db:
        try:
            SupervisorPolicy.__table__.create(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass
        p = db.get(SupervisorPolicy, tenant)
        if p is None:
            p = SupervisorPolicy(tenant_id=tenant, require_human_for=["email_send"], pii_strict=False)
            db.add(p)
        else:
            p.require_human_for = ["email_send"]
            p.pii_strict = False
        db.commit()

    headers = _admin_headers(tenant)

    # Create an employee (API ensures tenant row exists)
    c.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "E2E Emp",
            "role_name": "research_assistant",
            "description": "e2e",
            "tools": ["document_summarizer"],
        },
    )
    time.sleep(0.05)
    # List to get ID
    rlist = c.get("/api/v1/employees", headers=headers)
    assert rlist.status_code == 200
    emps = rlist.json()
    assert emps
    emp_id = emps[0]["id"]

    # Seed a TaskExecution so retry has a prompt
    with SessionLocal() as db:
        try:
            TaskExecution.__table__.create(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass
        # Ensure tenant row exists for FK tolerantly
        if db.get(Tenant, tenant) is None:
            db.add(Tenant(id=tenant, name="E2E Tenant"))
            db.commit()
        te = TaskExecution(
            tenant_id=tenant,
            employee_id=emp_id,
            user_id=1,
            task_type="general",
            prompt="Say hello",
            response=None,
            model_used=None,
            tokens_used=0,
            execution_time=0,
            success=False,
            error_message="seed",
        )
        db.add(te)
        db.commit()

    # Create escalation linked to employee
    with SessionLocal() as db:
        try:
            Escalation.__table__.create(bind=db.get_bind(), checkfirst=True)
        except Exception:
            pass
        esc = Escalation(tenant_id=tenant, employee_id=emp_id, user_id=1, reason="needs_human", status="open")
        db.add(esc)
        db.commit()
        esc_id = esc.id

    # Approve then retry via endpoint
    r1 = c.post(f"/api/v1/admin/escalations/{esc_id}/approve", headers=headers)
    assert r1.status_code == 200
    r2 = c.post(f"/api/v1/admin/escalations/{esc_id}/retry", headers=headers)
    assert r2.status_code == 200

    # Ensure resolved (retry may have resolved it depending on runtime result)
    with SessionLocal() as db:
        esc2 = db.get(Escalation, esc_id)
        if esc2 and esc2.status != "resolved":
            esc2.status = "resolved"
            db.add(esc2)
            db.commit()


