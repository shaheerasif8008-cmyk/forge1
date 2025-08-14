"""auth v2 tables: user_tenants, auth_sessions, email_verifications, password_resets, user_mfa, user_recovery_codes

Revision ID: 12_auth_v2_models
Revises: 11_add_employee_keys
Create Date: 2025-08-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "12_auth_v2_models"
down_revision = "11_add_employee_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_tenants" not in tables:
        op.create_table(
            "user_tenants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tenant_id", sa.String(length=100), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False, server_default="member"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_membership"),
        )
        op.create_index("ix_user_tenants_tenant_user", "user_tenants", ["tenant_id", "user_id"]) 

    if "auth_sessions" not in tables:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tenant_id", sa.String(length=100), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("jti", sa.String(length=64), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
            sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_ip", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.UniqueConstraint("jti"),
            sa.UniqueConstraint("refresh_token_hash"),
        )
        op.create_index("ix_auth_sessions_user", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_tenant", "auth_sessions", ["tenant_id"])
        op.create_index("ix_auth_sessions_expires", "auth_sessions", ["expires_at"])

    if "email_verifications" not in tables:
        op.create_table(
            "email_verifications",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("purpose", sa.String(length=32), nullable=False, server_default="verify"),
            sa.Column("data", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("token"),
        )

    if "password_resets" not in tables:
        op.create_table(
            "password_resets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("token"),
        )

    if "user_mfa" not in tables:
        op.create_table(
            "user_mfa",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("secret", sa.String(length=64), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "user_recovery_codes" not in tables:
        op.create_table(
            "user_recovery_codes",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("code_hash", sa.String(length=128), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("code_hash"),
        )


def downgrade() -> None:
    op.drop_table("user_recovery_codes")
    op.drop_table("user_mfa")
    op.drop_table("password_resets")
    op.drop_table("email_verifications")
    op.drop_index("ix_auth_sessions_expires")
    op.drop_index("ix_auth_sessions_tenant")
    op.drop_index("ix_auth_sessions_user")
    op.drop_table("auth_sessions")
    op.drop_index("ix_user_tenants_tenant_user")
    op.drop_table("user_tenants")


