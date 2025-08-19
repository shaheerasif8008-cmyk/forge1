"""Database models for Forge 1."""

from datetime import UTC, datetime
from typing import Any

try:
    from pgvector.sqlalchemy import Vector as _Vector  # type: ignore
    _HAS_VECTOR = True
except Exception:
    _Vector = None  # type: ignore
    _HAS_VECTOR = False
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Index, UniqueConstraint, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, deferred


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    """Tenant/organization model for multi-tenant isolation."""

    __tablename__ = "tenants"

    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    beta = Column(Boolean, nullable=False, default=False)
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
    # Optional pointer to the active version snapshot for rollback/promotions
    active_version_id = Column(Integer, ForeignKey("employee_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_employees_tenant_created", "tenant_id", "created_at"),
        Index("ix_employees_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Employee(id='{self.id}', tenant_id='{self.tenant_id}', name='{self.name}')>"


class TaskExecution(Base):
    """Task execution model for tracking AI task runs."""

    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)
    employee_id = Column(
        String(100), ForeignKey("employees.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id = Column(Integer, nullable=False)
    task_type = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    execution_time = Column(Integer, nullable=True)  # in milliseconds
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    # Approximate API cost for this task in cents (computed from provider/token map)
    # Deferred to avoid selecting when column is missing in older local DBs
    cost_cents = deferred(Column(Integer, nullable=True))
    task_data = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return (
            f"<TaskExecution(id={self.id}, user_id={self.user_id}, task_type='{self.task_type}')>"
        )


class RunFailure(Base):
    """Failed run metadata to support DLQ replay."""

    __tablename__ = "run_failures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_execution_id = Column(Integer, index=True, nullable=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    employee_id = Column(String(100), index=True, nullable=True)
    reason = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)  # input/context snapshot
    error = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="queued")  # queued|replayed|ignored
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class TaskReview(Base):
    """Review metadata for executed tasks (feedback loop)."""

    __tablename__ = "task_reviews"

    id = Column(Integer, primary_key=True, index=True)
    task_execution_id = Column(Integer, ForeignKey("task_executions.id", ondelete="CASCADE"), index=True)
    score = Column(Integer, nullable=True)  # store score * 100 (0..100)
    status = Column(String(50), nullable=False, default="scored")  # scored | retry_planned | escalated
    fix_plan = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TraceSpan(Base):
    """Span/event for distributed tracing graphs.

    Spans form a tree via parent_span_id. Input/output/error are small JSON snapshots for replay.
    """

    __tablename__ = "trace_spans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(64), index=True, nullable=False)
    span_id = Column(String(64), unique=True, index=True, nullable=False)
    parent_span_id = Column(String(64), index=True, nullable=True)

    tenant_id = Column(String(100), index=True, nullable=True)
    employee_id = Column(String(100), index=True, nullable=True)

    span_type = Column(String(32), nullable=False)  # task|router|rag|llm|tool|cache|policy|guard
    name = Column(String(200), nullable=False)
    status = Column(String(16), nullable=False, default="running")  # running|ok|error

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    input = Column(JSONB, nullable=True)
    output = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    # Column name can't be 'metadata' to avoid Base.metadata clash
    meta = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_trace_spans_trace_parent", "trace_id", "parent_span_id"),
        Index("ix_trace_spans_tenant_trace", "tenant_id", "trace_id"),
    )


class EmployeeVersion(Base):
    """Immutable snapshots of `Employee.config` to support tuning and rollback."""

    __tablename__ = "employee_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(100), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    # Monotonic version number per employee (1, 2, 3, ...)
    version = Column(Integer, nullable=False)
    parent_version_id = Column(Integer, ForeignKey("employee_versions.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active|canary|retired|candidate
    notes = Column(Text, nullable=True)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("employee_id", "version", name="uq_employee_version"),
        Index("ix_employee_versions_emp_status", "employee_id", "status"),
    )


class PerformanceSnapshot(Base):
    """Aggregated performance metrics for an employee or specific version/strategy.

    Used by the self-tuning loop to compare strategies over the same workload window.
    """

    __tablename__ = "performance_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(100), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    employee_version_id = Column(Integer, ForeignKey("employee_versions.id", ondelete="SET NULL"), index=True, nullable=True)
    strategy = Column(String(50), nullable=True)
    window_start = Column(DateTime(timezone=True), nullable=True)
    window_end = Column(DateTime(timezone=True), nullable=True)
    tasks = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    avg_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    avg_cost_cents = Column(Float, nullable=True)
    metrics = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_perf_snap_emp_version", "employee_id", "employee_version_id"),
    )


