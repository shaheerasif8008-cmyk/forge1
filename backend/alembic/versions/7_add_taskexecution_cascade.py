"""add ON DELETE CASCADE to task_executions.employee_id

Revision ID: 7_add_taskexecution_cascade
Revises: 6_add_promotion_audit
Create Date: 2025-08-11 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "7_add_taskexecution_cascade"
down_revision = "5_add_beta_metrics"  # safe to run regardless of rollouts; depends only on employees
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop and recreate the FK with ON DELETE CASCADE if it exists
    conn = op.get_bind()
    insp = sa.inspect(conn)
    fks = insp.get_foreign_keys("task_executions")
    for fk in fks:
        if fk.get("referred_table") == "employees" and set(fk.get("constrained_columns", [])) == {"employee_id"}:
            op.drop_constraint(fk["name"], "task_executions", type_="foreignkey")
            break
    op.create_foreign_key(
        "fk_taskexec_employee_cascade",
        source_table="task_executions",
        referent_table="employees",
        local_cols=["employee_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert to FK without cascade
    conn = op.get_bind()
    insp = sa.inspect(conn)
    fks = insp.get_foreign_keys("task_executions")
    for fk in fks:
        if fk.get("referred_table") == "employees" and set(fk.get("constrained_columns", [])) == {"employee_id"}:
            op.drop_constraint(fk["name"], "task_executions", type_="foreignkey")
            break
    op.create_foreign_key(
        "fk_taskexec_employee",
        source_table="task_executions",
        referent_table="employees",
        local_cols=["employee_id"],
        remote_cols=["id"],
    )


