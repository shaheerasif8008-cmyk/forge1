from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Tenant, Employee, TaskExecution, TaskReview


def test_cascade_delete_employee_taskreviews() -> None:
    with SessionLocal() as db:  # type: Session
        # Create only required tables to avoid pgvector dependency in this test
        bind = db.get_bind()
        from app.db.models import Base
        Base.metadata.create_all(bind=bind, tables=[
            Tenant.__table__, Employee.__table__, TaskExecution.__table__, TaskReview.__table__
        ])
        # Create tenant and employee (ensure clean slate)
        db.query(TaskReview).delete()
        db.query(TaskExecution).delete()
        db.query(Employee).delete()
        # Remove prior test tenant if present without touching other tenants referenced by users
        old = db.get(Tenant, "t-cs")
        if old is not None:
            db.delete(old)
            db.commit()
        t = Tenant(id="t-cs", name="T")
        db.add(t)
        db.commit()
        e = Employee(id="e-cs", tenant_id=t.id, name="E", config={})
        db.add(e)
        db.commit()

        # Create task execution and review
        te = TaskExecution(tenant_id=t.id, employee_id=e.id, user_id=1, task_type="x", prompt="p")
        db.add(te)
        db.commit()
        tr = TaskReview(task_execution_id=te.id, score=50, status="scored")
        db.add(tr)
        db.commit()

        # Delete employee -> should cascade task_execution and review
        db.delete(e)
        db.commit()

        assert db.query(TaskExecution).filter_by(employee_id="e-cs").count() == 0
        assert db.query(TaskReview).count() == 0

