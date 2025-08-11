"""add tenants table and tenant fks

Revision ID: 0001_tenant
Revises: 0a0d0717a24e
Create Date: 2025-08-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_tenant"
down_revision = "0a0d0717a24e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=100), primary_key=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add tenant_id columns and FKs where missing
    with op.batch_alter_table("users") as batch:
        batch.alter_column("tenant_id", type_=sa.String(length=100), existing_nullable=True)
        batch.create_foreign_key("fk_users_tenant", "tenants", ["tenant_id"], ["id"], use_alter=True)

    with op.batch_alter_table("employees") as batch:
        batch.alter_column("tenant_id", type_=sa.String(length=100), existing_nullable=False)
        batch.create_foreign_key(
            "fk_employees_tenant", "tenants", ["tenant_id"], ["id"], use_alter=True
        )

    # task_executions may not have tenant_id yet; try to add if missing
    if not _has_column("task_executions", "tenant_id"):
        op.add_column("task_executions", sa.Column("tenant_id", sa.String(length=100), nullable=True))
    with op.batch_alter_table("task_executions") as batch:
        batch.create_foreign_key(
            "fk_taskexec_tenant", "tenants", ["tenant_id"], ["id"], use_alter=True
        )

    # long_term_memory tenant_id
    if not _has_column("long_term_memory", "tenant_id"):
        op.add_column("long_term_memory", sa.Column("tenant_id", sa.String(length=100), nullable=True))
    with op.batch_alter_table("long_term_memory") as batch:
        batch.create_foreign_key(
            "fk_ltm_tenant", "tenants", ["tenant_id"], ["id"], use_alter=True
        )


def downgrade() -> None:
    with op.batch_alter_table("long_term_memory") as batch:
        batch.drop_constraint("fk_ltm_tenant", type_="foreignkey")
    if _has_column("long_term_memory", "tenant_id"):
        op.drop_column("long_term_memory", "tenant_id")

    with op.batch_alter_table("task_executions") as batch:
        batch.drop_constraint("fk_taskexec_tenant", type_="foreignkey")
    if _has_column("task_executions", "tenant_id"):
        op.drop_column("task_executions", "tenant_id")

    with op.batch_alter_table("employees") as batch:
        batch.drop_constraint("fk_employees_tenant", type_="foreignkey")

    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_tenant", type_="foreignkey")

    op.drop_table("tenants")


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


