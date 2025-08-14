"""unique (tenant_id, name) on employees

Revision ID: 9_unique_employee_tenant_name
Revises: 8_make_ltm_tenant_nonnull_and_indexes
Create Date: 2025-08-11 12:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9_unique_employee_tenant_name"
down_revision = "8_make_ltm_tenant_nonnull_and_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_employees_tenant_name",
        "employees",
        ["tenant_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_employees_tenant_name", table_name="employees")