class Escalation(Base):
    """Escalation record for tasks requiring human review or intervention."""

    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    employee_id = Column(String(100), index=True, nullable=True)
    user_id = Column(Integer, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="open")  # open | resolved | dismissed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SupervisorPolicy(Base):
    """Per-tenant AI Supervisor policy configuration."""

    __tablename__ = "supervisor_policy"

    tenant_id = Column(String(100), primary_key=True, index=True)
    # Budgets in cents
    budget_per_request_cents = Column(Integer, nullable=True)
    budget_per_day_cents = Column(Integer, nullable=True)
    # Lists of action names
    require_human_for = Column(JSONB, nullable=True, default=list)
    deny_actions = Column(JSONB, nullable=True, default=list)
    pii_strict = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    # HITL Controls
    ghost_mode = Column(Boolean, nullable=False, default=False)
    pause_high_impact = Column(Boolean, nullable=False, default=True)

class LongTermMemory(Base):
    """Long-term memory stored with vector embeddings for semantic search."""

    __tablename__ = "long_term_memory"

    id = Column(String(100), primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    # Python attribute `meta` maps to DB column name 'metadata' to avoid Base.metadata clash
    meta = Column("metadata", JSONB, nullable=False, default=dict)
    # Use pgvector when available; fallback to JSONB for portability in dev/test
    embedding: Any = Column(JSONB if not _HAS_VECTOR else _Vector(1536))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<LongTermMemory(id={self.id})>"


class MemEvent(Base):
    """Raw memory events captured for an employee.

    Examples: task runs, tool outputs, user feedback. Stores embedding for ANN search.
    """

    __tablename__ = "mem_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String(100), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(50), nullable=False, default="task")  # task|tool|note|feedback
    content = Column(Text, nullable=False)
    # Python attribute `meta` maps to DB column name 'metadata' to avoid Base.metadata clash
    meta = Column("metadata", JSONB, nullable=True)
    embedding = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

    __table_args__ = (
        Index("ix_mem_event_tenant_emp_created", "tenant_id", "employee_id", "created_at"),
    )


class MemFact(Base):
    """Summarized atomic facts distilled from events with embeddings for semantic search."""

    __tablename__ = "mem_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String(100), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    source_event_id = Column(Integer, ForeignKey("mem_events.id", ondelete="SET NULL"), nullable=True, index=True)
    fact = Column(Text, nullable=False)
    # Python attribute `meta` maps to DB column name 'metadata' to avoid Base.metadata clash
    meta = Column("metadata", JSONB, nullable=True)
    embedding = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

    __table_args__ = (
        Index("ix_mem_fact_tenant_emp_created", "tenant_id", "employee_id", "created_at"),
    )

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


class EmployeeKey(Base):
    """API key allowing external invocation of a specific `Employee`.

    Keys are tenant- and employee-scoped. Secrets are never stored in plaintext; only
    an HMAC/hashed form is persisted. Runtime authentication compares in constant time.
    """

    __tablename__ = "employee_keys"

    # UUID stored as string for portability
    id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(
        String(100), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Short, unique prefix used to identify key records without revealing the secret
    prefix = Column(String(32), unique=True, index=True, nullable=False)
    # Hex-encoded HMAC/hashed secret (length allows SHA-256/512 hex digests)
    hashed_secret = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    # 'active' | 'revoked'
    status = Column(String(20), nullable=False, default="active")
    # Optional scopes for future fine-grained permissions (e.g., specific tools)
    scopes = Column(JSONB, nullable=False, default=dict)
    # Optional expiry for key rotation policies
    expires_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<EmployeeKey(id='{self.id}', employee_id='{self.employee_id}', status='{self.status}')>"


class AiInsight(Base):
    """Insights produced by internal AIs (e.g., CEO AI, Testing AI)."""

    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    actor = Column(String(50), nullable=False, index=True)  # ceo_ai | central_ai | testing_ai
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    labels = Column(JSONB, nullable=True)  # e.g., {"product": true, "infra": true}
    metrics = Column(JSONB, nullable=True)  # snapshot of KPIs used
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AiEvaluation(Base):
    """Evaluation reports for employees by the central AI."""

    __tablename__ = "ai_evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(String(100), index=True, nullable=False)
    suite_name = Column(String(200), nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    report = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AiRiskReport(Base):
    """Risk heatmap and test battery summary from the Testing AI."""

    __tablename__ = "ai_risk_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -------------------- Auth v2: multi-tenant accounts, sessions, MFA --------------------


class UserTenant(Base):
    """Many-to-many mapping between users and tenants with a role per tenant."""

    __tablename__ = "user_tenants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    # role names: owner | admin | member | viewer
    role = Column(String(50), nullable=False, default="member")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant_membership"),
        Index("ix_user_tenants_tenant_user", "tenant_id", "user_id"),
    )


class AuthSession(Base):
    """Refresh-rotation session store for JWT refresh tokens.

    We store a hash of the refresh token and its JTI to support revocation and rotation.
    """

    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    # JWT ID for refresh tokens
    jti = Column(String(64), unique=True, nullable=False, index=True)
    # Hex/base64 hash of refresh token value (never store plaintext)
    refresh_token_hash = Column(String(128), unique=True, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    last_ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    mfa_verified = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_auth_sessions_user", "user_id"),
        Index("ix_auth_sessions_tenant", "tenant_id"),
        Index("ix_auth_sessions_expires", "expires_at"),
    )


class EmailVerification(Base):
    """Email verification tokens for new registrations and email changes."""

    __tablename__ = "email_verifications"

    id = Column(String(36), primary_key=True, index=True)
    # For invites, user_id may not exist yet; store email and create user on accept
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    purpose = Column(String(32), nullable=False, default="verify")  # verify | invite | change_email
    # Optional extra info (e.g., {"tenant_id": "...", "role": "member"})
    data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)


class PasswordReset(Base):
    """Password reset tokens."""

    __tablename__ = "password_resets"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)


