"""init testing schema and tables

Revision ID: 0001_init
Revises: 
Create Date: 2025-08-13 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS testing")

    test_kind = sa.Enum("unit", "integration", "e2e", "rag", "tool", "security", name="test_kind")
    run_status = sa.Enum("running", "pass", "fail", "aborted", name="run_status")
    severity = sa.Enum("critical", "high", "medium", "low", name="severity")
    load_tool = sa.Enum("k6", "locust", name="load_tool")
    target_env = sa.Enum("staging", "prod", name="target_env")

    op.create_table(
        "test_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", test_kind, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000)),
        sa.Column("inputs", sa.JSON()),
        sa.Column("asserts", sa.JSON()),
        sa.Column("tags", sa.ARRAY(sa.String())),
        sa.Column("disabled", sa.Integer(), server_default="0", nullable=False),
        schema="testing",
    )

    op.create_table(
        "test_suites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("target_env", target_env, nullable=False),
        sa.Column("scenario_ids", sa.ARRAY(sa.Integer())),
        sa.Column("load_profile", sa.JSON()),
        sa.Column("chaos_profile", sa.JSON()),
        sa.Column("security_profile", sa.JSON()),
        schema="testing",
    )

    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("suite_id", sa.Integer(), sa.ForeignKey("testing.test_suites.id"), index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", run_status, nullable=False),
        sa.Column("stats", sa.JSON()),
        sa.Column("artifacts", sa.ARRAY(sa.String())),
        sa.Column("target_api_url", sa.String(length=500), nullable=False),
        sa.Column("trace_id", sa.String(length=200)),
        schema="testing",
    )
    op.create_index("ix_runs_suite_id", "test_runs", ["suite_id"], schema="testing")

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("testing.test_runs.id"), index=True),
        sa.Column("severity", severity, nullable=False),
        sa.Column("area", sa.String(length=200), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("trace_id", sa.String(length=200)),
        sa.Column("suggested_fix", sa.String(length=2000)),
        schema="testing",
    )
    op.create_index("ix_findings_run_id", "findings", ["run_id"], schema="testing")

    op.create_table(
        "load_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("testing.test_runs.id"), index=True),
        sa.Column("tool", load_tool, nullable=False),
        sa.Column("params", sa.JSON()),
        sa.Column("results_url", sa.String(length=1000)),
        schema="testing",
    )

    op.create_table(
        "chaos_experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("testing.test_runs.id"), index=True),
        sa.Column("config", sa.JSON()),
        sa.Column("status", sa.String(length=50)),
        schema="testing",
    )


def downgrade() -> None:
    op.drop_table("chaos_experiments", schema="testing")
    op.drop_table("load_jobs", schema="testing")
    op.drop_index("ix_findings_run_id", table_name="findings", schema="testing")
    op.drop_table("findings", schema="testing")
    op.drop_index("ix_runs_suite_id", table_name="test_runs", schema="testing")
    op.drop_table("test_runs", schema="testing")
    op.drop_table("test_suites", schema="testing")
    op.drop_table("test_scenarios", schema="testing")


