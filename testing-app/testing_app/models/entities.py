from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


from sqlalchemy import event
from sqlalchemy.engine import Engine

SCHEMA_NAME = "testing"


class TestKind(str, Enum):
    unit = "unit"
    integration = "integration"
    e2e = "e2e"
    rag = "rag"
    tool = "tool"
    security = "security"


class TargetEnv(str, Enum):
    staging = "staging"
    prod = "prod"


class RunStatus(str, Enum):
    running = "running"
    passed = "pass"
    failed = "fail"
    aborted = "aborted"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class LoadTool(str, Enum):
    k6 = "k6"
    locust = "locust"


class TestScenario(Base):
    __tablename__ = "test_scenarios"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[TestKind] = mapped_column(SAEnum(TestKind, name="test_kind"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    inputs: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    asserts: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    tags: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    disabled: Mapped[bool] = mapped_column(Integer, default=0)


class TestSuite(Base):
    __tablename__ = "test_suites"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_env: Mapped[TargetEnv] = mapped_column(SAEnum(TargetEnv, name="target_env"), nullable=False)
    scenario_ids: Mapped[list[int] | None] = mapped_column(JSON)
    load_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    chaos_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    security_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class TestRun(Base):
    __tablename__ = "test_runs"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_NAME}.test_suites.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, name="run_status"), nullable=False)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    artifacts: Mapped[list[str] | None] = mapped_column(JSON)
    target_api_url: Mapped[str] = mapped_column(String(500), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(200))

    suite: Mapped[TestSuite] = relationship(backref="runs")


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_NAME}.test_runs.id"), index=True)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity, name="severity"), nullable=False)
    area: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(200))
    suggested_fix: Mapped[str | None] = mapped_column(String(2000))


class LoadJob(Base):
    __tablename__ = "load_jobs"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_NAME}.test_runs.id"), index=True)
    tool: Mapped[LoadTool] = mapped_column(SAEnum(LoadTool, name="load_tool"), nullable=False)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    results_url: Mapped[str | None] = mapped_column(String(1000))


class ChaosExperiment(Base):
    __tablename__ = "chaos_experiments"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey(f"{SCHEMA_NAME}.test_runs.id"), index=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str | None] = mapped_column(String(50))


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover - best-effort
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