class UserMfa(Base):
    """Per-user TOTP MFA secret and status."""

    __tablename__ = "user_mfa"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    secret = Column(String(64), nullable=True)
    enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    enabled_at = Column(DateTime(timezone=True), nullable=True)


class UserRecoveryCode(Base):
    """Hashed recovery codes for MFA bypass."""

    __tablename__ = "user_recovery_codes"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False, unique=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -------------------- Marketplace & Tools Registry --------------------


class MarketplaceTemplate(Base):
    __tablename__ = "marketplace_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    vertical = Column(String(100), index=True, nullable=True)
    description = Column(Text, nullable=False)
    required_tools = Column(JSONB, nullable=False, default=list)
    default_config = Column(JSONB, nullable=False, default=dict)
    version = Column(String(32), nullable=False, default="1.0")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class ToolManifest(Base):
    __tablename__ = "tools_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    version = Column(String(32), nullable=False, default="1.0")
    scopes = Column(JSONB, nullable=True, default=list)
    config_schema = Column(JSONB, nullable=True, default=dict)
    docs_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class TenantToolConfig(Base):
    __tablename__ = "tenant_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    tool_name = Column(String(100), index=True, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    config = Column(JSONB, nullable=True, default=dict)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    __table_args__ = (
        UniqueConstraint("tenant_id", "tool_name", name="uq_tenant_tool"),
        Index("ix_tenant_tools_tenant_tool", "tenant_id", "tool_name"),
    )


