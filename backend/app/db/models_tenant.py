from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase


class BaseTenant(DeclarativeBase):
    pass


class Tenant(BaseTenant):
    __tablename__ = "tenants"

    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# Phase-2 tables (aliases only for reference; actual tables in app.db.models)
# These are minimal shells to aid explicit migration generation if needed.
class Agent(BaseTenant):  # type: ignore[misc]
    __tablename__ = "employees"  # agents/employees table

    id = Column(String(100), primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)


class Task(BaseTenant):  # type: ignore[misc]
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)


