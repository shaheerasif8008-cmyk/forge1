"""Database models for Forge 1."""

from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    """Tenant/organization model for multi-tenant isolation."""

    __tablename__ = "tenants"

    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<Tenant(id='{self.id}', name='{self.name}')>"


class User(Base):
    """User model for authentication and user management."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String(50), nullable=False, default="user")
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, email='{self.email}', username='{self.username}', role='{self.role}')>"
        )


class UserSession(Base):
    """User session model for tracking active sessions."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_used_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    session_data = Column(Text, nullable=True)  # JSON string for additional session data

    def __repr__(self) -> str:
        return (
            f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at='{self.expires_at}')>"
        )


class Employee(Base):
    """Employee entity storing built configurations per tenant."""

    __tablename__ = "employees"

    id = Column(String(100), primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    owner_user_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<Employee(id='{self.id}', tenant_id='{self.tenant_id}', name='{self.name}')>"


class TaskExecution(Base):
    """Task execution model for tracking AI task runs."""

    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)
    employee_id = Column(String(100), ForeignKey("employees.id"), nullable=True, index=True)
    user_id = Column(Integer, nullable=False)
    task_type = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    execution_time = Column(Integer, nullable=True)  # in milliseconds
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    task_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return (
            f"<TaskExecution(id={self.id}, user_id={self.user_id}, task_type='{self.task_type}')>"
        )


class LongTermMemory(Base):
    """Long-term memory stored with vector embeddings for semantic search."""

    __tablename__ = "long_term_memory"

    id = Column(String(100), primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    # Python attribute `meta` maps to DB column name 'metadata' to avoid Base.metadata clash
    meta = Column("metadata", JSONB, nullable=False, default=dict)
    embedding: Any = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<LongTermMemory(id={self.id})>"


class AuditLog(Base):
    """Audit log of API actions for basic compliance and debugging."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    meta = Column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, path='{self.path}', status={self.status_code})>"