# -------------------- Routing Telemetry & Refinement --------------------


class ModelRouteLog(Base):
    __tablename__ = "model_route_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    employee_id = Column(String(100), index=True, nullable=True)
    task_type = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    latency_ms = Column(Integer, nullable=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RefinementSlo(Base):
    __tablename__ = "refinement_slo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(200), index=True, nullable=True)
    template_key = Column(String(100), index=True, nullable=True)
    min_success_ratio = Column(Float, nullable=True)
    max_p95_ms = Column(Integer, nullable=True)
    max_cost_cents = Column(Integer, nullable=True)
    max_tool_error_rate = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RefinementAction(Base):
    __tablename__ = "refinement_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(100), index=True, nullable=False)
    action = Column(String(50), nullable=False)  # proposed | promoted | rolled_back
    details = Column(JSONB, nullable=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -------------------- Pipelines --------------------


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id = Column(String(100), primary_key=True)
    pipeline_id = Column(String(100), ForeignKey("pipelines.id", ondelete="CASCADE"), index=True, nullable=False)
    order = Column(Integer, nullable=False, index=True)
    employee_id = Column(String(100), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    input_map = Column(JSONB, nullable=False, default=dict)
    output_key = Column(String(100), nullable=False)
    input_schema = Column(JSONB, nullable=True)
    output_schema = Column(JSONB, nullable=True)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(String(100), ForeignKey("pipelines.id", ondelete="CASCADE"), index=True, nullable=False)
    tenant_id = Column(String(100), index=True, nullable=False)
    status = Column(String(20), nullable=False, default="running")  # running|succeeded|failed
    input = Column(JSONB, nullable=True)
    output = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at = Column(DateTime(timezone=True), nullable=True)


class PipelineStepRun(Base):
    __tablename__ = "pipeline_step_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    step_id = Column(String(100), ForeignKey("pipeline_steps.id", ondelete="CASCADE"), index=True, nullable=False)
    order = Column(Integer, nullable=False)
    employee_id = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="running")
    input = Column(JSONB, nullable=True)
    output = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    retries = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    finished_at = Column(DateTime(timezone=True), nullable=True)


# -------------------- Router (Thompson Sampling) --------------------


class RouterMetric(Base):
    """Aggregated per-tenant, per-task_type, per-model scorecard.

    Stores Beta posterior parameters for success probability and rolling
    Gaussian moments for latency and cost, along with approximate p95s.
    """

    __tablename__ = "router_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    task_type = Column(String(50), index=True, nullable=False)
    model_name = Column(String(100), index=True, nullable=False)

    # Beta posterior parameters for success probability
    alpha = Column(Integer, nullable=False, default=1)
    beta = Column(Integer, nullable=False, default=1)

    # Rolling Gaussian moments for latency (ms)
    latency_mu = Column(Integer, nullable=True)
    latency_sigma = Column(Integer, nullable=True)
    latency_p95 = Column(Integer, nullable=True)

    # Rolling Gaussian moments for cost (cents)
    cost_mu = Column(Integer, nullable=True)
    cost_sigma = Column(Integer, nullable=True)
    cost_p95 = Column(Integer, nullable=True)

    trials = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_type", "model_name", name="uq_router_metric_scope"),
        Index("ix_router_metric_scope", "tenant_id", "task_type", "model_name"),
    )


class RouterPolicyConfig(Base):
    """Per-tenant and optional per-template default router policy configuration."""

    __tablename__ = "router_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    template_key = Column(String(100), index=True, nullable=True)
    enabled = Column(Boolean, nullable=False, default=False)
    policy = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint("tenant_id", "template_key", name="uq_router_policy_scope"),
        Index("ix_router_policy_tenant_template", "tenant_id", "template_key"),
    )


# -------------------- RAG v2 (incremental + hybrid) --------------------


