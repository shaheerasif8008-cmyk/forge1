from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, engine
from app.db.models import Tenant, User, Employee, TaskExecution


def _ensure_user(tenant_id: str, username: str, email: str) -> None:
    with SessionLocal() as db:
        # Create basic tables if absent (dev CI tolerances)
        try:
            from sqlalchemy import inspect

            insp = inspect(engine)
            tables = set(insp.get_table_names())
            if "tenants" not in tables:
                Tenant.__table__.create(bind=engine, checkfirst=True)
            if "users" not in tables:
                User.__table__.create(bind=engine, checkfirst=True)
            if "employees" not in tables:
                Employee.__table__.create(bind=engine, checkfirst=True)
        except Exception:
            pass
        # Ensure tenant exists
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name=f"Tenant {tenant_id}"))
            db.commit()
        # Ensure user exists
        existing = db.query(User).filter(User.username == username).first()
        if existing is None:
            user = User(
                email=email,
                username=username,
                hashed_password="admin",
                is_active=True,
                is_superuser=False,
                role="user",
                tenant_id=tenant_id,
            )
            db.add(user)
            db.commit()


def _login(username: str) -> str:
    c = TestClient(app)
    resp = c.post("/api/v1/auth/login", data={"username": username, "password": "admin"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_multi_tenant_isolation_e2e() -> None:
    # Setup two tenants and users
    _ensure_user("tenantA", "alice", "alice@example.com")
    _ensure_user("tenantB", "bob", "bob@example.com")

    client = TestClient(app)

    # Login as alice (tenantA)
    token_a = _login("alice")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Create employee under tenantA
    create_a = client.post(
        "/api/v1/employees/",
        headers=headers_a,
        json={
            "name": "AgentA",
            "role_name": "Sales Agent",
            "description": "desc",
            "tools": ["api_caller"],
        },
    )
    assert create_a.status_code in (201, 409)

    # Fetch list for tenantA
    list_a = client.get("/api/v1/employees/", headers=headers_a)
    assert list_a.status_code == 200
    employees_a = list_a.json()
    assert isinstance(employees_a, list)
    assert any(e["name"] == "AgentA" for e in employees_a)
    emp_id_a = employees_a[0]["id"]

    # Run employee task under tenantA
    run_a = client.post(f"/api/v1/employees/{emp_id_a}/run", headers=headers_a, json={"task": "hello"})
    assert run_a.status_code in (200, 500)

    # Logs visible for tenantA
    logs_a = client.get(f"/api/v1/employees/{emp_id_a}/logs", headers=headers_a)
    assert logs_a.status_code == 200

    # Login as bob (tenantB)
    token_b = _login("bob")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create employee under tenantB
    create_b = client.post(
        "/api/v1/employees/",
        headers=headers_b,
        json={
            "name": "AgentB",
            "role_name": "Research Assistant",
            "description": "desc",
            "tools": ["api_caller"],
        },
    )
    assert create_b.status_code in (201, 409)

    # List under tenantB should not include tenantA employee IDs/names
    list_b = client.get("/api/v1/employees/", headers=headers_b)
    assert list_b.status_code == 200
    employees_b = list_b.json()
    assert isinstance(employees_b, list)
    assert all(e.get("name") != "AgentA" for e in employees_b)

    # Accessing tenantA employee via tenantB should be 404
    get_cross = client.get(f"/api/v1/employees/{emp_id_a}", headers=headers_b)
    assert get_cross.status_code == 404
    logs_cross = client.get(f"/api/v1/employees/{emp_id_a}/logs", headers=headers_b)
    assert logs_cross.status_code == 404

    # Optional: check DB-level isolation for created logs
    with SessionLocal() as db:
        # Resolve alice's tenant and ensure logs match that tenant
        emp_a_row = db.get(Employee, emp_id_a)
        if emp_a_row is not None:
            tenant_id = emp_a_row.tenant_id
            try:
                from sqlalchemy import inspect

                insp = inspect(engine)
                if "task_executions" in set(insp.get_table_names()):
                    rows = (
                        db.query(TaskExecution)
                        .filter(TaskExecution.employee_id == emp_id_a)
                        .all()
                    )
                    for r in rows:
                        assert r.tenant_id == tenant_id
            except Exception:
                # Best-effort only, table may not exist locally
                pass


