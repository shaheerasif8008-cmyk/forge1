from typing import Any

from fastapi import APIRouter, Depends, Response, status
import logging
from redis import Redis
from sqlalchemy import text
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import get_session
from ..core.logging_config import get_trace_id
from ..interconnect import get_interconnect

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
async def ready(
    response: Response, db: Session = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    db_ok = False
    redis_ok = False
    mig_ok = False
    ic_ok = False

    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False

    try:
        sync_client: Any = Redis.from_url(settings.redis_url, decode_responses=True)
        redis_ok = bool(sync_client.ping())
        sync_client.close()
    except Exception:  # noqa: BLE001
        redis_ok = False

    # Check alembic head match (non-blocking)
    try:
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = set(script.get_heads())
        from app.db.session import _make_engine_url
        eng = create_engine(_make_engine_url(), pool_pre_ping=True, future=True)
        with eng.connect() as conn:
            cur = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        mig_ok = (cur in heads) if heads else True
    except Exception:
        mig_ok = False

    # Interconnect health (non-blocking)
    try:
        ic = await get_interconnect()
        cli = await ic.client()
        # aio redis ping
        pong = await cli.ping()  # type: ignore[func-returns-value]
        ic_ok = bool(pong is True or pong == b"PONG")
    except Exception:  # noqa: BLE001
        ic_ok = False

    if db_ok and redis_ok and mig_ok and ic_ok:
        return {"status": "ready", "db": True, "redis": True, "migrations": True, "interconnect": True, "trace_id": get_trace_id()}
    # In dev/local, allow degraded state to be considered ready for basic UI/dev flows
    from ..core.config import settings as cfg
    if cfg.env in {"dev", "local"} and redis_ok:
        return {"status": "ready_degraded", "db": db_ok, "redis": redis_ok, "migrations": mig_ok, "interconnect": ic_ok, "trace_id": get_trace_id()}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "unready", "db": db_ok, "redis": redis_ok, "migrations": mig_ok, "interconnect": ic_ok, "trace_id": get_trace_id()}


@router.get("/")
async def health(db: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
    """Liveness endpoint; simple and fast."""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        client: Any = Redis.from_url(settings.redis_url, decode_responses=True)
        redis_ok = bool(client.ping())
        client.close()
    except Exception:
        redis_ok = False
    return {"status": "live" if (db_ok or settings.env in {"dev", "local"}) else "dead", "db": db_ok, "redis": redis_ok, "trace_id": get_trace_id()}