class RagSource(Base):
    __tablename__ = "rag_sources"

    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    key = Column(String(200), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # http | s3 | webhook
    uri = Column(String(1024), nullable=True)
    meta = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_rag_source_tenant_key"),
    )


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id = Column(String(100), primary_key=True)
    source_id = Column(String(100), ForeignKey("rag_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)
    content = Column(Text, nullable=False)
    meta = Column(JSONB, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    embedding = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        Index("ix_rag_chunks_source_hash", "source_id", "content_hash", unique=True),
        Index("ix_rag_chunks_source_version", "source_id", "version"),
    )


class RagJob(Base):
    __tablename__ = "rag_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    source_id = Column(String(100), index=True, nullable=False)
    status = Column(String(20), nullable=False, default="queued")  # queued|running|done|failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


# -------------------- Ledger (double-entry) --------------------


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # asset|liability|expense|revenue|equity|off
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_ledger_account_tenant_name"),
        Index("ix_ledger_account_tenant", "tenant_id"),
    )


class LedgerJournal(Base):
    __tablename__ = "ledger_journals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    name = Column(String(200), nullable=False)
    external_id = Column(String(200), nullable=True, unique=True)
    meta = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    journal_id = Column(Integer, ForeignKey("ledger_journals.id", ondelete="CASCADE"), index=True, nullable=False)
    account_id = Column(Integer, ForeignKey("ledger_accounts.id", ondelete="RESTRICT"), index=True, nullable=False)
    commodity = Column(String(50), nullable=False)  # usd_cents | tokens
    side = Column(String(10), nullable=False)  # debit | credit
    amount = Column(Integer, nullable=False)  # integer minor units (cents or tokens)
    meta = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        Index("ix_ledger_entries_journal", "journal_id"),
        Index("ix_ledger_entries_account", "account_id"),
        Index("ix_ledger_entries_commodity", "commodity"),
    )


# -------------------- Policy Audits --------------------


class PolicyAudit(Base):
    __tablename__ = "policy_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    subject = Column(String(200), nullable=False)  # e.g., tool:api_caller
    action = Column(String(100), nullable=False)  # e.g., execute
    decision = Column(String(20), nullable=False)  # allow|deny|kill
    reason = Column(String(500), nullable=True)
    meta = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -------------------- HITL (Human-in-the-Loop) --------------------


class ActionApproval(Base):
    __tablename__ = "action_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    employee_id = Column(String(100), index=True, nullable=True)
    action = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending|approved|rejected
    reason = Column(Text, nullable=True)
    decided_by_user = Column(Integer, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    __table_args__ = (
        Index("ix_action_approvals_tenant_status", "tenant_id", "status"),
    )


# -------------------- Plugins / App Store --------------------


class Plugin(Base):
    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    homepage = Column(String(512), nullable=True)
    latest_version = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending|approved|denied
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class PluginVersion(Base):
    __tablename__ = "plugin_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id", ondelete="CASCADE"), index=True, nullable=False)
    version = Column(String(50), nullable=False)
    manifest = Column(JSONB, nullable=False)  # manifest.json contents
    entry_module = Column(String(200), nullable=False)
    entry_handler = Column(String(100), nullable=False)
    permissions = Column(JSONB, nullable=True)  # e.g., {"network": true}
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        UniqueConstraint("plugin_id", "version", name="uq_plugin_version"),
    )


class PluginInstall(Base):
    __tablename__ = "plugin_installs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    plugin_id = Column(Integer, ForeignKey("plugins.id", ondelete="CASCADE"), index=True, nullable=False)
    version_id = Column(Integer, ForeignKey("plugin_versions.id", ondelete="SET NULL"), index=True, nullable=True)
    auto_update = Column(Boolean, nullable=False, default=False)
    pinned_version = Column(String(50), nullable=True)
    installed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    __table_args__ = (
        UniqueConstraint("tenant_id", "plugin_id", name="uq_plugin_install_tenant_plugin"),
    )


# -------------------- Shadow/Canary --------------------


