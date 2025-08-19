from __future__ import annotations

import os
import sqlalchemy as sa


def test_core_tables_exist_after_upgrade() -> None:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://forge:forge@127.0.0.1:5542/forge1_local",
    )
    eng = sa.create_engine(url, future=True)
    insp = sa.inspect(eng)
    tables = set(insp.get_table_names())
    # Critical tables
    expected = {
        "tenants",
        "users",
        "employees",
        "task_executions",
        "audit_logs",
        # memory related
        "long_term_memory",
        "mem_events",
        "mem_facts",
        # feature flags and related infra
        "feature_flags",
    }
    missing = sorted(list(expected - tables))
    assert not missing, f"Missing tables after migration: {missing} (have={sorted(tables)})"


