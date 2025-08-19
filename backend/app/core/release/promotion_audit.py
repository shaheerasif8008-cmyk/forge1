from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.db.models import Base


class PromotionAudit(Base):
    __tablename__ = "audit_promotions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(20), nullable=False)  # promote | demote
    feature = Column(String(200), nullable=False)
    tenant_ids = Column(JSONB, nullable=False)
    performed_by = Column(String(100), nullable=False)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    details = Column(JSONB, nullable=True)


def write_audit(
    db: Session,
    action: str,
    feature: str,
    tenant_ids: list[str],
    performed_by: str,
    details: dict | None = None,
) -> None:
    entry = PromotionAudit(
        action=action,
        feature=feature,
        tenant_ids=tenant_ids,
        performed_by=performed_by,
        details=details or {},
    )
    db.add(entry)
    db.commit()


