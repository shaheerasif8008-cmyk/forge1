from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    tenant_id = Column(String(100), primary_key=True)
    flag = Column(String(200), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# Indexes are created via Alembic migrations to avoid runtime side effects.


def is_enabled(db: Session, tenant_id: str, flag: str, default: bool = False) -> bool:
    """Return whether a feature flag is enabled; fall back to default if not found or on error.

    Behavior expected by tests:
    - When flag not present, return the provided `default` (True or False)
    - When present, return the stored boolean
    """
    try:
        row = (
            db.query(FeatureFlag.enabled)
            .filter(FeatureFlag.tenant_id == tenant_id, FeatureFlag.flag == flag)
            .first()
        )
        if row is None:
            return True if default else False
        enabled_val = row[0]
        return True if bool(enabled_val) else False
    except Exception:  # noqa: BLE001
        return True if default else False


def set_flag(db: Session, tenant_id: str, flag: str, enabled: bool) -> None:
    # Upsert behavior for convenience
    stmt = pg_insert(FeatureFlag).values(
        tenant_id=tenant_id,
        flag=flag,
        enabled=enabled,
        updated_at=datetime.now(UTC),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[FeatureFlag.tenant_id, FeatureFlag.flag],
        set_={"enabled": enabled, "updated_at": datetime.now(UTC)},
    )
    db.execute(stmt)
    db.commit()