class CanaryConfig(Base):
    __tablename__ = "canary_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    employee_id = Column(String(100), index=True, nullable=False)
    shadow_employee_id = Column(String(100), index=True, nullable=True)
    percent = Column(Integer, nullable=False, default=0)
    threshold = Column(Float, nullable=False, default=0.9)
    windows = Column(Integer, nullable=False, default=10)
    status = Column(String(20), nullable=False, default="off")  # off|active|promote_ready|demote
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", name="uq_canary_emp"),
        Index("ix_canary_tenant_emp", "tenant_id", "employee_id"),
    )


class ShadowInvocation(Base):
    __tablename__ = "shadow_invocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    employee_id = Column(String(100), index=True, nullable=False)
    shadow_employee_id = Column(String(100), index=True, nullable=False)
    correlation_id = Column(String(64), index=True, nullable=False)
    input = Column(Text, nullable=False)
    primary_output = Column(Text, nullable=True)
    shadow_output = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -------------------- Webhooks --------------------


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    url = Column(String(1024), nullable=False)
    secret = Column(String(128), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    # Optional event type filter; when empty deliver all
    event_types = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    __table_args__ = (
        Index("ix_webhook_tenant_active", "tenant_id", "active"),
    )


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint_id = Column(Integer, ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), index=True, nullable=False)
    tenant_id = Column(String(100), index=True, nullable=False)
    event_type = Column(String(200), nullable=False)
    message_id = Column(String(50), nullable=True)  # bus message id used for dedupe
    payload = Column(JSONB, nullable=False)
    signature = Column(String(200), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="queued")  # queued|delivered|failed|dlq
    last_status_code = Column(Integer, nullable=True)
    last_error = Column(Text, nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    __table_args__ = (
        UniqueConstraint("endpoint_id", "message_id", name="uq_delivery_endpoint_message"),
        Index("ix_webhook_deliveries_tenant_status", "tenant_id", "status"),
    )


# -------------------- Data Lifecycle Policies --------------------


class DataLifecyclePolicy(Base):
    __tablename__ = "data_lifecycle_policies"

    tenant_id = Column(String(100), primary_key=True, index=True)
    chat_ttl_days = Column(Integer, nullable=True)  # TaskExecution retention
    tool_io_ttl_days = Column(Integer, nullable=True)  # AuditLog/tool logs retention
    pii_redaction_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -------------------- Data Moat / Aggregation & Training --------------------


class DataConsent(Base):
    __tablename__ = "data_consents"

    tenant_id = Column(String(100), primary_key=True, index=True)
    rag_aggregation_enabled = Column(Boolean, nullable=False, default=False)
    task_aggregation_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AggregatedSample(Base):
    __tablename__ = "aggregated_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=False)
    industry = Column(String(100), index=True, nullable=True)
    sample_type = Column(String(20), nullable=False, default="task")  # task|rag
    prompt_hash = Column(String(64), nullable=True)
    output_hash = Column(String(64), nullable=True)
    model_name = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    consent_snapshot = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        Index("ix_agg_samples_tenant_type", "tenant_id", "sample_type"),
    )


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(20), nullable=False)  # embedding|fine_tune
    industry = Column(String(100), index=True, nullable=True)
    status = Column(String(20), nullable=False, default="queued")  # queued|running|completed|failed
    params = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    industry = Column(String(100), index=True, nullable=True)
    task_type = Column(String(50), index=True, nullable=True)
    model_name = Column(String(100), nullable=False)
    baseline_model = Column(String(100), nullable=True)
    score = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (
        Index("ix_benchmark_industry_task", "industry", "task_type"),
    )


class ConsensusLog(Base):
    __tablename__ = "consensus_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), index=True, nullable=True)
    employee_id = Column(String(100), index=True, nullable=True)
    task_type = Column(String(50), nullable=True)
    models = Column(JSONB, nullable=True)  # [{model, ok, hash, latency_ms}]
    agreed = Column(Boolean, nullable=False, default=False)
    selected_model = Column(String(100), nullable=True)
    consensus_k = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
