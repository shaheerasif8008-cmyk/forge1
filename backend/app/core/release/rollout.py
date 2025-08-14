from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from redis import Redis

from app.db.models import Base
from app.db.session import SessionLocal, engine


class RolloutState(Base):
    __tablename__ = "rollouts"

    id = Column(Integer, primary_key=True, autoincrement=False, default=1)
    mode = Column(String(20), nullable=False, default="off")  # off | percent | allowlist
    percent = Column(Integer, nullable=True)
    allowlist = Column(JSONB, nullable=True)  # list of tenant ids
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def _ensure_table() -> None:
    # Create table if missing (useful in dev/local tests)
    RolloutState.__table__.create(bind=engine, checkfirst=True)


def _get_or_init(db: Session) -> RolloutState:
    _ensure_table()
    st = db.get(RolloutState, 1)
    if st is None:
        st = RolloutState(id=1, mode="off", percent=None, allowlist=[])
        db.add(st)
        db.commit()
        db.refresh(st)
    return st


def current_mode() -> dict[str, Any]:
    with SessionLocal() as db:
        st = _get_or_init(db)
        if st.mode == "percent":
            return {"mode": "percent", "value": int(st.percent or 0)}
        if st.mode == "allowlist":
            return {"mode": "allowlist", "value": list(st.allowlist or [])}
        return {"mode": "off", "value": None}


def _with_lock(key: str, func) -> None:
    # Best-effort distributed lock using Redis
    try:
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client: Redis = Redis.from_url(redis_url, decode_responses=True)
        # Acquire lock with short TTL
        token = str(datetime.now(UTC).timestamp())
        got = client.set(key, token, nx=True, ex=5)
        if not got:
            raise RuntimeError("rollout locked")
        try:
            func()
        finally:
            # Release if owned
            cur = client.get(key)
            if cur == token:
                client.delete(key)
            client.close()
    except Exception:
        # Fallback to direct execution if redis unavailable
        func()


def set_canary_percent(p: int) -> None:
    if p < 0 or p > 100:
        raise ValueError("percent must be between 0 and 100")
    def _op() -> None:
        with SessionLocal() as db:
            st = _get_or_init(db)
            st.mode = "percent"
            st.percent = int(p)
            st.allowlist = []
            st.updated_at = datetime.now(UTC)
            db.add(st)
            db.commit()

    _with_lock("rollout:lock", _op)


def set_canary_allowlist(tenant_ids: list[str]) -> None:
    def _op() -> None:
        with SessionLocal() as db:
            st = _get_or_init(db)
            st.mode = "allowlist"
            st.percent = None
            st.allowlist = list(tenant_ids)
            st.updated_at = datetime.now(UTC)
            db.add(st)
            db.commit()

    _with_lock("rollout:lock", _op)


def rollback_now() -> None:
    def _op() -> None:
        with SessionLocal() as db:
            st = _get_or_init(db)
            st.mode = "off"
            st.percent = None
            st.allowlist = []
            st.updated_at = datetime.now(UTC)
            db.add(st)
            db.commit()

    _with_lock("rollout:lock", _op)


